# AGENTS.md — NiRepurpose

Guidance for **Cursor**, **Claude Code**, **Codex**, and human contributors.

## Product context

Desktop **Python** app using **CustomTkinter** for bulk image/video repurposing (ffmpeg + exiftool). Shipped as **Lite** (system tools) and **Full** (bundled binaries) via GitHub Actions on version tags.

## Ownership

| Role | Who |
|------|-----|
| **Repo & release owner** | Ryan (@TheDevWhoSaysNi) — merges, tags, release go/no-go |
| **Contractors** | Feature branches and PRs per assigned issues |

## Git rules

1. **Never push to `main`.** Use `feat/...` or `fix/...`.
2. Open a **PR**; fill the template; link the issue.
3. Ryan **merges** after review.
4. Avoid committing unnecessary changes under `tools/` (bundled binaries).

## Local checks (before every PR)

```bash
pip install -r requirements.txt
python -m compileall -q NiRepurpose.py
```

Run `python NiRepurpose.py` for UI or processing changes. Note OS tested in the PR.

## Packaging

- Release workflow: `.github/workflows/build-release.yml`
- Do not create `v*` tags without Ryan’s approval.

## More detail

- Org workflow: https://github.com/suncoast-servers/.github/blob/main/CONTRIBUTING.md
- This repo: `docs/COLLABORATOR.md`, `docs/ROADMAP.md`, `CONTRIBUTING.md`
