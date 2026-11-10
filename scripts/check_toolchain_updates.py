#!/usr/bin/env python3
"""
Detect new upstream toolchain releases and update the pins in scripts/toolchain.json.

Tracks the same channels as the current pins:
  * ffmpeg   - newest stable release tag (nX.Y[.Z]) of FFmpeg, once every platform source
               (gyan.dev for Windows, Martin Riedl for Linux/macOS) publishes that exact version.
  * ExifTool - newest *production* release named on https://exiftool.org/history.html.

A tool is only updated when every platform has the new version (no mixed versions), and only
upward (never downgrades). Every new download is checked against the checksum its publisher
provides. ExifTool production releases often no longer have a published checksum, so those
downloads are also compared file-by-file with the official exiftool/exiftool git tag.

Modes:
    python scripts/check_toolchain_updates.py                # report only (no downloads, no changes)
    python scripts/check_toolchain_updates.py --apply        # update manifest, docs and Windows tools/
    python scripts/check_toolchain_updates.py --apply --pr-body pr-body.md --github-output "$GITHUB_OUTPUT"

Standard library only. Set GITHUB_TOKEN to avoid GitHub API rate limits.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_tools  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = fetch_tools.USER_AGENT

FFMPEG_TAGS_REPO = "https://github.com/FFmpeg/FFmpeg.git"
GYAN_RELEASE_API = "https://api.github.com/repos/GyanD/codexffmpeg/releases/tags/{version}"
GYAN_ASSET = "ffmpeg-{version}-essentials_build.zip"
GYAN_SHA256 = "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-{version}-essentials_build.zip.sha256"
RIEDL_LATEST = "https://ffmpeg.martin-riedl.de/redirect/latest/{os}/{arch}/release/ffmpeg.zip"
RIEDL_PLATFORMS = {"linux-x64": ("linux", "amd64"), "macos-arm64": ("macos", "arm64"), "macos-x64": ("macos", "amd64")}

EXIFTOOL_HISTORY = "https://exiftool.org/history.html"
EXIFTOOL_CHECKSUMS = "https://exiftool.org/checksums.txt"
EXIFTOOL_FILES = {
    "windows-x64": "https://sourceforge.net/projects/exiftool/files/exiftool-{version}_64.zip/download",
    "unix": "https://sourceforge.net/projects/exiftool/files/Image-ExifTool-{version}.tar.gz/download",
}
EXIFTOOL_FILE_NAMES = {"windows-x64": "exiftool-{version}_64.zip", "unix": "Image-ExifTool-{version}.tar.gz"}
EXIFTOOL_GIT_TAG = "https://github.com/exiftool/exiftool/archive/refs/tags/{version}.tar.gz"

# Lines in docs that carry the pinned version (label -> files). Updated in place.
DOC_LINES = {
    "ffmpeg": [("README.md", r"^\| FFmpeg \|"), ("NOTICE", r"^\d\) FFmpeg ")],
    "exiftool": [("README.md", r"^\| ExifTool \|"), ("NOTICE", r"^\d\) ExifTool ")],
}


# ---------------------------------------------------------------- HTTP helpers

def _request(url: str, accept_json: bool = False) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT}
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif accept_json:
        headers["Accept"] = "application/json"
    return urllib.request.Request(url, headers=headers)


def http_text(url: str) -> str:
    with urllib.request.urlopen(_request(url), timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def http_json(url: str):
    try:
        with urllib.request.urlopen(_request(url, accept_json=True), timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def redirect_target(url: str) -> str | None:
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(_request(url), timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            return urllib.parse.urljoin(url, exc.headers["Location"])
        raise
    return None


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


# ---------------------------------------------------------------- upstream discovery

def latest_ffmpeg_release() -> str:
    out = subprocess.run(
        ["git", "ls-remote", "--tags", FFMPEG_TAGS_REPO, "refs/tags/n*"],
        capture_output=True, text=True, check=True, timeout=120,
    ).stdout
    versions = [m.group(1) for m in re.finditer(r"refs/tags/n(\d+\.\d+(?:\.\d+)?)$", out, re.M)]
    if not versions:
        raise RuntimeError("No FFmpeg release tags found")
    return max(versions, key=version_tuple)


def ffmpeg_sources(version: str) -> tuple[dict, list[str]]:
    """Return ({platform: {url, sha256, checksum_source}}, [pending reasons]) for an ffmpeg version."""
    found: dict = {}
    pending: list[str] = []

    release = http_json(GYAN_RELEASE_API.format(version=version))
    asset_name = GYAN_ASSET.format(version=version)
    asset = next((a for a in (release or {}).get("assets", []) if a["name"] == asset_name), None)
    if not asset:
        pending.append(f"windows-x64: gyan.dev has not published {asset_name} yet")
    else:
        digest = (asset.get("digest") or "").removeprefix("sha256:")
        try:
            published = http_text(GYAN_SHA256.format(version=version)).split()[0]
        except Exception:
            published = ""
        if digest and published and digest != published:
            raise RuntimeError(f"gyan.dev checksum ({published}) and GitHub digest ({digest}) disagree for {asset_name}")
        sha = digest or published
        if not re.fullmatch(r"[0-9a-f]{64}", sha or ""):
            pending.append(f"windows-x64: no published sha256 for {asset_name}")
        else:
            found["windows-x64"] = {
                "url": asset["browser_download_url"],
                "sha256": sha,
                "checksum_source": "GitHub asset digest + gyan.dev .sha256" if digest and published else "publisher",
            }

    for plat, (os_name, arch) in RIEDL_PLATFORMS.items():
        target = redirect_target(RIEDL_LATEST.format(os=os_name, arch=arch))
        match = re.search(r"/(\d+)_(\d+\.\d+(?:\.\d+)?)/ffmpeg\.zip$", target or "")
        if not match or match.group(2) != version:
            have = match.group(2) if match else "unknown"
            pending.append(f"{plat}: Martin Riedl latest release build is {have}, waiting for {version}")
            continue
        sha = http_text(target + ".sha256").split()[0]
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            pending.append(f"{plat}: no valid sha256 next to {target}")
            continue
        found[plat] = {"url": target, "sha256": sha, "checksum_source": "publisher .sha256"}
    return found, pending


def exiftool_production_release() -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(http_text(EXIFTOOL_HISTORY)))
    match = re.search(r"most recent production release is\s+Version\s+(\d+\.\d+)", text, re.I)
    if not match:
        raise RuntimeError("Could not find the production release note on exiftool.org/history.html")
    return match.group(1)


def exiftool_sources(version: str) -> dict:
    try:
        checksums = http_text(EXIFTOOL_CHECKSUMS)
    except Exception:
        checksums = ""
    found = {}
    for key, url in EXIFTOOL_FILES.items():
        name = EXIFTOOL_FILE_NAMES[key].format(version=version)
        match = re.search(rf"SHA2-256\({re.escape(name)}\)=\s*([0-9a-f]{{64}})", checksums)
        found[key] = {
            "url": url.format(version=version),
            "sha256": match.group(1) if match else None,  # None: computed, then verified against the git tag
            "checksum_source": "exiftool.org checksums.txt" if match else "git tag cross-check",
        }
    return found


# ---------------------------------------------------------------- verification

def download_and_hash(url: str, target: Path, attempts: int = 4) -> str:
    for attempt in range(1, attempts + 1):
        try:
            digest = hashlib.sha256()
            with urllib.request.urlopen(_request(url), timeout=300) as response, target.open("wb") as out:
                while chunk := response.read(1 << 20):
                    digest.update(chunk)
                    out.write(chunk)
            return digest.hexdigest()
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"Download failed after {attempts} attempts: {url}: {exc}") from exc
            print(f"  retrying ({attempt}/{attempts - 1}) after: {exc}")
            time.sleep(10 * attempt)
    raise AssertionError("unreachable")


def _strip_top(name: str) -> str:
    return name.split("/", 1)[1] if "/" in name else name


def crosscheck_exiftool(version: str, windows_zip: Path, unix_tar: Path, workdir: Path) -> None:
    """Raise unless the downloads match the official exiftool/exiftool git tag file-by-file."""
    tag_path = workdir / f"exiftool-tag-{version}.tar.gz"
    download_and_hash(EXIFTOOL_GIT_TAG.format(version=version), tag_path)
    with tarfile.open(tag_path) as tag_tar:
        tag = {
            _strip_top(m.name): tag_tar.extractfile(m).read()
            for m in tag_tar.getmembers()
            if m.isfile() and (_strip_top(m.name).startswith("lib/") or _strip_top(m.name) in ("exiftool", "windows_exiftool"))
        }
    tag_lib = {k: v for k, v in tag.items() if k.startswith("lib/")}

    dist = fetch_tools.Archive(unix_tar)
    try:
        files = {_strip_top(n): n for n in dist.members}
        dist_lib = {k: dist.read(n) for k, n in files.items() if k.startswith("lib/")}
        if dist_lib != tag_lib or dist.read(files["exiftool"]) != tag["exiftool"]:
            raise RuntimeError(f"Image-ExifTool-{version}.tar.gz does not match git tag {version}")
    finally:
        dist.close()

    win = fetch_tools.Archive(windows_zip)
    try:
        prefix = re.compile(r"^[^/]+/exiftool_files/(.+)$")
        files = {m.group(1): n for n in win.members if (m := prefix.match(n))}
        win_image = {f"lib/{k[4:]}": win.read(n) for k, n in files.items() if k.startswith("lib/Image/")}
        tag_image = {k: v for k, v in tag_lib.items() if k.startswith("lib/Image/")}
        if win_image != tag_image or win.read(files["exiftool.pl"]) != tag["windows_exiftool"]:
            raise RuntimeError(f"exiftool-{version}_64.zip does not match git tag {version}")
    finally:
        win.close()


def verify_downloads(tool: str, version: str, sources: dict, workdir: Path) -> dict[str, Path]:
    """Download every new asset, enforce published checksums, fill in computed ones. Returns local paths."""
    paths: dict[str, Path] = {}
    for key, info in sources.items():
        path = workdir / f"{tool}-{version}-{key}.download"
        actual = download_and_hash(info["url"], path)
        if info["sha256"] and actual != info["sha256"]:
            raise RuntimeError(f"{tool} {key}: sha256 mismatch\n  published {info['sha256']}\n  download  {actual}")
        info["sha256"] = actual
        paths[key] = path
        print(f"[{tool}] {key}: sha256 {actual[:16]}... ({info['checksum_source']})")
    if tool == "exiftool":
        crosscheck_exiftool(version, paths["windows-x64"], paths["unix"], workdir)
        print(f"[exiftool] downloads match official git tag {version}")
    return paths


# ---------------------------------------------------------------- applying

def version_regex(tool: str, version: str) -> str:
    escaped = re.escape(version)
    return f"ffmpeg version n?{escaped}(?![0-9])" if tool == "ffmpeg" else f"^{escaped}$"


def update_docs(root: Path, tool: str, old: str, new: str) -> list[str]:
    """Replace the version on the known doc lines. Returns warnings for lines that were not found."""
    warnings = []
    for rel, line_pattern in DOC_LINES[tool]:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        lines = text.split("\n")
        hits = 0
        for i, line in enumerate(lines):
            if re.search(line_pattern, line) and old in line:
                lines[i] = line.replace(old, new)
                hits += 1
        if hits:
            path.write_text("\n".join(lines), encoding="utf-8", newline="")
        else:
            warnings.append(f"{rel}: no {tool} {old} line found to update")
    return warnings


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository root (default: this repo)")
    parser.add_argument("--apply", action="store_true", help="download, verify and write the updates")
    parser.add_argument("--pr-body", type=Path, help="write a pull request description here (with --apply)")
    parser.add_argument("--github-output", type=Path, help="append changed/branch/title for GitHub Actions")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = root / "scripts" / "toolchain.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = {tool: manifest[tool]["version"] for tool in fetch_tools.TOOLS}

    upstream = {"ffmpeg": latest_ffmpeg_release(), "exiftool": exiftool_production_release()}
    print(f"ffmpeg:   pinned {current['ffmpeg']}, latest stable {upstream['ffmpeg']}")
    print(f"exiftool: pinned {current['exiftool']}, latest production {upstream['exiftool']}")

    updates: dict[str, dict] = {}
    pending: list[str] = []
    for tool in fetch_tools.TOOLS:
        if version_tuple(upstream[tool]) <= version_tuple(current[tool]):
            continue
        if tool == "ffmpeg":
            sources, waiting = ffmpeg_sources(upstream[tool])
            if waiting:
                pending.extend(f"ffmpeg {upstream[tool]}: {w}" for w in waiting)
                continue
        else:
            sources = exiftool_sources(upstream[tool])
        updates[tool] = {"version": upstream[tool], "sources": sources}

    for line in pending:
        print(f"PENDING {line}")
    if not updates:
        print("Toolchain is up to date." if not pending else "No update ready yet (see PENDING).")
        _github_output(args.github_output, changed=False)
        return 0
    for tool, update in updates.items():
        print(f"UPDATE  {tool}: {current[tool]} -> {update['version']}")
    if not args.apply:
        _github_output(args.github_output, changed=False)
        return 0

    warnings: list[str] = []
    rows: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ni_toolchain_update_") as tmp:
        workdir = Path(tmp)
        # Phase 1: download + verify everything. Nothing in the repo changes if any check fails.
        downloads = {tool: verify_downloads(tool, u["version"], u["sources"], workdir) for tool, u in updates.items()}
        # Phase 2: write manifest, docs and Windows binaries.
        for tool, update in updates.items():
            new = update["version"]
            paths = downloads[tool]
            entry = manifest[tool]
            for key, info in update["sources"].items():
                old_url = entry["platforms"][key]["url"]
                entry["platforms"][key]["url"] = info["url"]
                entry["platforms"][key]["sha256"] = info["sha256"]
                rows.append(
                    f"| {tool} | {key} | {current[tool]} | **{new}** | `{info['sha256'][:16]}…` ({info['checksum_source']}) |"
                )
                if old_url == info["url"]:
                    raise RuntimeError(f"{tool} {key}: URL did not change for a new version: {old_url}")
            entry["version"] = new
            entry["version_regex"] = version_regex(tool, new)
            warnings += update_docs(root, tool, current[tool], new)

            # Windows binaries are committed (Git LFS): install the verified download into tools/.
            win_rules = entry["platforms"]["windows-x64"]["extract"]
            for written in fetch_tools.extract(paths["windows-x64"], win_rules, root / "tools"):
                print(f"[{tool}] updated {written.relative_to(root)}")
        write_manifest(manifest_path, manifest)

    versions = {tool: updates[tool]["version"] if tool in updates else current[tool] for tool in fetch_tools.TOOLS}
    changes = ", ".join(f"{t} {current[t]} -> {updates[t]['version']}" for t in updates)
    title = f"chore(toolchain): {changes}"
    branch = "automation/toolchain-" + "-".join(f"{t}-{versions[t]}" for t in fetch_tools.TOOLS)
    if args.pr_body:
        args.pr_body.write_text(_pr_body(changes, rows, pending, warnings), encoding="utf-8")
    _github_output(args.github_output, changed=True, branch=branch, title=title)
    print(f"Branch: {branch}\nTitle:  {title}")
    for warning in warnings:
        print(f"WARNING {warning}")
    return 0


def _pr_body(changes: str, rows: list[str], pending: list[str], warnings: list[str]) -> str:
    parts = [
        "## Summary",
        "",
        f"Automated toolchain update: **{changes}**.",
        "Opened by the **Toolchain update** workflow (`.github/workflows/toolchain-update.yml`). See `docs/TOOLCHAIN.md`.",
        "",
        "- **Related issue:** #3 (automation)",
        "- **Platforms tested:** Toolchain check on windows-x64, linux-x64, macos-arm64 and macos-x64 (result above)",
        "",
        "## Version changes",
        "",
        "| Tool | Platform | Old | New | SHA-256 (checksum source) |",
        "|------|----------|-----|-----|---------------------------|",
        *rows,
        "",
        "## What changed",
        "",
        "- `scripts/toolchain.json`: versions, download URLs, SHA-256 pins",
        "- `tools/` (Windows, Git LFS): new binaries, extracted from the verified downloads",
        "- `README.md`, `NOTICE`: version numbers",
    ]
    if warnings:
        parts += ["", "### ⚠️ Needs a manual look", "", *[f"- {w}" for w in warnings]]
    if pending:
        parts += ["", "### Not included yet (waiting for upstream)", "", *[f"- {p}" for p in pending]]
    parts += [
        "",
        "## Release checklist (Ryan)",
        "",
        "- [ ] Toolchain check is green on all four platforms",
        "- [ ] Bundled-binary size/license change acceptable (Git LFS)",
        "- [ ] Merge",
        "- [ ] Optional: bump `APP_VERSION` and tag `v*` to publish Lite + Full builds (Ryan only)",
        "",
        "No release tag is created by this automation.",
    ]
    return "\n".join(parts) + "\n"


def _github_output(path: Path | None, **values) -> None:
    if not path:
        return
    with path.open("a", encoding="utf-8") as fh:
        for key, value in values.items():
            fh.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")


if __name__ == "__main__":
    sys.exit(main())
