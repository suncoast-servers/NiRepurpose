# NiRepurpose — contractor onboarding

Welcome. You are helping improve **NiRepurpose**, a desktop Python app for bulk social-media-friendly media processing.

**Ryan** ([@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi)) owns the repository, releases, and **merge authority**. You work through **issues and pull requests** on GitHub.

## Access model (recommended)

Outside **collaborator** on **this repository only** with **`push`** permission — not a full `suncoast-servers` org member. That lets you branch and open PRs without org-wide access.

After accepting Ryan’s GitHub invitation, confirm access:

```bash
git ls-remote https://github.com/suncoast-servers/NiRepurpose.git HEAD
```

## Clone

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

For packaging work, read `README.md` and `.github/workflows/build-release.yml`. **Release tags (`v*`) publish Lite + Full artifacts** — coordinate with Ryan before tagging.

## Workflow (required)

`main` is **protected**: no direct pushes, PR + approval required.

1. Pick a **GitHub Issue** under milestone **NiRepurpose enhancements** (start from epic **[#6](https://github.com/suncoast-servers/NiRepurpose/issues/6)**) or ask Ryan to create one.
2. Sync and branch:

   ```bash
   git fetch origin
   git checkout main && git pull
   git checkout -b feat/<issue>-short-description
   ```

3. Before every PR:

   ```bash
   python -m compileall -q NiRepurpose.py
   ```

   Run the app manually on your OS with sample media when touching processing or UI.

4. Push and open a **Pull Request** into `main` (use the template).
5. Address review comments. **Do not merge** unless Ryan explicitly asks.

Branch names: `feat/<issue>-short-name` or `fix/<issue>-short-name`.

## Where direction lives

| Channel | Use for |
|---------|---------|
| **GitHub Issues** | Scoped tasks, acceptance criteria, technical discussion |
| **Pull requests** | Code review, design notes, test evidence |
| **Upwork** | Contract, schedule, rates, confidential decisions |
| **Email** | info@suncoastservers.com — escalations |

Read [docs/ROADMAP.md](ROADMAP.md) for priorities.

## AI coding tools

Follow **[`AGENTS.md`](../AGENTS.md)** — no secrets in chat, no push to `main`.

## Security

- Do not commit API keys, tokens, or private customer media paths.
- Bundled `tools/` binaries are large; change only when the task requires it and call it out in the PR.

## Offboarding

When the engagement ends, Ryan removes collaborator access.
