# Toolchain: pinned ffmpeg + ExifTool and automated updates

Full builds bundle **ffmpeg** and **ExifTool**. Their versions, download URLs and SHA-256 checksums are pinned in [`scripts/toolchain.json`](../scripts/toolchain.json). Everything below reads from or writes to that one file.

| Script / workflow | Purpose |
|-------------------|---------|
| `scripts/fetch_tools.py` | Download the pinned tools for one platform, verify SHA-256, extract into `tools/`, check versions, reject Git LFS pointer files |
| `scripts/smoke_test.py` | Strip planted metadata from a sample JPEG and transcode a sample MP4 with the app's own functions |
| `scripts/check_toolchain_updates.py` | Detect new upstream releases; with `--apply`, update the manifest, docs and Windows binaries |
| `.github/workflows/toolchain-check.yml` | Fetch + verify + smoke test on Windows, Linux, macOS arm64 and macOS Intel (PRs, and called by the update workflow) |
| `.github/workflows/toolchain-update.yml` | Weekly: detect → verify → push `automation/toolchain-*` branch → Toolchain check → open PR |
| `.github/workflows/build-release.yml` | On `v*` tags: install the pinned tools, smoke test, package, publish (Ryan only) |

## Which releases are tracked

| Tool | Channel | How the newest version is found | Platform sources |
|------|---------|--------------------------------|------------------|
| ffmpeg | Stable releases only (git tags `nX.Y` / `nX.Y.Z`, no nightlies) | Highest release tag in the official FFmpeg repository | Windows: gyan.dev release build (GitHub mirror `GyanD/codexffmpeg`, exact version tag). Linux + macOS: Martin Riedl release builds |
| ExifTool | Production releases only | "The most recent production release is Version X" on [exiftool.org/history.html](https://exiftool.org/history.html) | Official Windows package and `Image-ExifTool` tarball (via SourceForge) |

Rules:

- **All platforms move together.** If the new ffmpeg tag exists but a platform build isn't published yet, the update waits and is listed as *pending* in the run summary. No PR is opened with mixed versions.
- **Only upward.** The automation never downgrades.
- **Checksums are mandatory.** ffmpeg downloads must match the publisher's SHA-256 (for Windows, both gyan.dev's `.sha256` and the GitHub asset digest). ExifTool downloads are matched against `exiftool.org/checksums.txt` when the version is still listed there, and are **always** compared file by file with the official `exiftool/exiftool` git tag.
- **All or nothing.** Every download is verified before any file in the repo changes.

## Weekly automation

`toolchain-update.yml` runs every Monday at 07:23 UTC, and can also be run by hand (**Actions → Toolchain update → Run workflow**, optionally with *dry run*).

1. **Detect:** compare the pins with upstream. Up to date or pending → stop (see the run summary).
2. **Prepare:** download + verify, update `scripts/toolchain.json`, `README.md`, `NOTICE` and the Windows binaries in `tools/` (Git LFS).
3. **Push** branch `automation/toolchain-ffmpeg-<v>-exiftool-<v>` (never `main`). If the branch already exists, the update was already proposed, so nothing is done.
4. **Verify:** run the Toolchain check on that branch on all four platforms.
5. **Open a PR** with a version table, checksum sources and a release checklist. If verification failed, the PR is opened as a **draft** with a link to the failing run.

Merging, version bumps and `v*` tags stay with Ryan. The automation never creates tags or releases.

### One-time repository setup (Ryan)

Pick one:

- **Settings → Actions → General → Workflow permissions:** enable *Allow GitHub Actions to create and approve pull requests*. Simplest option.
- Or add a repository secret **`TOOLCHAIN_PR_TOKEN`**: a fine-grained personal access token for this repo with *Contents: read and write* and *Pull requests: read and write*. With it, the automated PR also triggers the normal PR checks (Python CI etc.). PRs opened with the built-in token don't trigger other workflows; the Toolchain check still runs inside the update workflow.

If neither is set, the workflow still pushes the branch and fails at the last step with a link to open the PR manually.

**After merging the automation workflow to `main`:** run **Actions → Toolchain update → Run workflow** once (dry run is fine). You should see *Toolchain is up to date* while pins match upstream (ffmpeg 9.0.2, ExifTool 13.55 today).

## Failure modes

| Situation | What happens | What to do |
|-----------|--------------|------------|
| Upstream site down / network error | Downloads retry with backoff; then the run fails before changing anything. GitHub emails a failure notice | Nothing; next week's run (or a manual run) retries |
| New ffmpeg tag, builds not published yet | Run succeeds and lists *pending* platforms; no PR | Wait. Builds usually follow within days |
| Checksum mismatch or ExifTool content differs from the git tag | Run fails with the expected and actual hashes; nothing is pushed | Treat as suspicious: compare with the publisher's site before changing any pin by hand |
| exiftool.org changes the history page wording | Run fails with "Could not find the production release note" | Update the regex in `exiftool_production_release()` |
| Platform build URL scheme changes (Martin Riedl / gyan) | That platform stays *pending*, or the run fails | Update the source logic in `scripts/check_toolchain_updates.py` |
| Wrong architecture or broken binary | Toolchain check fails on that runner (version check or smoke test); PR opened as draft | Don't merge; check the build source for that platform |
| Git LFS storage or bandwidth limits | Push of the Windows binaries (~115 MB per ffmpeg update) or Windows CI checkouts fail | Check the LFS quota under the org's billing settings; delete stale `automation/toolchain-*` branches |
| Update already proposed | Branch exists, so the run does nothing | Merge or close the open automation PR (delete its branch to get it proposed again) |
| `gh pr create` not permitted | Branch is pushed, last step fails with a compare link | Do the one-time setup above, or open the PR from the link |

## Manual use

```bash
python scripts/check_toolchain_updates.py            # report only
python scripts/check_toolchain_updates.py --apply    # update manifest, docs, Windows tools/ locally
python scripts/fetch_tools.py --verify-only          # check tools/
python scripts/smoke_test.py                         # strip + transcode smoke test
```

To pin a version by hand (e.g. to roll back), edit `scripts/toolchain.json` (version, `version_regex`, URLs, SHA-256), run `python scripts/fetch_tools.py` on Windows to refresh `tools/`, and open a PR. The Toolchain check verifies all platforms.
