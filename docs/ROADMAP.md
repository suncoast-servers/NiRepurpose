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

## Backlog

Ryan will add **GitHub Issues** (and optionally a milestone) for contractor work. Until then:

1. Open an issue per task with acceptance criteria before large PRs.
2. Prefer small PRs scoped to one issue.
3. Release/packaging changes need explicit coordination — only Ryan tags production releases unless delegated.

## How work is assigned

1. Ryan creates or refines a **GitHub Issue**.
2. Contractor branches `feat/<issue>-short-name` or `fix/...`.
3. PR references the issue; Ryan reviews and merges.
