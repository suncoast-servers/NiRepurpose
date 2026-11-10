# NiRepurpose — product roadmap

**Owner / merge authority:** [@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi)  
**Organization:** [suncoast-servers](https://github.com/suncoast-servers)  
**Repo:** [suncoast-servers/NiRepurpose](https://github.com/suncoast-servers/NiRepurpose)

NiRepurpose is an open-source desktop app (Python / CustomTkinter) for bulk repurposing images and videos for social posting, with metadata stripping and platform-friendly encodes.

Commercial scope, rates, and sensitive direction stay on **Upwork**. **GitHub Issues** track deliverables with acceptance criteria.

## North star

Reliable **Lite + Full** releases on Windows, Linux, and macOS (Apple Silicon and Intel), with a stable UI and predictable ffmpeg/exiftool behavior for non-technical users.

## Current baseline

| Area | Status |
|------|--------|
| Core app | `NiRepurpose.py` — bulk processing, naming modes, optional subfolders |
| Releases | Tag `v*` → GitHub Actions builds Lite/Full per OS |
| Docs | OS instruction files + README |
| CI | Python compile check on PRs (see `.github/workflows/python-ci.yml`) |

## Milestone: NiRepurpose enhancements

Active contractor work is tracked under milestone **[NiRepurpose enhancements](https://github.com/suncoast-servers/NiRepurpose/milestones)** and the **pinned epic** on the Issues tab.

| Track | Theme |
|-------|--------|
| Toolchain | Current stable **ffmpeg** + **ExifTool** in Full builds |
| Automation | PR/release workflow when upstream stable versions change |
| UX | Themes/skins + approved icon/logo |
| Premium | **Architecture RFC only** in this repo — custom metadata + PayRam credits (see [PRODUCT_SPEC.md](PRODUCT_SPEC.md)) |

**Suggested order:** toolchain upgrade → automation → UI (parallel OK) → premium ADR (Ryan sign-off before paid-feature implementation).

## Backlog rules

1. One issue per PR when possible.
2. Release/packaging tags (`v*`) — Ryan unless explicitly delegated.
3. Premium payment secrets and proprietary injection logic **do not** belong in this public repository.

## How work is assigned

1. Ryan creates or refines a **GitHub Issue**.
2. Contractor branches `feat/<issue>-short-name` or `fix/...`.
3. PR references the issue; Ryan reviews and merges.
