# ADR 0008 — Versioning + release pipeline (semantic-release + AMO auto-publish)

- **Status**: Accepted
- **Date**: 2026-04-29
- **Deciders**: Mohamed (project owner)

## Context

Round E set up the **CI gates** (test, lint, format, e2e, coverage) but said nothing about how releases happen — how the repo gets a version, how a CHANGELOG gets written, and how the extension reaches Firefox users on AMO (addons.mozilla.org).

Round F closes that gap. Constraints in play:

- **AMO requires SemVer** (`MAJOR.MINOR.PATCH`) in `manifest.json` — the version scheme isn't a free choice.
- **Conventional Commits already enforced** (Round B + Round E commitlint workflow) — a tool that consumes them gets value for free.
- **Branch protection on `main` blocks direct pushes** (Round E) — any release tool that wants to commit a bumped version + CHANGELOG back to `main` needs a way through that gate.
- **`prod` GitHub Environment exists with required-reviewer protection** (Round E) — the production safety net is *already there*; release pipeline should plug into it instead of inventing a parallel gate.
- **Polyglot repo** — TS extension + Python backend + Python scripts. The user-facing artifact is the extension; backend and scripts are deployment internals.
- **One-person project today** but the goal is enterprise-pattern muscle memory ([feedback memory](../README.md)).

## Decision

### Versioning model — single repo SemVer

One version stream for the whole repo, advanced from Conventional Commits.

- **`extension/package.json`** is the source of truth for the version number.
- **`extension/manifest.json`** is auto-derived by WXT at build time from `package.json`'s `version` field — no separate bump.
- **`backend/`** and **`scripts/`** rely on the **git tag** as their version. No in-file bump in `pyproject.toml`. Their deployments are pinned to the tag, not to a file inside the project.
- The `MAJOR`/`MINOR`/`PATCH` semantics follow the Conventional Commits → semantic-release default mapping (`feat:` → minor, `fix:` → patch, `BREAKING CHANGE:` → major).

### Release tool — semantic-release on `main` only

`semantic-release` runs on every push to `main`. No pre-release channel from `develop`.

- Reads conventional commits since the last tag, decides if a bump is warranted.
- Bumps `extension/package.json` `version` field.
- Writes `CHANGELOG.md` at the **repo root** (single CHANGELOG, single version stream).
- Commits the changes back to `main` via a **GitHub App installation token** (see below).
- Creates the git tag (`v<version>`) and a GitHub Release with auto-generated notes.

semantic-release plugin chain:

```jsonc
// extension/.releaserc.json (added when extension/ scaffolds)
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/changelog",
      { "changelogFile": "../CHANGELOG.md" }
    ],
    [
      "@semantic-release/npm",
      { "npmPublish": false }
    ],
    [
      "@semantic-release/git",
      {
        "assets": ["package.json", "../CHANGELOG.md"],
        "message": "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}\n\n[skip ci]"
      }
    ],
    "@semantic-release/github"
  ]
}
```

Notes on the plugin chain:

- `@semantic-release/npm` with `npmPublish: false` is used **only to bump the version field in `package.json`** — we do not publish to npm.
- `@semantic-release/git` writes `CHANGELOG.md` to repo root (relative path `../CHANGELOG.md` from `extension/`) and commits with `[skip ci]` to avoid an infinite release loop.
- `@semantic-release/github` creates the GitHub Release and uploads any attached `.xpi` later (publish-amo job uses the release tag as its checkout ref).

### Commit-back authentication — GitHub App

`main` is branch-protected (Round E); semantic-release cannot push the version-bump + CHANGELOG commit using the default `GITHUB_TOKEN` (which respects branch protection). It needs an actor that bypasses protection in a controlled way.

**Choice: a dedicated GitHub App** ("rafmag-release-bot" — installed on this repo only) whose installation token is generated per-run via [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token).

- App permissions: `Contents: Read & Write`, `Pull requests: Read`, `Issues: Read & Write` (for release-note linking).
- Branch protection rule on `main` configured to allow this App's identity to bypass the "Require PR" rule (via *Bypassers* in the branch ruleset).
- Commits land in git history under the bot's name (visibly machine-authored), not under Mohamed's personal account.
- Token rotates automatically every hour — no manual PAT rotation.

Two secrets in the **`dev` GitHub Environment** (read by the `release` job):

| Secret | What |
|--------|------|
| `RELEASE_BOT_APP_ID` | The numeric App ID of rafmag-release-bot |
| `RELEASE_BOT_PRIVATE_KEY` | The App's PEM private key |

### `release.yml` workflow shape

Two jobs, with the `prod` environment review gate sitting between them:

```yaml
# .github/workflows/release.yml — added when extension/ scaffolds
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  ci-typescript:
    uses: ./.github/workflows/_test-typescript.yml
    with:
      project-path: extension

  ci-e2e:
    uses: ./.github/workflows/_e2e.yml
    with:
      extension-path: extension

  release:
    name: Release (semantic-release)
    needs: [ci-typescript, ci-e2e]
    runs-on: ubuntu-latest
    environment: dev
    permissions:
      contents: write
      issues: write
      pull-requests: write
    outputs:
      published: ${{ steps.semantic.outputs.new_release_published }}
      version: ${{ steps.semantic.outputs.new_release_version }}
    steps:
      - name: Generate App token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.RELEASE_BOT_APP_ID }}
          private-key: ${{ secrets.RELEASE_BOT_PRIVATE_KEY }}

      - name: Checkout (full history)
        uses: actions/checkout@v4
        with:
          token: ${{ steps.app-token.outputs.token }}
          fetch-depth: 0

      - name: Set up pnpm
        uses: pnpm/action-setup@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: extension/pnpm-lock.yaml

      - name: Install dependencies (frozen)
        working-directory: extension
        run: pnpm install --frozen-lockfile

      - name: Build extension
        working-directory: extension
        run: pnpm build

      - name: Run semantic-release
        id: semantic
        working-directory: extension
        env:
          GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}
        run: pnpm exec semantic-release

  publish-amo:
    name: Publish to AMO
    needs: [release]
    if: needs.release.outputs.published == 'true'
    runs-on: ubuntu-latest
    environment: prod # required reviewer gate (Round E)
    steps:
      - name: Checkout (release tag)
        uses: actions/checkout@v4
        with:
          ref: v${{ needs.release.outputs.version }}

      - name: Set up pnpm
        uses: pnpm/action-setup@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: extension/pnpm-lock.yaml

      - name: Install dependencies (frozen)
        working-directory: extension
        run: pnpm install --frozen-lockfile

      - name: Build production bundle
        working-directory: extension
        run: pnpm build

      - name: Sign + submit to AMO (listed channel)
        working-directory: extension
        env:
          WEB_EXT_API_KEY: ${{ secrets.AMO_JWT_ISSUER }}
          WEB_EXT_API_SECRET: ${{ secrets.AMO_JWT_SECRET }}
        run: pnpm exec web-ext sign --channel listed --source-dir .output/firefox-mv3
```

### Pipeline at a glance

```
PR merged into main
   │
   ▼
release.yml triggered
   │
   ├─ ci-typescript    ┐  reusable workflows from Round E
   └─ ci-e2e           ┘  must both pass before release proceeds
            │
            ▼
release  (env: dev, GitHub App token)
   • bump extension/package.json
   • write /CHANGELOG.md
   • commit back to main with [skip ci]
   • git tag v1.4.0
   • GitHub Release v1.4.0
            │
            ▼
publish-amo  (env: prod)
   ⏸  paused — required reviewer must approve
            │
            ▼
   • checkout v1.4.0
   • build production bundle
   • web-ext sign → AMO listed channel
```

### Secrets layout (final)

| Environment | Secret | Used by |
|-------------|--------|---------|
| `dev` | `GEMINI_API_KEY_DEV`, `FIREBASE_SERVICE_ACCOUNT_DEV` | test workflows (Round E) |
| `dev` | `RELEASE_BOT_APP_ID`, `RELEASE_BOT_PRIVATE_KEY` | `release.yml` → release job |
| `prod` | `GEMINI_API_KEY_PROD`, `FIREBASE_SERVICE_ACCOUNT_PROD` | (future) backend/scripts deploy |
| `prod` | `AMO_JWT_ISSUER`, `AMO_JWT_SECRET` | `release.yml` → publish-amo job |

## Alternatives considered

### release-please instead of semantic-release

Google's tool. Reads conventional commits, opens a *Release PR* on every merge to `main` containing the version bump + CHANGELOG; tag fires when the Release PR merges. **Considered + rejected** — semantic-release's auto-tag-on-merge model was preferred. Trade-off accepted: less review-gating at the tag step (the prod environment review gate on `publish-amo` is the safety net).

### changesets

Per-PR `.changeset/*.md` files describing the bump kind, aggregated by a "Version Packages" PR. **Rejected** — npm-ecosystem-centric, weaker support for our polyglot setup, adds a per-PR overhead step that contributors must remember.

### Manual versioning + CHANGELOG

Hand-edit `manifest.json`/`package.json` + `CHANGELOG.md` per release. **Rejected** — drifts under hackathon time pressure; defeats the point of having Conventional Commits enforced.

### Per-component versioning (`extension/1.4.0`, `backend/0.3.0`, ...)

Each component on its own version stream + CHANGELOG. **Rejected** — backend and scripts are deployment internals, not user-facing artifacts. Decoupling buys 3× release plumbing without delivering user value at hackathon scale. Off-ramp documented below.

### Pre-release channel from `develop`

`develop` merges produce `1.4.0-rc.1` tags; `main` cuts the real `1.4.0`. Lets you test on AMO's beta channel before promoting. **Rejected** — adds workflow complexity and a second `release.yml` trigger path. The prod-environment required-reviewer gate provides the safety property RC tags would. Accepted residual risk: a regression that passes CI + reviewer's eye reaches AMO immediately, with no AMO-side test channel between.

### Single job (`release` + `publish-amo` merged)

One job tags + uploads to AMO atomically. **Rejected** — defeats the purpose of having the prod environment. The two-job split is what makes the required-reviewer gate from Round E into a real gate.

### PAT (Personal Access Token) for commit-back instead of GitHub App

Store a fine-grained PAT as `GH_TOKEN` secret. **Rejected** — PATs are tied to a personal account (commits show under Mohamed's name, misleading); PATs expire and need manual rotation; PATs grant whatever scope they're issued, less granular than GitHub App permissions. GitHub App is the canonical enterprise pattern.

### Repo rulesets bypass actor (default `GITHUB_TOKEN`)

Configure a branch ruleset that lets `github-actions[bot]` bypass the "Require PR" rule. **Considered** — simplest setup, no app to install. **Rejected** — granting bypass to a generic `github-actions[bot]` actor means *any* workflow in this repo can push to `main`, not just the release workflow. The GitHub App's per-app identity gives finer-grained authorization (only the release-bot's installation token can bypass).

### `workflow_run` trigger (chain after `extension.yml`)

`release.yml` listens for `extension.yml` to complete successfully. **Rejected** — `workflow_run` makes the release workflow harder to trigger manually for re-runs, and the indirection makes failures harder to trace. The job-level `needs:` dependency on the reusable workflows in this same file is more direct.

### `workflow_dispatch` only (manual trigger)

Releases happen only when Mohamed clicks "Run workflow" in the Actions tab. **Rejected** — defeats the "every merge ships" automation premise. The required-reviewer gate on `publish-amo` already provides the human checkpoint where it matters (before AMO publish), without sacrificing the auto-tag step.

## Consequences

### Good

- **Zero-touch tags + CHANGELOG.** Every merge to `main` that has a `feat`/`fix`/breaking commit produces a tag, a GitHub Release, and a CHANGELOG entry — no human action.
- **Human gate where it matters.** `publish-amo` requires required-reviewer approval. The pipeline can't push a regression to real AMO users without an explicit click.
- **Polyglot version-bump dodge works.** semantic-release is npm-native; by making `extension/package.json` the source of truth and letting WXT derive `manifest.json`, we avoid the polyglot bump complexity. backend/scripts ride on the git tag.
- **Enterprise-pattern muscle memory.** GitHub App for commit-back, GitHub Environments for secret isolation, two-job pipeline with a review gate — exactly the shape large teams use.
- **Conventional Commits keep paying off.** Every author's commit messages now drive automatic release notes.

### Bad

- **Every meaningful merge to `main` cuts a release.** No batching ("ship a week's worth of fixes together"). If you want quieter releases, you'd switch to `workflow_dispatch` (off-ramp).
- **GitHub App setup is required ops** (~30 min one-time): create the App on GitHub, install it on the repo, add `RELEASE_BOT_APP_ID` + `RELEASE_BOT_PRIVATE_KEY` to the `dev` environment, configure branch ruleset bypass actor.
- **AMO API JWT setup required** (~10 min one-time): generate JWT credentials in your AMO developer account, add `AMO_JWT_ISSUER` + `AMO_JWT_SECRET` to the `prod` environment.
- **No AMO beta channel safety net.** With `main only`, a regression that passes CI + reviewer is published to AMO listed users immediately. Mitigations: rigorous CI (Round D ≥80% coverage gate), e2e on every PR, manual reviewer click at `publish-amo`.
- **CI runs twice on every merge.** Once on the PR (extension.yml/backend.yml/scripts.yml callers), once on `main` push (release.yml's `ci-typescript` + `ci-e2e` jobs). Cost: extra CI minutes; benefit: defense in depth — release.yml proves the merged commit actually passes everything.

### Neutral

- **`backend/` and `scripts/` versions are implicit** (git tag only, no `pyproject.toml` bump). Consumers of those components today are CI itself + the `release.yml` pipeline; both pin to a tag, not a file. Consequence: if you `pip install` from the repo as a dependency, you'd need a workaround to surface the version. Acceptable given today's consumers.
- **`extension/.releaserc.json` and `release.yml` are not yet on disk.** They scaffold when `extension/` does, matching the pattern from `extension.yml`/`backend.yml`/`scripts.yml`. The shape is locked here; the file is a transcription.
- **Bot-authored commits in git history.** `chore(release): 1.4.0` commits show up under the GitHub App bot's name. Some teams find this noisy; the alternative (PAT under personal account) is misleading.

## When we'd revisit this

- **Backend or scripts gain independent consumers** (e.g., the backend Cloud Function gets a separate package consumed by other repos). **Action:** switch to per-component versioning. semantic-release's monorepo support is awkward; this would likely also mean swapping to release-please (which natively handles polyglot monorepos).
- **A regression reaches AMO that should have been caught.** **Action:** add `develop`-channel pre-release (`1.4.0-rc.1` published to AMO beta channel); promotion `develop → main` becomes the "graduate to listed" step. New ADR amendment.
- **Release noise gets painful** (every merge cuts a release; you want batching). **Action:** switch trigger to `workflow_dispatch` only. Revisit Conventional Commits → release-notes mapping if commit-batching becomes the dominant flow.
- **GitHub App ownership becomes a coordination problem** (e.g., the App is tied to Mohamed's account, blocking handoff). **Action:** transfer the App to a GitHub Organization, or replace with a repo ruleset bypass actor. Document the migration in this ADR's amendment.
- **AMO publishing reliability problems** (signing flake, API rate limits). **Action:** retry logic in the publish job; manual fallback path documented in CONTRIBUTING.md.
- **Polyglot bump dodge breaks** (e.g., `pyproject.toml` versions are needed for backend pip-installable distribution). **Action:** add a `@semantic-release/exec` step that updates `backend/pyproject.toml` and `scripts/pyproject.toml` with `uv version --bump` or `tomlkit` script.
