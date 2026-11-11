# NiRepurpose — product specification

**Owner:** [@TheDevWhoSaysNi](https://github.com/TheDevWhoSaysNi)  
**Organization:** [suncoast-servers](https://github.com/suncoast-servers)

## Positioning

Open-source **desktop** tool for bulk repurposing images and videos for social posting: encode tweaks, metadata stripping, organized output folders.

## Editions (target)

| Edition | License | Audience | Capabilities |
|---------|---------|----------|----------------|
| **NiRepurpose** (this repo) | Open source (Apache-2.0) | Everyone | Bulk processing, **strip** metadata, Lite + Full releases |
| **Premium / Pro** (TBD) | **Not open source** | Agencies, mass posters, corporations | **Inject** or template custom metadata, usage metering, paid credits |

Premium implementation may live in a **separate private repository** or a proprietary plugin/binary — decided in architecture issue. This public repo must remain forkable without leaking paid logic or payment keys.

**Proposed direction:** [ADR-0001 — Premium tier architecture](adr/0001-premium-tier-architecture.md) recommends one app in two editions built from two repositories (public free, private Pro). **Proposed, not accepted** — no premium or payment code starts until Ryan approves in writing on [#5](https://github.com/suncoast-servers/NiRepurpose/issues/5).

## Ryan-owned infrastructure (premium)

- **PayRam** on **Hetzner VPS** for crypto payments (nominal fee TBD: per-job credits and/or monthly cap).
- Pricing and policy finalized by Ryan; contractor proposes technical integration only.

## Non-goals in the public repo

- PayRam API secrets, webhook signing keys, or proprietary metadata injection algorithms committed to git.
- DRM that breaks legitimate OSS users; free tier stays fully functional for privacy/strip use case.

## Issue tracker

Delivery breakdown: milestone **[NiRepurpose enhancements](https://github.com/suncoast-servers/NiRepurpose/milestone/1)**, epic **[#6](https://github.com/suncoast-servers/NiRepurpose/issues/6)**, issues **#2–#5**.
