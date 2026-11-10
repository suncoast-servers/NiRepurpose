# NiRepurpose

[![Python CI](https://github.com/suncoast-servers/NiRepurpose/actions/workflows/python-ci.yml/badge.svg)](https://github.com/suncoast-servers/NiRepurpose/actions/workflows/python-ci.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/suncoast-servers/NiRepurpose)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

**Organization:** [suncoast-servers](https://github.com/suncoast-servers) · **Project lead / merge authority:** [@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi)

NiRepurpose is a desktop app inspired by NiClean, focused on bulk repurposing media for social posting.

It supports both images and videos, applies subtle randomized processing, strips metadata, and exports into an automatic output subfolder.

## Features

- NiClean-style UI and workflow
- Bulk media processing (`images + videos`)
- Optional recursive scan with `Include Subfolders`
- Copies-per-media control (`1` to `100`)
- Naming modes: `iPhone`, `Android`, `Original`, `Random`
- Random mirror flip option (`hflip` only)
- Optional run log generation (`NiRepurpose_log.txt`)
- Metadata stripping via `exiftool`
- Social-friendly encode defaults via `ffmpeg`

## Releases: Lite vs Full

Every tagged release (`v*`) publishes **two editions** for Windows, Linux, macOS Apple Silicon, and macOS Intel:

| Edition | Download name | Best for | Tools |
|---------|---------------|----------|-------|
| **Full** | `NiRepurpose-Full-*.zip` | Most users | Bundled `ffmpeg` + `exiftool` |
| **Lite** | `NiRepurpose-Lite-*.zip` | Smaller download | You install `ffmpeg` + `exiftool` on PATH |

macOS architecture:

- Apple Silicon (M1/M2/M3/M4): `NiRepurpose-*-macOS.zip`
- Intel: `NiRepurpose-*-macOS-Intel.zip`

Check with `uname -m` (`arm64` vs `x86_64`). Intel Macs need the Intel zip.

- [NiRepurpose Releases](https://github.com/suncoast-servers/NiRepurpose/releases)

## Quick Start

1. Download **Full** for your OS (easiest), or **Lite** if you already keep tools on PATH.
2. Extract and run.
3. Click `Select Folder`, then `NiRepurpose my Media`.
4. Output is written to `<Destination Folder>/NiRepurpose_repurposed`.

OS guides:

- `Instructions_Windows.md`
- `Instructions_Linux.md`
- `Instructions_MacOS.md`

## How Output Works

- Choose `Destination Folder` in the UI.
- NiRepurpose writes output to:
  - `<Destination Folder>/NiRepurpose_repurposed`

## Developer Run (from source)

```bash
git clone https://github.com/suncoast-servers/NiRepurpose.git
cd NiRepurpose
python -m venv .venv
```

Activate:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
python NiRepurpose.py
```

Source/dev mode uses `ffmpeg` and `exiftool` from PATH (or from a local `tools/` folder if present).

## Packaging

Tagging `v*` triggers GitHub Actions and builds Lite + Full for Windows, Linux, macOS Apple Silicon, and macOS Intel.

## Contributing (contractors & collaborators)

This repo uses **pull requests into `main`**. Direct pushes to `main` are blocked (ruleset + CODEOWNERS).

| Doc | Audience |
|-----|----------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Everyone — links org policy + repo workflow |
| [docs/COLLABORATOR.md](docs/COLLABORATOR.md) | Contractors — clone, branches, local checks |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Priorities and release goals |
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | OSS vs premium scope |
| [AGENTS.md](AGENTS.md) | AI coding assistants |

1. Read **COLLABORATOR.md** and org [CONTRIBUTING.md](https://github.com/suncoast-servers/.github/blob/main/CONTRIBUTING.md).
2. Branch: `feat/<issue>-short-description` or `fix/...`.
3. Open a PR; wait for review from **@TheDevWhoSaysNi** before merge.

## Notes

- Full edition is recommended for non-CLI users.
- Lite edition stays small and expects system-installed tools.
- Test on sample media before large runs.
