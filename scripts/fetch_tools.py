#!/usr/bin/env python3
"""
Download, verify and install the pinned ffmpeg + ExifTool used by NiRepurpose Full builds.

Pins live in scripts/toolchain.json (version, URL and sha256 per platform). Every download is
checked against its sha256 before anything is extracted. Standard library only.

Examples:
    python scripts/fetch_tools.py                      # host platform -> tools/, then verify versions
    python scripts/fetch_tools.py --platform macos-x64 --dest build/tools --no-verify
    python scripts/fetch_tools.py --verify-only        # check what is already in tools/ (e.g. Windows LFS files)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("toolchain.json")
PLATFORMS = ("windows-x64", "linux-x64", "macos-arm64", "macos-x64")
TOOLS = ("ffmpeg", "exiftool")
USER_AGENT = "NiRepurpose-toolchain-fetch (+https://github.com/suncoast-servers/NiRepurpose)"
LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


def detect_platform() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows" and machine in ("amd64", "x86_64"):
        return "windows-x64"
    if system == "Linux" and machine in ("x86_64", "amd64"):
        return "linux-x64"
    if system == "Darwin":
        return "macos-arm64" if machine == "arm64" else "macos-x64"
    raise SystemExit(f"Unsupported host platform: {system} {machine}. Pass --platform explicitly.")


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as fh:
        return json.load(fh)


def platform_entry(manifest: dict, tool: str, plat: str) -> dict:
    platforms = manifest[tool]["platforms"]
    if plat in platforms:
        return platforms[plat]
    for entry in platforms.values():
        if plat in entry.get("used_by", []):
            return entry
    raise SystemExit(f"No {tool} pin for platform {plat} in {MANIFEST.name}")


def download(url: str, sha256: str, target: Path, attempts: int = 3) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            digest = hashlib.sha256()
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as out:
                while chunk := response.read(1 << 20):
                    digest.update(chunk)
                    out.write(chunk)
            actual = digest.hexdigest()
            if actual != sha256.lower():
                raise ValueError(f"sha256 mismatch for {url}\n  expected {sha256}\n  actual   {actual}")
            return
        except ValueError:
            raise
        except Exception as exc:  # network errors: retry with backoff
            last_error = exc
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Download failed after {attempts} attempts: {url}: {last_error}")


def _pattern_regex(pattern: str) -> str:
    # "*" matches exactly one path component (e.g. the versioned top-level folder of an archive).
    return re.escape(pattern.rstrip("/")).replace(r"\*", "[^/]+")


def _safe_relative(path: str) -> PurePosixPath:
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Unsafe archive path: {path}")
    return rel


class Archive:
    """Minimal read-only view over zip or tar archives: names, modes and file bytes."""

    def __init__(self, path: Path):
        if zipfile.is_zipfile(path):
            self._zip = zipfile.ZipFile(path)
            self._tar = None
            self.members = {i.filename.rstrip("/"): i for i in self._zip.infolist() if not i.is_dir()}
        else:
            self._zip = None
            self._tar = tarfile.open(path, "r:*")
            self.members = {m.name.removeprefix("./"): m for m in self._tar.getmembers() if m.isfile()}

    def is_executable(self, name: str) -> bool:
        info = self.members[name]
        mode = (info.external_attr >> 16) if self._zip else info.mode
        return bool(mode & 0o111)

    def copy_to(self, name: str, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if self._zip:
            source = self._zip.open(self.members[name])
        else:
            source = self._tar.extractfile(self.members[name])
        with source, target.open("wb") as out:
            shutil.copyfileobj(source, out)

    def close(self) -> None:
        (self._zip or self._tar).close()


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def extract(archive_path: Path, rules: list[dict], dest: Path) -> list[Path]:
    archive = Archive(archive_path)
    written: list[Path] = []
    try:
        for rule in rules:
            source, target = rule["from"], rule["to"]
            regex = _pattern_regex(source)
            target_path = dest / _safe_relative(target.rstrip("/"))
            if source.endswith("/"):
                prefix = re.compile(f"^{regex}/(.+)$")
                matches = [(n, m.group(1)) for n in archive.members if (m := prefix.match(n))]
                if not matches:
                    raise ValueError(f"{archive_path.name}: no files under '{source}'")
                _remove(target_path)
                for name, rel in matches:
                    out = target_path / _safe_relative(rel)
                    archive.copy_to(name, out)
                    if archive.is_executable(name):
                        _make_executable(out)
                written.append(target_path)
            else:
                matches = [n for n in archive.members if re.fullmatch(regex, n)]
                if len(matches) != 1:
                    raise ValueError(f"{archive_path.name}: expected one match for '{source}', found {matches}")
                _remove(target_path)
                archive.copy_to(matches[0], target_path)
                if not target_path.suffix:  # ffmpeg / exiftool on macOS + Linux
                    _make_executable(target_path)
                written.append(target_path)
    finally:
        archive.close()
    return written


def tool_command(tool: str, plat: str, dest: Path) -> list[str]:
    if tool == "ffmpeg":
        return [str(dest / ("ffmpeg.exe" if plat == "windows-x64" else "ffmpeg")), "-hide_banner", "-version"]
    if plat == "windows-x64":
        return [str(dest / "exiftool.exe"), "-ver"]
    return [shutil.which("perl") or "perl", str(dest / "exiftool"), "-ver"]


def verify(manifest: dict, tool: str, plat: str, dest: Path) -> str:
    """Run the installed tool and check the reported version against the pin. Returns the version line."""
    cmd = tool_command(tool, plat, dest)
    binary = Path(cmd[0] if tool == "ffmpeg" or plat == "windows-x64" else cmd[1])
    if not binary.is_file():
        raise SystemExit(f"[{tool}] missing: {binary}")
    with binary.open("rb") as fh:
        if fh.read(len(LFS_POINTER_PREFIX)) == LFS_POINTER_PREFIX:
            raise SystemExit(f"[{tool}] {binary} is a Git LFS pointer, not the real file. Run: git lfs pull")
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    output = (proc.stdout or proc.stderr).decode("utf-8", errors="replace").strip()
    line = output.splitlines()[0] if output else ""
    if proc.returncode != 0 or not re.search(manifest[tool]["version_regex"], line):
        raise SystemExit(
            f"[{tool}] version check failed: expected {manifest[tool]['version']}, got {line!r} (exit {proc.returncode})"
        )
    return line


def release_notes(manifest: dict) -> str:
    lines = [
        "## Bundled tools (Full edition)",
        "",
        "| Tool | Version | Platform | Source |",
        "|------|---------|----------|--------|",
    ]
    for tool in TOOLS:
        info = manifest[tool]
        for plat in PLATFORMS:
            entry = platform_entry(manifest, tool, plat)
            lines.append(f"| {tool} | {info['version']} ({info['channel']}) | {plat} | {entry['source']} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", choices=PLATFORMS, help="target platform (default: this machine)")
    parser.add_argument("--dest", type=Path, default=ROOT / "tools", help="install directory (default: tools/)")
    parser.add_argument("--tool", choices=TOOLS, action="append", help="limit to one tool (repeatable)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verify-only", action="store_true", help="do not download; verify installed versions")
    group.add_argument("--no-verify", action="store_true", help="skip running the tools (cross-platform fetch)")
    group.add_argument("--release-notes", action="store_true", help="print a Markdown table of the pinned tools")
    args = parser.parse_args()

    manifest = load_manifest()
    if args.release_notes:
        print(release_notes(manifest))
        return 0
    host = detect_platform_safe()
    plat = args.platform or host or detect_platform()
    tools = args.tool or list(TOOLS)
    dest = args.dest.resolve()
    can_run = plat == host

    if not args.verify_only:
        dest.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="ni_toolchain_") as tmp:
            for tool in tools:
                entry = platform_entry(manifest, tool, plat)
                archive = Path(tmp) / f"{tool}-{plat}.download"
                print(f"[{tool}] {manifest[tool]['version']} for {plat}: {entry['url']}")
                download(entry["url"], entry["sha256"], archive)
                print(f"[{tool}] sha256 OK ({entry['sha256'][:16]}...)")
                for path in extract(archive, entry["extract"], dest):
                    print(f"[{tool}] installed {path}")

    if args.no_verify:
        return 0
    if not can_run:
        print(f"Skipping version check: {plat} binaries cannot run on this machine.")
        return 0
    for tool in tools:
        print(f"[{tool}] OK: {verify(manifest, tool, plat, dest)}")
    return 0


def detect_platform_safe() -> str | None:
    try:
        return detect_platform()
    except SystemExit:
        return None


if __name__ == "__main__":
    sys.exit(main())
