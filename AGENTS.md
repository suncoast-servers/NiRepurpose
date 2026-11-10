# AGENTS.md — NiRepurpose

Guidance for **Cursor**, **Claude Code**, **Codex**, and human contributors.

## Product context

Desktop **Python** app using **CustomTkinter** for bulk image/video repurposing (ffmpeg + exiftool). Shipped as **Lite** (system tools) and **Full** (bundled binaries) via GitHub Actions on version tags.

## Ownership

| Role | Who |
|------|-----|
| **Repo & release owner** | Ryan (@TheDevWhoSaysNi) — merges, tags, release go/no-go |
| **Delivery lead** | Owais (@owaischanna) — feature branches, PRs, milestone work |

## Git rules

1. **Never push to `main`.** Use `feat/...` or `fix/...`.
2. Open a **PR**; fill the template; link the issue.
3. Ryan **merges** after review.
4. Avoid committing unnecessary changes under `tools/` (bundled binaries).

## Local checks (before every PR)

```bash
pip install -r requirements.txt
python -m compileall -q NiRepurpose.py scripts
```

Run `python NiRepurpose.py` for UI or processing changes. Note OS tested in the PR.

For changes under `scripts/toolchain.json` or toolchain workflows:

```bash
python scripts/check_toolchain_updates.py          # report only
python scripts/fetch_tools.py --verify-only      # when tools/ is present (Windows Full)
```

See `docs/TOOLCHAIN.md` for pins, automation and failure modes.

## Packaging

- Release workflow: `.github/workflows/build-release.yml`
- Toolchain pins and weekly update automation: `docs/TOOLCHAIN.md`, `.github/workflows/toolchain-update.yml`
- Do not create `v*` tags without Ryan’s approval.

## More detail

- Org workflow: https://github.com/suncoast-servers/.github/blob/main/CONTRIBUTING.md
- This repo: `docs/COLLABORATOR.md`, `docs/ROADMAP.md`, `CONTRIBUTING.md`
