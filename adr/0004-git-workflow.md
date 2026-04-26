# ADR 0004 — Git workflow (branching, commits, pull requests)

- **Status**: Accepted
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

The repo needs a single rule for how branches are named and routed, what commit messages look like, and what every PR must say. Even with one contributor, these rules pay off as durable history (PRs as the "why" log), as input to release tooling (auto-CHANGELOG, semantic versioning), and as muscle memory for enterprise practice.

Constraints driving the decision:

- **Solo contributor today, possibly more later.** The workflow shouldn't change shape if a second person joins.
- **Stretch goal: practice with patterns used in large company repos** ([feedback memory](../README.md): Mohamed wants enterprise-pattern muscle memory, not just minimum-viable shortcuts).
- **AMO releases need clean changelog input.** Each Mozilla submission requires human-readable release notes — auto-generation from commits is a real win.
- **Rolling single release.** No parallel-version maintenance burden; the workflow doesn't have to support that, but should not actively prevent it.

## Decision

Adopt the canonical **Git Flow** branching model, **Conventional Commits with scopes** for messages, and a **standard PR template** as the description schema for every pull request.

### Branching — Git Flow

**Long-running branches:**

- `main` — production. Every commit is tagged `v<x.y.z>`. Updated only by merging `release/*` or `hotfix/*` branches.
- `develop` — integration / current state of work. Default GitHub branch.

**Short-lived branches** (named `<type>/<short-kebab-desc>`):

| Type | Branched from | Merged into | Used for |
|------|---------------|-------------|----------|
| `feature/*` | `develop` | `develop` | New user-visible feature |
| `bugfix/*` | `develop` | `develop` | Non-urgent bug fix |
| `docs/*` | `develop` | `develop` | Documentation only (extension to canonical Git Flow) |
| `chore/*` | `develop` | `develop` | Tooling, deps, config (extension to canonical Git Flow) |
| `release/v<x.y.z>` | `develop` | `main` AND `develop` | Release prep — version bump + last-mile fixes only |
| `hotfix/v<x.y.z>` | `main` | `main` AND `develop` | Emergency production fix |

**Merge strategy:**

- Squash-merge for `feature` / `bugfix` / `docs` / `chore` → clean linear `develop` history.
- True merge commit (no squash) for `release/*` / `hotfix/*` → preserves the release moment for changelog tools.

**Solo-dev concessions:**

- Self-merge PRs allowed.
- Branch protection on `main` and `develop` (no direct pushes — enforced via GitHub branch protection rules in Round E).

### Commit messages — Conventional Commits with scopes

Format:

```
<type>(<scope>): <subject>

<optional body — what and why, not how>

<optional footer — BREAKING CHANGE: …, Closes #N, Co-Authored-By: …>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `ci`, `build`, `revert`.

**Scopes**: `extension`, `backend`, `scripts`, `adr`, `brainstorming`, `experiments`. (Extend as the codebase grows; document new scopes in `CONTRIBUTING.md`.)

**Rules:**

- Subject in **imperative mood** ("add", not "added"), no trailing period, ≤ 72 chars.
- Body wrapped at 100 chars.
- Breaking changes marked with `!` after scope **and** a `BREAKING CHANGE:` footer.
- `commitlint` enforces the format in CI (set up in Round E).

### Pull request template

Stored at `.github/PULL_REQUEST_TEMPLATE.md`. Sections (in order):

1. **Why** — motivation. Link to ADR / open question / brainstorming doc when applicable.
2. **What changed** — 1–3 bullets in plain English.
3. **Type of change** — checkbox list mirroring Conventional Commit types.
4. **How to verify** — concrete steps per affected component (extension / backend / scripts).
5. **Screenshots / recordings** — required for extension UI changes.
6. **Checklist** — branch name format, commit format, target branch correct, tests, lint, docs updated.
7. **Migration notes** — only for `BREAKING CHANGE`.
8. **Linked** — `Closes #N`, `Implements ADR-XXXX`, etc.

## Alternatives considered

### GitHub Flow (recommended, declined for practice value)

`main` always shippable, short-lived `<type>/<desc>` branches, PR per change, no `develop` branch, no release/hotfix machinery. Simpler, matches what most senior product teams ship today (the original Git Flow author publicly recommends GitHub Flow for projects without parallel-version support — and we don't have that). **Rejected** because Mohamed explicitly chose Git Flow over GitHub Flow for enterprise-pattern practice value, and the cost of the extra ceremony is acceptable on a one-person project.

### Trunk-based development

Branches live hours, not days. Feature flags hide unfinished work in `main`. Best velocity at scale, requires strong CI gating every push. **Rejected** because the CI maturity isn't in place yet (Round E destination) and the feature-flag overhead would be premature for a one-person project.

### Commit-to-main

No branches, push direct to `main`. Maximum velocity, zero PR audit trail. **Rejected** because the durable "why" log via PR descriptions is a load-bearing benefit; losing it is not worth the saved seconds.

### Conventional Commits without scopes (`<type>: <subject>`)

Cleaner, slightly less typing. **Rejected** because scopes give us a free filter (`git log --grep "(extension)"`) and pair with the branch-naming convention. Cost is low (one parenthesized word per commit).

### gitmoji

Emoji as type prefix. Visual, fun. **Rejected** because tooling support (commitlint, semantic-release) is partial, AMO release notes don't render emojis well in their changelog UI, and it's not the dominant enterprise pattern.

### Minimal PR template (Summary + Test plan only)

Faster to fill. **Rejected** because the "Why" section is the most load-bearing piece and it isn't in the minimal template. The standard template's ~1-minute fill cost is small relative to the documentation value.

## Consequences

### Good

- **Durable why-history.** PR descriptions and Conventional Commit messages combine into a searchable log. Six months later, "why did we add X?" is a `git log --grep` or a GitHub search away.
- **Auto-tooling unlocks.** `commitlint` rejects malformed commits in CI. `semantic-release` writes `CHANGELOG.md` and bumps version automatically from commit history. AMO release notes generate themselves.
- **Clean release moment.** `release/*` branches make the AMO submission boundary explicit — `main` always reflects exactly what's published.
- **Branch type is self-documenting.** `feature/extension-auto-seek` tells you what it is and where it goes without opening it.
- **Enterprise practice.** Mohamed gets daily reps on the workflow shape used in many large-team repos.

### Bad

- **Double-merge tax.** Every release and hotfix has to be merged into both `main` and `develop`. Forgetting the back-merge is the most common Git Flow bug; mitigated by a checklist item in the release process.
- **`main` lags `develop`.** What's on AMO and what's in active development live in different branches. Easy to confuse "deployed" with "current"; mitigated by tagging every `main` commit with its version.
- **PR target confusion possible.** Most PRs target `develop`; only `release/*` and `hotfix/*` target `main`. The PR template checklist enforces this.
- **More ceremony per change.** A one-line typo fix still goes through `docs/typo` → PR → review → squash-merge. Accepted as the cost of the workflow.

### Neutral

- The branch type vocabulary (`feature`, `bugfix`, `docs`, `chore`, etc.) is identical to the Conventional Commit type vocabulary. One thing to learn, used in two places.

## When we'd revisit this

- **Multiple parallel versions become required** (e.g. Firefox v1.x maintenance while v2.0 is in development). **Action:** Git Flow already handles this — no change. Possibly add `support/*` branches.
- **CI matures enough for trunk-based** (every push runs full extension + backend + script tests in < 2 minutes; feature flags in place for unfinished work). **Action:** evaluate the simplification trade-off; new ADR if migrated.
- **Commit lint rejection rate becomes painful** (you're rewriting commits more than writing them). **Action:** relax to Conventional Commits without scopes, document in this ADR's amendment.
- **A second contributor joins.** **Action:** no workflow change; extend `CODEOWNERS` (added in Round F).
