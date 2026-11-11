# ADR-0001 — Premium tier architecture: custom metadata, credits, PayRam

| | |
|---|---|
| **Status** | **Proposed** — awaiting written approval from [@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi) |
| **Issue** | [#5](https://github.com/suncoast-servers/NiRepurpose/issues/5) (epic [#6](https://github.com/suncoast-servers/NiRepurpose/issues/6)) |
| **Author** | [@owaischanna](https://github.com/owaischanna) (delivery lead) |
| **Decision owner** | [@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi) |
| **Date** | 2026-11-11 |

> **Scope guard.** This document is **architecture only**. No premium or payment code is
> proposed for merge, in this repository or elsewhere, until Ryan approves a direction in
> writing on issue #5. See [Phased plan](#9-phased-plan-and-effort-estimate).

---

## 1. Recommendation (read this first)

**Build one application in two editions from two repositories.** The public repo
(`suncoast-servers/NiRepurpose`, Apache-2.0) stays the free edition and gains **no** paid
logic. A new **private** repo (`NiRepurpose-Pro`) consumes this repo as a pinned upstream
dependency, adds a `pro/` package (metadata injection, credits, PayRam client), and
publishes signed **NiRepurpose Pro** builds from a Ryan-controlled host.

**Rationale, one sentence:** it keeps the public repo forkable and completely free of paid
logic, avoids publishing a plugin API that would double as a blueprint for re-implementing
Pro, and lets Ryan ship and revoke Pro builds on his own cadence — at the cost of
maintaining one extra build pipeline.

Two supporting decisions follow from it:

- **Credits are metered by a small entitlement service on the Hetzner VPS, not by PayRam and
  not by the app.** PayRam issues invoices; it cannot meter per-user credits, and the app
  must never hold the PayRam API key.
- **Sell prepaid credit packs and 30-day passes, not subscriptions.** PayRam has no native
  recurring billing, so a "monthly cap" is modelled as a one-off invoice for a 30-day pass.

---

## 2. Context

| Edition | Repo | Licence | Audience | Metadata |
|---|---|---|---|---|
| **NiRepurpose** (today) | public | Apache-2.0 | everyone | **strip** |
| **NiRepurpose Pro** (proposed) | private | proprietary | agencies, mass posters, corporates | **inject / template** |

The free edition's value is privacy: `strip_all_metadata()` runs `exiftool -all=` over every
output file. The paid edition inverts that for users who need *controlled, consistent*
metadata across large batches — agency and corporate workflows where provenance fields,
copyright and campaign tagging must match across thousands of assets.

### 2.1 An honest statement about the "proprietary algorithm"

Issue #5 asks that premium logic "must not be trivially rip-able from the public repo." It
is worth being blunt in writing before we design around a false premise:

**Metadata injection is not defensible intellectual property.** It is `exiftool -TAG=VALUE`.
The tag names are public, ExifTool is open source, and any competent developer can reproduce
the mechanism in an afternoon. Obfuscating it buys nothing.

What *is* defensible, and what customers actually pay for:

1. **The hosted template library** — curated, maintained device profiles and campaign
   templates that live server-side and are kept current.
2. **The audit log** — a verifiable record of what was written to which file, which is a
   compliance requirement for agencies, not a nice-to-have.
3. **Turnkey distribution** — signed, notarised builds that pass SmartScreen and Gatekeeper,
   with support and invoices a company can expense.
4. **Convenience** — batch scale, CSV-driven overrides, presets, no CLI.

Every architectural choice below optimises for protecting **1–4**, and explicitly declines to
spend effort protecting the mechanism itself.

---

## 3. Decision 1 — packaging: single app, separate app, or plugin

### Options considered

| | **A. Single app, Pro tab, closed-source plugin** | **B. Separate Pro app, duplicated code** | **C. One app, two editions, two repos** |
|---|---|---|---|
| Public repo contains paid logic | no, but contains the **plugin API** | no | no |
| Blueprint risk | **high** — a documented plugin interface tells a cloner exactly what to build | low | low |
| Code duplication | none | **high** — UI and processing diverge immediately | none — Pro imports upstream |
| Free-user upgrade path | in-place | re-download | re-download |
| Apache-2.0 boundary questions | fiddly (dynamic import boundary) | none | none |
| Build pipelines to maintain | 1 | 2 | 2 |
| Public repo churn | ongoing (API must stay stable) | none | **minimal** |

### Decision: **Option C**

```
suncoast-servers/NiRepurpose          (public, Apache-2.0)   -- unchanged free app
            |  pinned by tag (v0.3.0, v0.4.0, ...)
            v
suncoast-servers/NiRepurpose-Pro      (private, proprietary)
            |-- upstream/             git submodule or pip install from tag
            |-- pro/
            |     |-- injection/      templates, variable expansion, exiftool argfiles
            |     |-- entitlement/    license token, balance, job grants
            |     |-- payments/       PayRam checkout handoff (no API key)
            |     +-- ui/             Pro tab, wired into upstream's window
            +-- .github/workflows/    signed Pro build matrix
```

**Why C over A.** Option A's cost is not the code, it is the *commitment*: a plugin API in a
public Apache-2.0 repo is a stable contract we must not break, and it is simultaneously a
specification for cloning Pro. Option C gets the same "one codebase" benefit by having Pro
depend on the free app, rather than the free app depend on a plugin contract.

**Why C over B.** B duplicates `NiRepurpose.py` — 1,000+ lines of processing and UI that
would drift within two releases. C has exactly one implementation of the free behaviour.

### What the public repo needs for this — deliberately almost nothing

Option C requires **no plugin SDK** and **no paid logic** here. The only upstream change
worth making is small and genuinely useful to OSS forkers too:

- Allow `RepurposerApp` to accept optional extra UI sections and an optional post-process
  hook, so Pro can attach its tab without patching upstream source. Roughly 30–60 lines, no
  premium concepts, no license checks, no network calls.
- Keep `APP_VERSION` and the edition label readable so Pro can display `v0.4.0 Pro`.

If Ryan prefers **zero** upstream change, Pro can instead carry a thin vendored patch — at
the cost of a merge conflict on every upstream UI change. **Recommended: make the small hook.**

---

## 4. Decision 2 — licensing boundary

### 4.1 Apache-2.0 is not a problem

Apache-2.0 is permissive and explicitly allows proprietary derivative works. Pro may include
and modify this repo's code without publishing Pro's source, provided it:

- ships this repo's `LICENSE` and `NOTICE`,
- retains copyright and attribution notices,
- states that changes were made (a line in Pro's `NOTICE` is sufficient),
- does not use the project name or Ryan's marks in a way implying endorsement beyond fact.

The Apache-2.0 patent grant travels with the code and is unaffected.

### 4.2 Bundled FFmpeg is GPL — this is the real constraint

`NOTICE` states plainly: *"The bundled builds below are **GPL** builds."* `scripts/toolchain.json`
pins the gyan.dev **essentials** Windows build and Martin Riedl Linux/macOS builds. ExifTool
is dual Perl Artistic/GPL, and the Windows package bundles Strawberry Perl.

This does **not** block a proprietary Pro edition, for a specific reason worth recording:

> NiRepurpose never links FFmpeg. `repurpose_image()` / `repurpose_video()` invoke
> `ffmpeg` through `subprocess.run()` with an argv list. The Pro binary and the GPL binary
> are **separate programs communicating at arm's length** — aggregation, not a combined
> derivative work.

But distributing a GPL binary still carries obligations, whatever the licence of the program
shipped next to it. For **Pro Full** builds Ryan must:

1. **Keep FFmpeg and ExifTool as standalone executables**, invoked by `subprocess`. Never
   link, never embed them in the Python process, never statically combine. *(Today's code
   already satisfies this — do not regress it.)*
2. **Convey the licence texts** — GPL/LGPL for FFmpeg, Artistic/GPL for ExifTool, plus the
   Strawberry Perl licences already in `tools/exiftool_files/`.
3. **Make a written offer for corresponding source**, valid three years, or ship the source
   alongside. This is cheap for us: `scripts/toolchain.json` already records the exact
   upstream URL and SHA-256 for every binary, so "corresponding source" is satisfied by
   mirroring the matching source tarballs on the same host that serves Pro downloads, and
   linking them from Pro's `NOTICE`.

**Recommendation:** ship **Pro Full** with the written offer (a one-time ~half-day task:
mirror the source archives, add the offer text to `NOTICE`). The alternative — Pro Lite only,
requiring agency users to install FFmpeg themselves — removes the obligation but damages the
exact turnkey value proposition corporate buyers are paying for.

**Open question for Ryan:** confirm you are comfortable hosting the FFmpeg/ExifTool source
mirrors. If not, Pro v1 ships Lite-only and we revisit at v2.

### 4.3 Summary of the boundary

| Stays Apache-2.0, public | Proprietary, private |
|---|---|
| Bulk processing, naming modes, subfolders | Metadata **injection** engine and templates |
| Metadata **stripping** | Credit metering and license tokens |
| Themes, icons, settings | PayRam client and checkout handoff |
| Toolchain pins, fetch/verify, automation | Audit log and device-profile library |
| Release workflow for Lite/Full | Signed Pro build and distribution pipeline |
| Optional UI hook (§3) | Pro UI tab |

**Non-negotiable:** no PayRam key, webhook secret, signing key, or injection template library
is ever committed to `suncoast-servers/NiRepurpose`. The free tier stays fully functional for
the privacy/strip use case, with no nag screens and no crippling.

---

## 5. Decision 3 — distribution and trust

| | Free edition | Pro edition |
|---|---|---|
| Channel | GitHub Releases (unchanged) | Ryan-controlled HTTPS host |
| Trigger | `v*` tag on public repo | `v*` tag on private repo |
| Windows | unsigned (status quo) | **Authenticode signed** |
| macOS | unsigned (status quo) | **Developer ID signed + notarised** |
| Integrity | — | SHA-256 published next to each artifact |

Code signing is not optional for Pro. An unsigned paid download triggers SmartScreen and
Gatekeeper warnings, which is fatal for corporate buyers whose IT will simply block it. This
is a hard cost (an EV/OV certificate and an Apple Developer account) and is budgeted in §9.

Pro downloads should be served behind the entitlement service so a download URL can be tied
to a paying account — a mild deterrent and, more usefully, install telemetry for support. It
is **not** a security control; see §7.

---

## 6. Decision 4 — payment and credit flow

### 6.1 What PayRam gives us, and what it does not

From PayRam's published documentation. **Verify against Ryan's instance before Phase 1** —
some published pages are dated and the supported-chain list differs between sources.

| Capability | Detail |
|---|---|
| Create payment | `POST /api/v1/payment` with customer email, customer ID, USD amount |
| Response | `reference_id` and a **hosted checkout URL** |
| Auth | `API-Key` header; per-project keys issued from the dashboard |
| Status poll | `GET /api/v1/payment/reference/{id}` |
| Webhook | signed, `X-Payram-Signature`, HMAC-SHA256 over the **raw** body |
| Credit trigger | invoice status **`FILLED`** |
| Hosting | self-hosted, self-custody; Ryan runs the node on Hetzner |

**Two gaps shape the design:**

1. **No native subscriptions.** Recurring billing would have to be built at the application
   layer. We should not build it for v1.
2. **No per-user credit metering.** PayRam settles invoices; it has no concept of "this user
   has 240 generations left."

Both gaps land in the same place: a small service of our own.

### 6.2 The entitlement service

A minimal private service on the same Hetzner VPS, beside PayRam:

```
  NiRepurpose Pro (desktop)
        |
        |  1. POST /v1/checkout   { pack: "credits_500" }      [device token auth]
        v
  Entitlement service  --2. POST /api/v1/payment -->  PayRam   [API-Key, server-side only]
        |              <-- { reference_id, checkout_url } -----+
        |  3. returns checkout_url
        v
  App opens checkout_url in the system browser --> user pays in crypto
                                                        |
  Entitlement service <-- 4. webhook, status FILLED -----+
        |                 verify X-Payram-Signature (HMAC-SHA256, raw body,
        |                 constant-time compare, replay window)
        |  5. credit the account, write ledger entry
        v
  App polls GET /v1/balance  -->  { credits: 500, pass_expires: null }
```

**The desktop app never holds `PAYRAM_API_KEY` and never receives webhooks.** It holds only
its own device token. This single property removes the worst failure mode in the whole
design: a paid binary in the wild containing a live payment credential.

No standalone checkout web app is required for v1 — PayRam's hosted checkout page is the
entire payment UI, which matches issue #5's constraint.

### 6.3 Products and metering

| Product | Model | Notes |
|---|---|---|
| **Credit pack** | one-off invoice, e.g. 100 / 500 / 2,000 credits | never expires; simplest to reason about |
| **30-day pass** | one-off invoice, unlimited injections for 30 days | this *is* the "monthly cap"; no recurring billing needed |

**1 credit = 1 media file successfully injected.** Not per batch (unpredictable for the
user), not per minute of video (unpredictable for us). Failed files are not charged.

Metering is **server-authoritative**:

1. App requests a **job grant** for N files.
2. Service checks balance, decrements, writes a ledger row, returns a short-lived
   **Ed25519-signed grant** (nonce, file count, expiry).
3. App injects locally and reports completion; credits for failed files are returned.

**Offline grace.** Pass holders get a signed entitlement valid for a configurable offline
window (suggest 7 days) so an agency on a flaky connection is never blocked mid-shoot.
Credit-pack users need connectivity to draw a grant. Renewal is a reminder plus a one-click
new invoice — not a recurring charge.

---

## 7. Decision 5 — security and threat model

Written as an honest threat model, per issue #5's instruction that this not be "DRM theater."

| # | Threat | Mitigation | Residual risk |
|---|---|---|---|
| 1 | PayRam API key extracted from the shipped binary | Key never leaves the VPS; app holds only a device token (§6.2) | **Very low** |
| 2 | Forged webhook crediting a free account | HMAC-SHA256 over raw body, constant-time compare, timestamp replay window, idempotency on `reference_id` | **Low** |
| 3 | Replaying a job grant for free generations | Server-side nonce ledger, short TTL, one-shot redemption | **Low** |
| 4 | One paid build shared across an agency | Device token bound to account; concurrent-device cap with self-service reset | **Medium** — deliberately tolerated |
| 5 | **Patched binary with the license check removed** | **None that works.** Python bytecode is decompilable; PyInstaller is unpackable | **High — accepted** |
| 6 | Someone re-implements injection from scratch | None needed; the mechanism is public knowledge (§2.1) | **High — accepted** |
| 7 | Stolen device token | Revocation list, rotation on login, server-side ban | **Low** |
| 8 | Payment chargeback fraud | Crypto settlement is final | **N/A** |

### What we are explicitly not doing

We are **not** attempting protection that survives a determined reverse engineer. A Python
desktop app cannot win that fight, and obfuscation spend would come straight out of the
budget for things customers actually pay for (§2.1). Threats **5** and **6** are accepted in
writing.

This is a commercially sound position because the target buyer — an agency or corporation —
does not run cracked software on company machines. They need invoices, support, signed
binaries and an audit trail. Piracy by individuals who were never going to buy a seat costs
approximately nothing.

The controls above exist to make **honest** usage accurate (correct metering, correct
balances, no accidental overcharge) and to keep **payment infrastructure** safe. Those are
the goals; "unbreakable licensing" is not.

---

## 8. Metadata injection — feature outline (spec only, no implementation)

> Specification only. No injection code is proposed for merge in this repo at any point, and
> none anywhere until Ryan signs off.

### 8.1 Template model

A template is a named, versioned set of tag writes across EXIF, IPTC and XMP:

| Field | Example |
|---|---|
| `id`, `name`, `version` | `agency-campaign-q4`, v3 |
| `tags` | `Artist`, `Copyright`, `XMP:Creator`, `IPTC:Keywords`, `GPSLatitude`, … |
| `variables` | resolved per file at apply time |
| `scope` | images / videos / both |

**Variables:** `{date}`, `{time}`, `{index}`, `{basename}`, `{uuid}`, `{gps.lat}`,
`{gps.lon}`, plus sequences and bounded random ranges, so a batch gets plausible per-file
variation rather than 2,000 identical timestamps.

**Device profiles:** curated presets writing a mutually consistent set of
make / model / lens / software / exposure fields for a chosen device. Cross-field consistency
is the hard part and the main reason to maintain this server-side — the hosted-library value
from §2.1.

### 8.2 Batch application

- Apply a template to a selection; per-file overrides via **CSV import** (filename → values).
- Dry-run preview showing the resolved tag set for the first N files before writing.
- Implementation note: ExifTool `-@ argfile` for batch efficiency, `-config` for custom tags,
  reusing the existing `exiftool_argv()` / `subprocess_kwargs_no_window()` helpers so Pro
  inherits the no-console-popup and Perl-script handling already solved upstream.
- Ordering: injection runs **after** the existing encode step and **replaces** the
  `strip_all_metadata()` call rather than running alongside it.

### 8.3 Audit log

JSONL, one row per file: UTC timestamp, source path, SHA-256 before and after, template id
and version, resolved tags written, operator, job grant nonce. Exportable as CSV.

This is a **compliance feature, not telemetry** — it stays on the user's machine, is never
uploaded, and exists so an agency can answer "what did we write to this asset, and when."

### 8.4 Guardrails — required, not optional

Injecting capture metadata has a legitimate ceiling. Pro **must not**:

- forge or re-sign **C2PA / Content Credentials** provenance assertions,
- present fabricated capture data as cryptographically verifiable,
- advertise evasion of platform authenticity checks.

Pro **must** surface a plain-language notice that fabricated capture metadata is
inappropriate for evidentiary, insurance, journalistic or legal use. The audit log supports
this position. Agency and marketing use — consistent copyright, creator and campaign
tagging — is entirely legitimate and is the market being served; a product that markets
itself on deception attracts a different and far worse class of problem, including platform
and payment-processor risk.

---

## 9. Phased plan and effort estimate

Working days for one developer, excluding Ryan's review time.

| Phase | Scope | Est. | Gate |
|---|---|---|---|
| **0** | **This ADR** — direction, boundary, threat model | done | **Ryan's written approval on #5** |
| **1** | **Spike** — entitlement service skeleton, PayRam create-payment + webhook → credit, proven end to end with a CLI against Ryan's instance. No UI. | 3–5 | Ryan sees a real payment credit an account |
| **2** | Private repo, upstream pinned as dependency, Pro build matrix (unsigned), Pro tab shell | 3–4 | Pro builds on all platforms |
| **3** | Injection MVP — template model, variable expansion, batch apply, dry run, audit log | 5–7 | Injection correct on sample media |
| **4** | Monetisation UX — balance, buy credits/pass, job grants, offline grace | 3–4 | Full purchase → inject loop |
| **5** | Trust & distribution — code signing, notarisation, download host, receipts, GPL source mirror (§4.2) | 4–6 | Clean install, no OS warnings |
| | **Total** | **18–26 days** | |
| **P** | Public repo: optional UI hook + docs (§3) | 1–2 | normal PR into `main` |

**Phase 1 is the real decision point.** It is deliberately small and throwaway-able: if
PayRam's API does not behave as documented against Ryan's instance, we learn it in week one
for 3–5 days of spend, rather than after the Pro pipeline exists.

### Costs Ryan carries (not developer time)

Windows code-signing certificate (annual), Apple Developer Program (annual), Hetzner VPS
(already running), and a download host for Pro builds plus the GPL source mirror.

---

## 10. Secrets and environment variables Ryan provisions

**Names only — no values in this repository, ever.**

**Entitlement service (Hetzner VPS):**

| Variable | Purpose |
|---|---|
| `PAYRAM_BASE_URL` | PayRam instance endpoint |
| `PAYRAM_API_KEY` | per-project merchant key, `API-Key` header |
| `PAYRAM_WEBHOOK_SECRET` | verifies `X-Payram-Signature` |
| `ENTITLEMENT_DB_URL` | accounts, balances, ledger, nonces |
| `LICENSE_SIGNING_KEY` | Ed25519 **private** key signing grants and entitlements |
| `SESSION_SECRET` | device-token session signing |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | receipts and expiry reminders |

**Private Pro build pipeline (GitHub Actions secrets):**

| Variable | Purpose |
|---|---|
| `LICENSE_SIGNING_PUBKEY` | Ed25519 **public** key embedded in Pro — not secret |
| `WINDOWS_CODE_SIGN_CERT`, `WINDOWS_CODE_SIGN_PASSWORD` | Authenticode |
| `APPLE_DEVELOPER_ID_CERT`, `APPLE_DEVELOPER_ID_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_NOTARY_KEY` | signing and notarisation |
| `PRO_RELEASE_HOST`, `PRO_RELEASE_TOKEN` | upload of signed artifacts |

**Public repo (`suncoast-servers/NiRepurpose`): none of the above. No new secrets.**

---

## 11. Open questions — Ryan's input needed to close this ADR

1. **Pricing.** Credit pack sizes and USD prices; 30-day pass price. (§6.3 assumes the shape,
   not the numbers.)
2. **Accounts.** Email magic-link (recommended — least friction, no password storage) or
   username/password?
3. **GPL source mirror.** Comfortable hosting FFmpeg/ExifTool source archives so Pro can ship
   **Full**? If not, Pro v1 ships **Lite-only**. (§4.2)
4. **Pro download host.** Which host serves signed Pro builds?
5. **Licensing unit.** Per-seat, or per-organisation with a device cap? (§7, threat 4)
6. **PayRam instance.** Confirm base URL and which chains/stablecoins are enabled, so Phase 1
   targets reality rather than the public docs.
7. **Upstream hook.** Approve the small UI hook in the public repo (§3), or require Pro to
   vendor a patch instead?

---

## 12. Acceptance criteria for sign-off (issue #5)

- [x] ADR comparing **single app + closed-source module** vs **separate app** — §3
- [x] Trust/distribution: GitHub Releases vs signed Pro builds from a Ryan-controlled host — §5
- [x] Licensing boundary: Apache-2.0 here vs private repo / proprietary build — §4
- [x] Payment flow, high level: in-app credits, PayRam on Hetzner, no standalone checkout app — §6
- [x] Security: API auth, credit metering, honest threat model — §7
- [x] Metadata injection outline: templates, batch apply, audit log — spec only, no secrets — §8
- [x] Effort estimate and phased proposal (Phase 1 spike vs full product) — §9
- [x] Explicit list of env vars/secrets Ryan provisions, names only — §10
- [x] Clear recommendation with one-sentence rationale — §1
- [ ] **Ryan reviews and approves direction in writing (comment on #5)** ← remaining

---

## 13. Consequences

**If approved as written:**

- The public repo stays Apache-2.0, forkable, and free of paid logic — permanently.
- Free users are never degraded; stripping stays a first-class, unlimited feature.
- Ryan carries one extra build pipeline, two annual certificate costs, and a small service.
- We accept, in writing, that a determined reverse engineer can bypass Pro licensing (§7).

**If rejected in favour of Option A (plugin):** the public repo must maintain a stable plugin
API as a permanent public contract, which also documents how to clone Pro.

**If rejected in favour of Option B (separate app):** expect upstream drift within two
releases and roughly double the maintenance on shared processing and UI code.
