# ADR 0009 — Governance: CODEOWNERS, ADR amendment policy, repo license

- **Status**: Accepted
- **Date**: 2026-05-04
- **Deciders**: Mohamed (project owner)

## Context

Rounds A–E locked the technical foundations (stack, git workflow, code conventions, testing, CI/CD); Round F.1 + F.2 (ADR 0008) locked the release pipeline. Round F.3 + F.4 closes the foundations sweep with the **governance** decisions — three small-but-load-bearing pieces that the prior rounds gestured at but never wrote down:

1. **Who reviews what.** Branch protection (Round E) requires a PR review on `main`/`develop`, but nothing today auto-routes that review to a specific person on a specific path. Today this is ceremonial (one contributor); the moment a second contributor joins it becomes a real safety property.
2. **How decisions evolve over time.** [`adr/README.md:12`](./README.md) already states the spirit ("ADRs are append-only — supersede, don't rewrite"), but the *edit-vs-supersede line* is undefined: is fixing a typo a supersession? Is adding a "When we'd revisit" trigger? The rule needs a sharp edge so it scales past 9 ADRs without bureaucracy.
3. **Repo license posture.** No `LICENSE` file exists. A public repo with no `LICENSE` defaults to **all rights reserved** under copyright law — but *implicitly*, which is a footgun: anyone who reads the code without realizing this is technically infringing, and there's no contact path for licensing inquiries. Decision needs to be locked + made visible.

Constraints:

- **One contributor today on a public GitHub repo.** Public visibility is for portfolio / hackathon submission, not for adoption.
- **No plan to open-source** the project; commercial direction is preserved as an option.
- **Goal: enterprise-pattern muscle memory** ([feedback memory](../README.md)) — lean toward canonical large-team shapes when the simpler version would deny the practice.
- **Append-only ADR convention** is already established (Round E set the precedent — ADR 0007 didn't replace ADR 0003, it just added).

## Decision

### CODEOWNERS — path-scoped, default-then-overrides

[`.github/CODEOWNERS`](../.github/CODEOWNERS) — owners file at the canonical GitHub-recognized path. Pattern: a default `*` line, then path-scoped overrides. Today every line names the same owner; the *shape* is what's load-bearing.

```
# Default — every file unless overridden below
*                       @mofach90

# Architecture decisions
/adr/                   @mofach90

# CI/CD + repo config
/.github/               @mofach90

# Component code
/extension/             @mofach90
/backend/               @mofach90
/scripts/               @mofach90

# Top-level governance docs
/CONTRIBUTING.md        @mofach90
/README.md              @mofach90
/CODEOWNERS             @mofach90
/LICENSE                @mofach90
```

**Branch-protection wiring** (already in place from Round E): `main` and `develop` require PR review. Once `CODEOWNERS` exists, GitHub automatically requests review from the listed owners on every PR touching their paths. The "Require review from Code Owners" branch-protection toggle gets flipped on at the same time the file lands.

**Self-review note.** Branch protection's "Require approval from someone other than the PR author" rule blocks self-merges by default. For a one-contributor project that would block all merges. Resolution: enable the "Allow specified actors to bypass required pull requests" rule with `@mofach90` as the bypass actor, **only on `main`** (not `develop`). The PR + CODEOWNERS auto-request still happens on every change; the self-merge becomes a single click instead of a hard block. When a second contributor joins, the bypass actor is removed and the rule becomes load-bearing.

### ADR amendment policy — edit narrowly, supersede broadly

Status lifecycle (locks the four states already gestured at in [`_template.md`](./_template.md)):

| Status | Meaning |
|---|---|
| **Proposed** | Under discussion. The decision isn't binding; the codebase doesn't yet reflect it. |
| **Accepted** | Locked. The codebase reflects it (or is on a path to). |
| **Superseded by ADR-00XX** | Replaced by a newer ADR. The new one's number is filled in; both ADRs stay in the index, both stay readable. |
| **Deprecated** | No longer relevant, no replacement (the constraint went away). Rare. |

**Edit-vs-supersede rule.** In the existing ADR file, *commit directly* (no new ADR needed) for any of:

- Typos, grammar, formatting.
- Broken or redirected links.
- **Status field flips** — `Proposed` → `Accepted`, `Accepted` → `Superseded by ADR-00NN`, `Accepted` → `Deprecated`.
- Adding entries to the **"When we'd revisit"** section as new evidence appears (a new trigger condition was discovered; not a change to existing triggers).
- Clarifying / expanding **Context** sections with new factual information that doesn't alter the decision.

*Must supersede with a new ADR* (write a new file, flip the old one to `Superseded by ADR-00NN`) for any change to:

- The **Decision** section — what was chosen.
- The **Alternatives considered** section — what was on the table and why it lost.
- The **Consequences** section — the trade-offs being accepted.
- The **Status** changing from `Accepted` back to `Proposed` (you've decided you weren't actually ready to commit; this is rare enough it deserves a new ADR explaining why).

**Cadence — trigger-based, not scheduled.** No quarterly review. ADRs get revisited when a "When we'd revisit" trigger fires (e.g., "Renovate PR volume becomes painful" from ADR 0007, or "Backend or scripts gain independent consumers" from ADR 0008). When a trigger fires: open a discussion → write a Proposed amendment ADR → review → flip to Accepted (which auto-supersedes the old one).

**Numbering.** Strictly sequential (`00NN`). Superseded ADRs **keep their number**; the replacement gets the next number. The supersession chain (`0003 → 0007 → ...`) is encoded in the Status field of each ADR. Never reuse a number. Never reorder.

**Authoring vs accepting.** Today both roles are Mohamed. When a second contributor joins: anyone can author an ADR (`Status: Proposed`). The **Deciders** field is the gate — flipping to `Accepted` requires every name in the Deciders list to approve via PR review. No formal RFC process beyond that.

### License — Proprietary / All Rights Reserved

A [`LICENSE`](../LICENSE) file at the repo root with an explicit "all rights reserved" notice and a `<contact>` placeholder for licensing inquiries.

**Posture:**

- **Code is visible** on the public GitHub repo for portfolio / hackathon-review purposes.
- **Code is not freely usable, modifiable, or redistributable.** Anyone wanting to use this code for any purpose needs explicit written permission.
- **AMO listing accepts this** — Mozilla allows proprietary extensions on AMO; the only restriction is you cannot describe a proprietary extension as "open source." The extension's listing copy will reflect that.
- **External contributions are not accepted by default.** A contributor PR before licensing is locked has ambiguous IP status and would not be merged until resolved (CLA or explicit license grant).

**Why proprietary, not OSS:**

- Hackathon submission today; commercial direction tomorrow is a real possibility worth preserving.
- Liberalizing later (proprietary → MIT / Apache-2.0) is straightforward — the copyright holder simply re-releases under the new license.
- Reversing later (OSS → proprietary) is **impossible** without consent of every contributor whose code is in the OSS-released history. Locking proprietary now keeps the option open in both directions.

**Contact placeholder rationale.** Public LICENSE files end up permanent in git history. Putting a personal email there invites spam scrapers; once landed it's not removable without a force-push that breaks every existing PR / clone. Decision: ship with `<licensing-contact>` placeholder, fill in via a separate (potentially private-repo-mirrored) commit if and when licensing inquiries become a real volume.

## Alternatives considered

### CODEOWNERS — flat single line

Just `* @mofach90` and nothing else. **Rejected** — same effort to type, materially less practice value, and doesn't auto-route review to the right person when components diversify (e.g., a future Python contributor owning `/backend/` doesn't need to review `/extension/` PRs).

### CODEOWNERS — per-file granularity

Owner per individual ADR, per individual workflow file, etc. **Rejected** — over-engineered, churn-heavy (every new ADR requires a CODEOWNERS update). Path-scoped is the canonical large-team shape; per-file is a smell.

### CODEOWNERS — at repo root, not `.github/`

GitHub looks for `CODEOWNERS` in three locations: repo root, `.github/`, or `docs/`. Repo root is also valid. **Rejected** — `.github/` is the most common location in large-team repos and keeps governance metadata out of the repo's "interesting" top-level surface. No functional difference.

### ADR amendment — strict append-only (never edit, always supersede)

Even typos require a superseding ADR. **Rejected** — bureaucratic, dilutes the supersession signal. When *every* change is a supersession, "supersedes ADR-X" carries no information about whether the decision actually changed.

### ADR amendment — anything goes, edit freely

Drop the supersession requirement entirely. **Rejected** — defeats the point of ADRs as a permanent decision log. The "why we changed our mind" trail disappears; future readers can't tell whether a section reflects the original decision or a quiet later revision.

### ADR cadence — quarterly review

Schedule a sweep every 3 months that walks every Accepted ADR and re-confirms / amends. **Rejected** — busywork without a trigger. The "When we'd revisit" sections already encode the right triggers; periodic review without a trigger generates either noise (rubber-stamp every ADR every quarter) or premature changes ("we have to revisit something this quarter, let's edit ADR 0005"). Off-ramp documented below if drift becomes a real problem.

### License — MIT

Maximum-adoption permissive OSS license. **Rejected** — no plan to open-source today; granting MIT rights when there are no consumers gives away optionality with no upside. MIT is a single `git mv` away if the project flips to OSS later; proprietary preserves both directions.

### License — Apache-2.0

Permissive + explicit patent grant + contributor patent retaliation. **Rejected** — same reasoning as MIT; the patent grant is valuable when there are downstream consumers, and there are none today. Apache-2.0 is the right pick *if and when* the project opens; locking it now is premature.

### License — MPL-2.0

Mozilla's license, thematic match with shipping on AMO. **Rejected** — file-level copyleft adds friction without corresponding benefit at hackathon scale, and locks the project into OSS posture immediately.

### License — no LICENSE file at all

Default to "all rights reserved" implicitly under copyright law. **Rejected** — the *behavior* is the same as proprietary, but readers don't *know* it's all-rights-reserved (most assume "no LICENSE" means "do what you want," which is the opposite of what's true). Explicit beats implicit; the LICENSE file is the visible signal.

### License contact — personal email in the LICENSE

Drop `mohamed-islem.ayari@cloudpilots.com` directly into the file. **Rejected** — public LICENSE files are permanent in git history; once landed, scrubbing requires a force-push that invalidates every existing clone. Email-in-public-repo invites spam scraping. Placeholder is the safer default; can be filled in at first real licensing inquiry, by which point the spam exposure is intentional.

### Full governance pack — CODE_OF_CONDUCT.md + SECURITY.md + issue templates

Adopt Contributor Covenant, write a security disclosure policy, scaffold GitHub issue templates. **Rejected (deferred)** — these are append-only files, no decisions to lock. CoC has no audience (single contributor); SECURITY.md needs a deployed backend before vulnerability reports become meaningful; issue templates need real issue volume to shape. Each is a one-line follow-up PR when the trigger fires.

## Consequences

### Good

- **Review discipline becomes a platform property.** CODEOWNERS auto-requests the right reviewer on every PR — no remembering, no manual `@mention`. Today ceremonial; the moment a second contributor joins, real.
- **Edit-vs-supersede rule is sharp.** Future contributors (and future-Mohamed) can answer "do I edit or write a new ADR?" by looking at *which section is changing*, not by judgment call.
- **Trigger-based ADR review beats scheduled review.** No periodic make-work; real changes still get formally captured because every Accepted ADR carries its own revisit triggers.
- **License posture is explicit.** A reader of the public repo knows immediately what they can and can't do, and where to ask for permission.
- **Optionality preserved in both directions.** Proprietary can liberalize to OSS later (one-author re-release); the reverse path (OSS → proprietary) would be effectively impossible. Locking proprietary now keeps both doors open.
- **Foundations sweep closes.** "Conventions still to lock" in `CONTRIBUTING.md` becomes empty; the next round is code, not docs.

### Bad

- **CODEOWNERS on a one-person repo creates self-review notification noise.** Every PR Mohamed opens auto-requests Mohamed's review. Resolved by the bypass-actor branch-protection rule, but it's an extra setting to maintain.
- **Public-repo + proprietary is non-obvious to casual readers.** Most readers see "public GitHub repo" and assume "free to use." The LICENSE file makes the posture *visible*, not *enforced* — enforcement requires legal action, which is impractical at hackathon scale. Acceptable: portfolio-visibility outweighs casual-misuse risk.
- **No CLA in place.** If an external contributor opens a PR before relicensing or CLA is set up, the IP status of their contribution is ambiguous and the PR can't be merged cleanly. Mitigation today: CONTRIBUTING.md notes that external PRs are not accepted yet; future trigger documented in "When we'd revisit."
- **Liberalizing the license later requires intentional re-release.** Not a one-line change; need to re-publish the repo under the new license, update CONTRIBUTING, possibly add a CLA. Acceptable: option preservation > switching cost.
- **Status-flip-as-edit can hide a meaningful change.** A maintainer flipping `Accepted` → `Deprecated` is technically just a status edit per the rule, but `Deprecated` is a real decision. Mitigation: the *commit message* for a Deprecated flip should explain why. Not enforced by tooling, just convention.

### Neutral

- **CODEOWNERS lives at `.github/CODEOWNERS`.** Alternatives are repo root or `docs/`; `.github/` is canonical. No functional difference.
- **No CODE_OF_CONDUCT.md, no SECURITY.md, no issue templates.** Each is a one-line PR away when the trigger fires; not absent on principle, just not yet useful.
- **License contact is a placeholder.** Until a real licensing inquiry appears, the placeholder is the maintenance-light choice. First real inquiry can fill it in.
- **Bypass-actor rule on `main`** means `@mofach90` can bypass required PRs. Today: makes self-merge possible. Tomorrow (second contributor): a setting to remove deliberately, not a backdoor.

## When we'd revisit this

- **Second contributor joins** → CODEOWNERS becomes load-bearing. Action: add their handle to relevant paths, remove `@mofach90` from the bypass-actor list on `main`, update the **Deciders** field on future ADRs to include them.
- **Decision to open-source the project** → flip LICENSE to MIT or Apache-2.0 (Apache-2.0 is the recommended pick — explicit patent grant), update `CONTRIBUTING.md` with a contribution-license clause, possibly add a CLA bot if external contributions are expected. New ADR amendment.
- **External contributor opens a PR before relicensing** → block-merge until contributor signs a CLA or explicitly grants license under the proprietary terms. Add CLA-bot integration. New ADR amendment.
- **AMO review process requests source-license attestation** → confirm Mozilla's process accepts proprietary; document any AMO-side license disclosure required for store listing.
- **ADR amendment volume becomes unwieldy** (many supersessions per quarter) → either the architectural foundation is too unstable (root cause: revisit early ADRs) or the supersession rule is too coarse (consider allowing in-place edits to **Alternatives considered** without a new ADR). New ADR amendment.
- **ADR / reality drift becomes a real problem** (multiple ADRs reference deprecated tools or moved files, but no triggers fired) → add a scheduled "ADR audit" issue (quarterly), Renovate-style dashboard listing every "When we'd revisit" trigger that may have fired. Counter-decision to the current "trigger-based only" rule.
- **Licensing inquiries arrive** → fill in `<licensing-contact>` placeholder with a dedicated alias (e.g., `licensing@<domain>`) rather than a personal email; document the alias in CONTRIBUTING.md.
- **The `@mofach90` bypass-actor rule gets accidentally inherited** when a second contributor joins (because nobody removed it) → audit branch protection settings as part of the new-contributor onboarding checklist.
