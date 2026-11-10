# Seed NiRepurpose enhancement backlog — run from repo root with gh auth.
$ErrorActionPreference = 'Stop'
$cred = @"
protocol=https
host=github.com

"@ | git credential fill 2>$null
$env:GH_TOKEN = (($cred | Where-Object { $_ -match '^password=' }) -replace '^password=','')
$gh = 'C:\Program Files\GitHub CLI\gh.exe'
$owner = 'suncoast-servers'
$repo = 'NiRepurpose'

$labels = @(
  @{ name = 'epic'; color = '5319E7'; description = 'Epic / parent issue' },
  @{ name = 'dependencies'; color = '0366D6'; description = 'ffmpeg, exiftool, bundled tools' },
  @{ name = 'automation'; color = '0E8A16'; description = 'CI/CD, release automation' },
  @{ name = 'ux-theme'; color = 'FBCA04'; description = 'UI, skins, branding' },
  @{ name = 'premium'; color = 'B60205'; description = 'Pro / paid metadata features (architecture)' }
)
foreach ($l in $labels) {
  $body = @{ name = $l.name; color = $l.color; description = $l.description } | ConvertTo-Json -Compress
  try { $body | & $gh api -X POST "repos/$owner/$repo/labels" --input - 2>$null } catch { }
}

$msBody = @{
  title = 'NiRepurpose enhancements'
  description = 'Toolchain updates, release automation, UI polish, premium architecture. See docs/PRODUCT_SPEC.md.'
} | ConvertTo-Json -Compress
$milestone = $msBody | & $gh api -X POST "repos/$owner/$repo/milestones" --input - | ConvertFrom-Json
$ms = $milestone.number

function New-Issue($title, $body, [string[]]$issueLabels) {
  $payload = @{ title = $title; body = $body; milestone = $ms; labels = $issueLabels } | ConvertTo-Json -Compress
  return ($payload | & $gh api -X POST "repos/$owner/$repo/issues" --input - | ConvertFrom-Json)
}

$issues = @(
  @{
    title = 'Upgrade bundled ffmpeg and exiftool to current stable releases'
    labels = @('dependencies')
    body = @'
## Context
**Full** edition bundles `ffmpeg` and `exiftool` under `tools/` (Windows via Git LFS; Linux/macOS builds fetch binaries in CI — see `.github/workflows/build-release.yml`).

These versions drift over time. Align all platforms with **current stable** upstream releases and document versions in the release notes.

## Acceptance criteria
- [ ] Record current bundled versions (Windows LFS + CI download URLs) in PR description
- [ ] Upgrade to latest **stable** ffmpeg appropriate per OS/arch (Windows, Linux, macOS arm64, macOS x86_64)
- [ ] Upgrade to latest **stable** ExifTool (follow [exiftool.org](https://exiftool.org/) / GitHub tags; Windows needs `exiftool.exe` + `exiftool_files` as today)
- [ ] Full edition smoke test: strip metadata on sample image + transcode sample video on at least one OS (document which)
- [ ] Update README or `NOTICE` if third-party versions changed materially
- [ ] No LFS pointer regressions (Windows full build must not ship pointer files)

## Technical notes
- macOS CI uses `eugeneware/ffmpeg-static` and exiftool tarball today — evaluate if better official sources exist while staying portable.
- Ryan approves before merging large binary updates (size + license unchanged).
- **Do not** tag a release unless Ryan asks; this issue is dependency refresh only.

## Out of scope
- Automated monitoring for future updates (see separate automation issue).
'@
  },
  @{
    title = 'Automate toolchain updates when ffmpeg or ExifTool stable releases ship'
    labels = @('automation', 'dependencies')
    body = @'
## Context
After baseline versions are current, reduce manual toil: when **ffmpeg** or **ExifTool** publish new **stable** releases, the project should detect, update, verify, and produce a **new NiRepurpose release** with minimal manual steps.

## Acceptance criteria
- [ ] Scheduled workflow (e.g. weekly) or release watcher that checks authoritative version sources:
  - ExifTool: `https://exiftool.org/ver.txt` and/or GitHub releases
  - ffmpeg: documented source per platform (static builds or official tags — must match issue #1 strategy)
- [ ] When versions change, open an **automated PR** updating toolchain pins/paths/docs (Ryan reviews; no direct push to `main`)
- [ ] CI validates compile/smoke checks on PR
- [ ] Optional (Ryan approval): workflow opens a **draft GitHub Release** or comments with checklist to tag `v*` — **Ryan retains tag/release authority** unless explicitly delegated
- [ ] Document failure modes (upstream URL down, LFS limits, arch mismatch)

## Design constraints
- Prefer **PR-first** updates over silent commits to `main`
- Binary/LFS updates may exceed normal PR size — use clear PR title/body with version diff table
- Security: pin download URLs; verify checksums when upstream publishes them

## Depends on
- Toolchain upgrade approach from the bundled ffmpeg/exiftool issue (same download sources).

## Out of scope
- Bleeding-edge/nightly ffmpeg; **stable only**
'@
  },
  @{
    title = 'UI themes, visual polish, and custom app icon/logo'
    labels = @('ux-theme')
    body = @'
## Context
The app uses CustomTkinter with default **blue** theme (`NiRepurpose.py`). Icons live in `assets/` (`nirepurpose.ico`, `.png`, `.icns`). Ryan wants a cleaner look and **on-brand artwork** (possibly AI-generated) instead of a generic open-source camera aesthetic.

## Acceptance criteria
- [ ] **2–3 selectable themes/skins** (colors, fonts, spacing) via a simple in-app control (Settings) or theme module; default remains usable for existing users
- [ ] Proposals include at least one **dark** and one **light** option suited to a media utility app
- [ ] **Icon/logo package**: propose replacement app icon set (`.ico`, `.png`, `.icns`) — Ryan approves final assets before merge if AI-generated (confirm license/rights in PR)
- [ ] PyInstaller `--icon` paths updated if filenames change
- [ ] Screenshots in PR for each theme + window chrome
- [ ] No functional regression in bulk processing workflow (smoke test documented)

## Ryan-owned
- Final logo approval and any trademark/branding constraints
- If AI assets used, contractor documents provenance in PR (model, license, no third-party marks)

## Out of scope
- Premium/pro UI tab (premium architecture issue)
'@
  },
  @{
    title = 'Premium tier architecture: custom metadata, credits, PayRam (RFC)'
    labels = @('premium', 'epic')
    body = @'
## Context
**Free / OSS (this repo):** privacy-focused bulk repurposing, **strip** metadata.

**Premium (not open source):** users who need to **inject** or template metadata for mass posting (corporations, agencies) pay nominal **crypto credits** via Ryan’s **PayRam** server on **Hetzner VPS**. Pricing model TBD: small fee per generation and/or cheap monthly cap — user chooses model in app.

Ryan needs a **solution architecture** before implementation. Premium logic must not be trivially rip-able from the public repo.

## Deliverables (this issue = architecture phase)
- [ ] **ADR / RFC** (`docs/adr/` or linked doc) comparing:
  - **Single app** with Pro tab + closed-source module/plugin vs **separate app** (e.g. NiRepurpose Pro)
  - Trust/distribution: GitHub Releases (OSS) vs signed Pro builds from Ryan-controlled host
- [ ] **Licensing boundary**: what stays Apache-2.0 in this repo vs private repo / binary module
- [ ] **Payment flow** (high level): in-app credit balance, PayRam on Hetzner, no complicated standalone checkout web app required for v1
- [ ] **Security**: API auth, credit metering, tamper resistance options (honest threat model — not DRM theater)
- [ ] **Metadata injection** feature outline: templates, batch apply, audit log — **spec only**, no secrets in git
- [ ] **Effort estimate** and phased implementation proposal (Phase 1 spike vs full product)

## Acceptance criteria for architecture sign-off
- [ ] Ryan reviews ADR in PR and approves direction in writing (issue comment)
- [ ] Explicit list of env vars/secrets Ryan provisions on VPS (names only, not values)
- [ ] Clear recommendation: same app vs Pro app with one-sentence rationale

## Implementation (future issues — out of scope here)
- PayRam integration code likely lives **outside** this public repository unless Ryan chooses otherwise
- No payment API keys committed to `suncoast-servers/NiRepurpose`

## Product reference
[docs/PRODUCT_SPEC.md](https://github.com/suncoast-servers/NiRepurpose/blob/main/docs/PRODUCT_SPEC.md)
'@
  }
)

$created = @()
foreach ($i in $issues) {
  $r = New-Issue $i.title $i.body $i.labels
  Write-Host "Created #$($r.number): $($r.title)"
  $created += $r
}

$childList = ($created | ForEach-Object { "- #$($_.number) $($_.title)" }) -join "`n"
$epicBody = @"
# Epic: NiRepurpose enhancements

Public OSS improvements plus **premium architecture** (implementation may be private).

**Spec:** [docs/PRODUCT_SPEC.md](https://github.com/suncoast-servers/NiRepurpose/blob/main/docs/PRODUCT_SPEC.md)

## Child issues
$childList

## Suggested order
1. Toolchain upgrade (bundled ffmpeg/exiftool)
2. Toolchain release automation
3. UI themes + logo (can overlap with #1 in parallel)
4. Premium RFC — **Ryan sign-off before any paid-feature code in public repo**

## Definition of done (epic)
- [ ] Full edition ships current stable tools on all platforms
- [ ] Automation proposes PRs when upstream stables change
- [ ] Selectable themes + approved icon set
- [ ] Approved premium architecture ADR and phased plan
"@

$epic = New-Issue 'Epic: NiRepurpose enhancements backlog' $epicBody @('epic')
Write-Host "Created epic #$($epic.number)"

foreach ($c in $created) {
  $p = @{ body = "Part of epic #$($epic.number)" } | ConvertTo-Json -Compress
  $p | & $gh api -X POST "repos/$owner/$repo/issues/$($c.number)/comments" --input - | Out-Null
}

$pin = @{ query = "mutation { pinIssue(input: {issueId: `"$($epic.node_id)`"}) { issue { number title } } }" } | ConvertTo-Json -Compress
$pin | & $gh api graphql --input - | Out-Null
Write-Host "Pinned epic #$($epic.number)"
Write-Host "Milestone: $($milestone.title) (#$ms)"
