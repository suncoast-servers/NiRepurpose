# Architecture decision records

Durable records of **why** a significant technical direction was chosen — not how-to docs.
Day-to-day guidance lives in [`docs/`](../), [`AGENTS.md`](../../AGENTS.md) and
[`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-premium-tier-architecture.md) | Premium tier architecture: custom metadata, credits, PayRam | **Proposed** — awaiting Ryan's written approval on [#5](https://github.com/suncoast-servers/NiRepurpose/issues/5) |

## Statuses

| Status | Meaning |
|--------|---------|
| **Proposed** | Open for review. **No implementation may start.** |
| **Accepted** | Ryan approved in writing. Implementation may proceed. |
| **Superseded** | Replaced by a later ADR, which is linked from the header. |
| **Rejected** | Kept on purpose, so the reasoning is not relitigated. |

## Writing one

1. Copy the heading block from ADR-0001 (status, issue, author, decision owner, date).
2. Number sequentially: `NNNN-short-kebab-title.md`.
3. Lead with the recommendation and a one-sentence rationale — Ryan should be able to decide
   from the first screen.
4. Record the options you rejected and why. That is the part that is valuable in a year.
5. Open it as a PR against `main` like any other change. An ADR only becomes **Accepted**
   when Ryan says so in writing on the linked issue.
