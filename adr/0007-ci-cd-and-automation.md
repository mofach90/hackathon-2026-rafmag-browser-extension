# ADR 0007 — CI/CD & automation (workflows, hooks, deps, secrets)

- **Status**: Accepted
- **Date**: 2026-04-27
- **Deciders**: Mohamed (project owner)

## Context

Rounds A–D produced conventions (tech stack, Git workflow, code style, testing). This round wires the **gates** that make those conventions unbypassable rather than aspirational:

- A pre-commit hook layer that catches violations before the commit lands.
- A GitHub Actions CI layer that catches anything the hooks missed and enforces the coverage gate from Round D.
- An automated dependency-update layer so the lockfiles don't rot.
- Branch protection + secrets management so production keys aren't reachable from arbitrary workflows.

Constraints:

- **One contributor today on a public-or-private GitHub repo** — GitHub-native tooling is the default.
- **Stretch goal: enterprise-pattern muscle memory** ([feedback memory](../README.md)).
- **Round D locked**: hard ≥80% line coverage gate, Playwright Firefox e2e on every PR, Firebase Emulator for backend/scripts integration tests.
- **Round B locked**: PR-only changes; commits follow Conventional Commits; develop is the default branch.

## Decision

### CI workflow shape — reusable workflows + per-component callers

`.github/workflows/` layout:

```
.github/workflows/
├── _test-python.yml        # Reusable: uv sync → ruff → pytest --cov (≥80%)
├── _test-typescript.yml    # Reusable: pnpm install → prettier → eslint → tsc → vitest --coverage
├── _e2e.yml                # Reusable: Playwright Firefox e2e on built extension
├── commitlint.yml          # Standalone: validates PR commit messages
├── extension.yml           # Caller — calls _test-typescript w/ extension/, then _e2e (added when extension/ scaffolds)
├── backend.yml             # Caller — calls _test-python w/ backend/ (added when backend/ scaffolds)
├── scripts.yml             # Caller — calls _test-python w/ scripts/ (added when scripts/ scaffolds)
└── release.yml             # Round F — semantic-release on main pushes
```

**E2E timing**: every PR targeting `develop` or `main`, in parallel with fast jobs (so unit/integration give early feedback while e2e gates the merge).

**Path filters** on per-component callers: e.g. `extension.yml` triggers on `paths: [extension/**, .github/workflows/extension.yml, .github/workflows/_test-*.yml, .github/workflows/_e2e.yml]`.

**Status checks required for merge** (configured in branch protection, see below):
- `test (extension)` from `extension.yml`
- `test (backend)` from `backend.yml`
- `test (scripts)` from `scripts.yml`
- `e2e` from `extension.yml` → `_e2e.yml`
- `commitlint` from `commitlint.yml`

### Pre-commit hooks — `pre-commit` framework

Single `.pre-commit-config.yaml` at repo root. Hooks:

| Layer | Hook | What it checks |
|-------|------|----------------|
| File hygiene | `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-json`, `check-toml`, `check-merge-conflict`, `mixed-line-ending` | Catches dumb bugs before they ever reach a diff |
| Python | `ruff` (lint with `--fix`) + `ruff-format` | Locked Round C |
| TypeScript / JSON / YAML | `prettier` (local hook, runs `pnpm exec prettier`) — added when `extension/` scaffolds | Locked Round C; Markdown excluded per ADR 0005 |
| TypeScript | `eslint` (local hook, runs `pnpm exec eslint`) — added when `extension/` scaffolds | Locked Round C |
| Secret scanning | `gitleaks` | No `GEMINI_API_KEY` ever lands in a commit |
| Commit message | `conventional-pre-commit` (commit-msg stage) | Matches Round B's Conventional Commits format |

Two install steps after clone:
```bash
pre-commit install                       # main (pre-commit) hooks
pre-commit install --hook-type commit-msg # commit-msg hook for conventional-pre-commit
```

Mirrored in CI as the same hooks via `pre-commit run --all-files` job (defense in depth — caught locally first, caught again in CI if hooks were bypassed with `--no-verify`).

### Dependency updates — Renovate

`.github/renovate.json5` config:

- Schedule: Mondays before 9am (one batched PR window per week, no daily noise).
- **Group minor + patch** updates per ecosystem (`npm`, `pep621`/Python, `github-actions`) into single PRs.
- **Auto-merge patch updates** after CI green — these almost never break anything; auto-merge keeps the lockfile fresh without busywork.
- **Major updates** stay as individual PRs with `major-update` label, manual review required.
- Vulnerability alerts always create immediate PRs (off-schedule), labelled `security`.
- GitHub Actions pinned to commit SHAs (Renovate auto-updates the SHAs) — supply-chain hardening.
- Dashboard issue enabled (Renovate posts a single tracking issue summarizing all open update PRs).

### Branch protection

Configured via GitHub repo settings (manually, in Round F migration; documented here so the settings are reproducible).

**`main`:**
- Require PR before merge.
- Require all required status checks pass.
- Require branches up-to-date before merge.
- Disallow direct push.
- Disallow force push.
- Require signed commits *(deferred to Round F)*.

**`develop`:**
- Same as main minus signed-commit requirement.

**Required status checks** (the list above): per-component test jobs, e2e, commitlint.

**Auto-merge** enabled at repo level (so Renovate patch-updates can land without manual click).

### Secrets — GitHub Environments (dev + prod)

Two environments configured in repo settings:

| Environment | Used by | Secrets stored | Protection rules |
|-------------|---------|----------------|------------------|
| `dev` | `_test-python.yml` (when integration tests need a fixture-only Gemini key), e2e workflow | `GEMINI_API_KEY_DEV` (low-quota dev key), `FIREBASE_SERVICE_ACCOUNT_DEV` (emulator/dev project) | None — readable by any workflow |
| `prod` | `release.yml` (Round F: AMO publish, prod Cloud Functions deploy) | `GEMINI_API_KEY_PROD`, `FIREBASE_SERVICE_ACCOUNT_PROD`, `AMO_JWT_ISSUER`, `AMO_JWT_SECRET` | **Required reviewer = Mohamed** before any job can read prod secrets |

Workflow jobs declare `environment: prod` to gate themselves — the deploy/publish jobs in `release.yml` are the only ones with `environment: prod`. Test jobs reference `environment: dev` (or no environment at all for tests using only fixtures).

**Why two environments rather than one:** isolates prod credentials behind a manual approval gate; matches the canonical large-team production-secret discipline. Today the "required reviewer" is yourself — feels redundant — but the pattern is the load-bearing piece. When a second contributor joins, the gate becomes a real safety property at zero workflow change.

## Alternatives considered

### CI shape: single workflow + path filters (recommended originally)

One `.github/workflows/ci.yml` with multiple jobs and `paths:` filters per job. **Rejected** in favor of reusable workflows for enterprise-practice value. Trade-off accepted: more workflow files to maintain (each language's setup steps live in a single reusable file, but caller files duplicate the trigger config) in exchange for the pattern that scales to large monorepos. The `When we'd revisit` section names the off-ramp.

### CI shape: single workflow, run everything always

Simplest, but wastes CI minutes on every change. **Rejected** — Playwright e2e is too expensive to run on docs-only PRs.

### CI shape: multiple workflows per component (no reusables)

`extension-ci.yml`, `backend-ci.yml`, `scripts-ci.yml` each fully self-contained. **Rejected** — duplicates setup steps (uv install, pnpm install, Node setup) across files. Reusable workflows DRY this up.

### Hooks: husky

Node-flavored, easy in JS-ecosystem repos. **Rejected** — awkward for the Python-side hooks (ruff, etc.) since husky's hook runner doesn't have a polyglot plugin ecosystem; pre-commit framework does.

### Hooks: lefthook

Go binary, fast, single config. **Rejected** — smaller plugin ecosystem than pre-commit; less common at large polyglot shops; the speed advantage (lefthook is faster than pre-commit) doesn't matter for our hook count.

### Deps: Dependabot

GitHub-native, zero install. **Rejected** — one PR per package by default creates PR fatigue within weeks; Renovate's grouping + auto-merge is meaningfully more powerful and is the enterprise canonical.

### Deps: Nothing / manual

**Rejected** — security advisories accumulate silently; lockfiles rot.

### Secrets: repo-level secrets only

Single set of GitHub Actions secrets; no dev/prod split. **Rejected** in favor of Environments for the production-isolation property and the practice value, even though for one-deploy-target it feels ceremonial today.

### Status checks: only "all green" required, no per-job requirement

Lighter to configure. **Rejected** — explicit per-job requirements make it visible in the UI which gate a PR is failing; faster to triage.

## Consequences

### Good

- **Conventions become unbypassable.** Code style (ruff, prettier, eslint), commit format (conventional-pre-commit + commitlint), coverage (≥80%), e2e — all enforced before merge.
- **Two layers of defense.** Hooks catch violations locally (fast feedback, free CI minutes); CI re-runs the same checks (catches `--no-verify` bypasses).
- **Reusable workflows scale.** When a second component of the same language scaffolds (e.g., a second Python service), it's a 5-line caller file pointing at `_test-python.yml`. New language? Add a `_test-<lang>.yml` reusable.
- **Renovate keeps deps fresh without effort.** Patch updates auto-merge after CI; minor updates batch weekly; majors get human review. The dashboard issue gives a single place to see "what's pending."
- **Production secret isolation.** Even on a one-person project, prod credentials sit behind a manual approval gate that a second contributor can't accidentally exfiltrate.
- **Practice value.** Daily reps on the exact CI/CD shape large product teams ship: reusable workflows, per-environment secrets, Renovate, pre-commit, commitlint.

### Bad

- **More workflow files to maintain.** Reusable + caller = 4–5 files for what `ci.yml` could do in 1. Off-ramp documented in `When we'd revisit`.
- **Reusable workflow debugging is painful.** When a reusable workflow fails, the error surface jumps between caller and reusable; harder to read than a flat workflow.
- **Pre-commit hooks slow down `git commit`.** First-run install pulls hook environments (one-time, minutes). Steady state: a few seconds per commit. Acceptable.
- **Renovate PR volume can spike.** Even with grouping, weeks where many ecosystems update produce 3–5 PRs in one Monday batch. Mitigated by `prConcurrentLimit`.
- **Auto-merge of patch updates means a malicious patch could land without review.** Mitigated by: required CI green (which runs the test suite); Renovate's `osvVulnerabilityAlerts` for known-CVE blocks; `vulnerabilityAlerts.enabled = true`. Risk acceptance: the velocity is worth the residual exposure for a non-financial side project.
- **GitHub Environments add friction to release workflows.** Manual reviewer click on every `release/*` deploy. By design.

### Neutral

- **CI minutes consumed.** GitHub free tier covers public repos with no limit; private repo on free tier has 2,000 min/month. Round F revisits if we go private and start hitting limits.
- **Per-environment secrets are duplicated** (`GEMINI_API_KEY_DEV` and `GEMINI_API_KEY_PROD`). Acceptable cost of the isolation.

## When we'd revisit this

- **Reusable-workflow maintenance tax exceeds the practice value** (you find yourself editing 3 caller files for every reusable change). **Action:** collapse to a single `ci.yml` + path filters (Round E's recommended option). New ADR amendment.
- **Renovate PR volume becomes painful** despite grouping. **Action:** stretch the schedule to every other Monday, or move to `dependencyDashboardOnly` mode (only opens PRs when you ask via the dashboard).
- **Pre-commit hooks become slow enough to skip** (commits regularly take >10s). **Action:** profile which hook is slow; consider lefthook for the same hook set if pre-commit overhead is the bottleneck.
- **CI minutes start hurting** (private repo, plan limits). **Action:** move e2e to a nightly + release-branch-only schedule; keep unit/integration on every PR.
- **A second contributor joins.** **Action:** the prod-environment required-reviewer rule starts paying real safety dividends. No workflow change needed.
- **Auto-merged patch breaks production.** **Action:** disable patch auto-merge (`packageRules` → `automerge: false`), revert to manual review for all updates. Document the incident in this ADR's amendment.
