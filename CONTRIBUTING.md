# Contributing to `rafmag-browser-extension`

The single source of truth for **how we work** on this project. Short on purpose — point to an ADR for the *why* of any decision.

## Tech stack

| Component | Language | Tooling | Lives in |
|-----------|----------|---------|----------|
| Browser extension | TypeScript | [WXT](https://wxt.dev) + [pnpm](https://pnpm.io) | `extension/` |
| Cloud Functions backend | Python 3.12 | [uv](https://docs.astral.sh/uv/) (export to `requirements.txt` for deploy) | `backend/` |
| One-shot scripts (backfill, etc.) | Python 3.12 | uv | `scripts/` |
| Database | Firestore (Native) | Firebase Admin SDK | — |
| LLM | Gemini API (`gemini-3.1-pro-preview`) | `google-genai` Python SDK | — |

Why this stack: see [`adr/0003-tech-stack-and-repo-structure.md`](./adr/0003-tech-stack-and-repo-structure.md). Why these external services: see [`adr/0001-backend-stack.md`](./adr/0001-backend-stack.md), [`adr/0002-data-storage.md`](./adr/0002-data-storage.md).

## Repo layout

```
.
├── extension/           # Firefox MV3 extension (WXT + TS)
├── backend/             # Cloud Functions Gen 2 (Python)
├── scripts/             # One-shot CLI scripts (Python)
├── adr/                 # Architecture decision records
├── brainstorming/       # Discovery docs (problem → solution → scope → constraints)
├── experiments/         # Empirical validation runs
├── .github/             # CI workflows, PR + issue templates
├── CONTRIBUTING.md      # This file
└── README.md            # Project elevator pitch
```

Each buildable component (`extension/`, `backend/`, `scripts/`) ships its own `README.md` with local "how to run / how to test" instructions.

## Local setup

> **Note:** the codebase folders are scaffolded as Round A through F decisions land. Steps below describe the *target* setup once code exists.

**Prerequisites**

- Python 3.12+ (`brew install python@3.12` or `pyenv install 3.12`)
- Node.js 20+ (`brew install node` or use `nvm`)
- `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `pnpm` (`corepack enable pnpm` — ships with modern Node)

**Per-component setup**

```bash
# Extension
cd extension
pnpm install
pnpm dev          # WXT dev server with Firefox auto-reload

# Backend
cd backend
uv sync           # install deps from uv.lock
uv run pytest

# Scripts
cd scripts
uv sync
uv run python backfill.py
```

## Git workflow

We follow **Git Flow** branching with **Conventional Commits** messages and a standard PR template. Full reasoning in [`adr/0004-git-workflow.md`](./adr/0004-git-workflow.md).

### Branches

**Long-running:**

- `main` — production. Tagged at every release.
- `develop` — integration. Default branch.

**Short-lived** (`<type>/<short-kebab-desc>`):

| Type | Off | Into | Used for |
|------|-----|------|----------|
| `feature/*` | `develop` | `develop` | New user-visible feature |
| `bugfix/*` | `develop` | `develop` | Non-urgent fix |
| `docs/*` | `develop` | `develop` | Documentation only |
| `chore/*` | `develop` | `develop` | Tooling / deps / config |
| `release/v<x.y.z>` | `develop` | `main` AND `develop` | Release prep |
| `hotfix/v<x.y.z>` | `main` | `main` AND `develop` | Emergency prod fix |

### Merge strategy

- **Squash merge** for `feature` / `bugfix` / `docs` / `chore` → linear history on `develop`.
- **Merge commit** (no squash) for `release/*` / `hotfix/*` → preserves the release moment.

### Commit messages — Conventional Commits

```
<type>(<scope>): <subject>

<optional body>

<optional footer>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `ci`, `build`, `revert`.

**Scopes:** `extension`, `backend`, `scripts`, `adr`, `brainstorming`, `experiments`. Add new scopes here as the codebase grows.

**Rules:**

- Subject in **imperative mood** (`add`, not `added`), no trailing period, ≤ 72 chars.
- Body wrapped at 100 chars.
- Breaking changes: append `!` after the scope and add a `BREAKING CHANGE:` footer.

**Examples:**

```
feat(extension): auto-seek to first show segment on rafmag video load
fix(backend): handle 404 when Firestore document missing
docs(adr): add ADR 0004 for git workflow
chore(scripts): bump google-genai to 0.8.4

feat(extension)!: rename episodeSegments to showSegments

BREAKING CHANGE: API now returns showSegments instead of episodeSegments.
```

### Pull requests

Every change opens a PR. The description follows the template at [`.github/PULL_REQUEST_TEMPLATE.md`](./.github/PULL_REQUEST_TEMPLATE.md) — GitHub fills it in automatically. Required sections: **Why**, **What changed**, **Type**, **How to verify**, **Checklist**.

Self-merge is allowed (one-person project), but the description still gets filled in — that's the durable "why" log.

## Code conventions

Full reasoning in [`adr/0005-code-conventions.md`](./adr/0005-code-conventions.md).

### Formatters & linters

| Language   | Formatter      | Linter       | Config                                  |
|------------|----------------|--------------|-----------------------------------------|
| Python     | `ruff format`  | `ruff check` | `pyproject.toml`                        |
| TypeScript | `prettier`     | `eslint`     | `.prettierrc` + `eslint.config.js`      |

Format-on-save is pinned in [`.zed/settings.json`](./.zed/settings.json) for Zed users. Non-Zed editors pick up the indent / line-ending baseline from [`.editorconfig`](./.editorconfig) and the language-level configs from each project.

### Naming

| Concept                | Python                       | TypeScript          |
|------------------------|------------------------------|---------------------|
| Variables / functions  | `snake_case`                 | `camelCase`         |
| Classes / types        | `PascalCase`                 | `PascalCase`        |
| Constants              | `UPPER_SNAKE_CASE`           | `UPPER_SNAKE_CASE`  |
| File names             | `snake_case.py`              | `kebab-case.ts`     |
| Folder names           | `kebab-case`                 | `kebab-case`        |
| Test files             | `test_<module>.py`           | `<module>.test.ts`  |
| Private members        | `_leading_underscore`        | `#privateField`     |

### Editor baseline

[`.editorconfig`](./.editorconfig) at the repo root sets UTF-8, LF line endings, final newline, trim trailing whitespace, and per-language indentation (4-space Python / 2-space TS / JSON / YAML / TOML; tabs preserved in `Makefile`; trailing whitespace preserved in `*.md` because it encodes `<br>`).

## Testing

Full reasoning in [`adr/0006-testing-strategy.md`](./adr/0006-testing-strategy.md).

### Pyramid shape (per component)

| Component | Unit | Integration | E2E |
|-----------|------|-------------|-----|
| `extension/` | **Heavy** — pure logic | Light — DOM via `happy-dom` | Playwright + real Firefox |
| `backend/`   | Medium               | **Heavy** — Firebase Emulator + Gemini fixtures | Sparse smoke per release |
| `scripts/`   | Medium               | **Heavy** — Firebase Emulator + fake input | N/A |

### Frameworks

| Layer | Tool |
|-------|------|
| TS unit + component | Vitest (with `happy-dom` for DOM tests) |
| TS extension e2e | Playwright (Firefox) |
| Python unit + integration | pytest + `pytest-asyncio` |
| Firestore in tests | Firebase Emulator Suite |
| Gemini in tests | Recorded fixtures (`vcrpy` or hand-rolled JSON) |

### Coverage

Hard **≥80% line coverage** gate in CI per project. Allowed exclusions: pure entry-point glue, defensive `assert`s, type-only stubs. Not allowed: business logic, error handling on the happy path, prompt construction, response parsing. Exclusions live in tool config with a one-line "why."

## CI/CD & automation

Full reasoning in [`adr/0007-ci-cd-and-automation.md`](./adr/0007-ci-cd-and-automation.md).

### Pre-commit hooks

After cloning, run once:

```bash
pre-commit install                        # main hooks
pre-commit install --hook-type commit-msg # Conventional Commits validator
```

Hooks: file hygiene + ruff (Python format/lint) + gitleaks (secret scanning) + conventional-pre-commit (commit message format). Prettier and eslint hooks are wired as local hooks once `extension/` scaffolds.

### CI workflows

Located in `.github/workflows/`. Reusable workflows + per-component callers:

- `_test-python.yml` — uv sync → ruff → pytest with ≥80% coverage gate
- `_test-typescript.yml` — pnpm install → prettier → eslint → tsc → vitest with ≥80% coverage gate
- `_e2e.yml` — Playwright Firefox e2e on the built extension
- `commitlint.yml` — validates PR commits against Conventional Commits + scope enum
- `extension.yml` / `backend.yml` / `scripts.yml` — caller workflows (added when each component scaffolds)
- `release.yml` — semantic-release on `main` push → AMO auto-publish (shape locked in ADR 0008; file ships when `extension/` scaffolds)

### Dependency updates

[Renovate](https://docs.renovatebot.com) configured at [`.github/renovate.json5`](./.github/renovate.json5). Schedule: Mondays before 9am Europe/Paris. Minor + patch grouped per ecosystem. Patch updates auto-merge after CI green; majors require manual review.

### Secrets

Two GitHub Environments configured at the repo level:

| Environment | Used by | Protection |
|-------------|---------|------------|
| `dev` | Test workflows, e2e | None (any workflow can read) |
| `prod` | `release.yml` only | Required reviewer = repo owner |

Prod secrets (`GEMINI_API_KEY_PROD`, AMO publishing keys, prod Firebase service account) are unreachable from anything but the release workflow.

### Branch protection

`main` and `develop` both require: PR before merge, all status checks pass, branch up-to-date, no direct push, no force push. Required checks: per-component `test (...)` jobs, `e2e (firefox)`, `commitlint`. Configured via GitHub repo settings (settings reproduced in the ADR).

## Releasing

Full reasoning in [`adr/0008-release-pipeline.md`](./adr/0008-release-pipeline.md).

### Versioning

- **Single repo SemVer.** One version stream, declared in `extension/package.json`.
- WXT auto-derives `extension/manifest.json` `version` from `package.json` at build time.
- `backend/` and `scripts/` use the **git tag** as their version — no in-file bump.

### Release flow

```
merge to main
   ↓
release.yml CI gate (re-runs _test-typescript + _e2e)
   ↓
release job (env: dev)
   • semantic-release reads conventional commits since last tag
   • bumps extension/package.json
   • writes /CHANGELOG.md
   • commits back to main via GitHub App token
   • creates v<x.y.z> tag + GitHub Release
   ↓
publish-amo job (env: prod) — paused until required reviewer approves
   • signs + uploads .xpi to AMO listed channel
```

### Conventional Commits drive everything

The release version is computed from commit types since the last tag:

| Commit type prefix | Bump |
|--------------------|------|
| `fix:` | patch (`1.4.0` → `1.4.1`) |
| `feat:` | minor (`1.4.0` → `1.5.0`) |
| any commit with `BREAKING CHANGE:` footer or `!` after scope | major (`1.4.0` → `2.0.0`) |
| `chore:`, `docs:`, `test:`, `style:`, `refactor:`, `ci:`, `build:` | no release |

If no commit warrants a release since the last tag, semantic-release exits cleanly with no tag.

### Manual override — skipping a release

To merge without triggering a release, put `[skip release]` in the merge commit body, or land the change with only `chore:`/`docs:`/`test:` types.

### One-time operational setup (before the first release)

These are owner-side ops, not in code. Track them in the repo's launch checklist:

1. **Create a GitHub App** named `rafmag-release-bot`, install on this repo only.
   - Permissions: `Contents: Read & Write`, `Pull requests: Read`, `Issues: Read & Write`.
   - Generate a private key (PEM); store the App ID + PEM in the **`dev`** GitHub Environment as `RELEASE_BOT_APP_ID` + `RELEASE_BOT_PRIVATE_KEY`.
2. **Configure the `main` branch ruleset** to allow this App as a *bypass actor* for the "Require pull request" rule. Without this, semantic-release's commit-back fails.
3. **Generate AMO API JWT credentials** at [https://addons.mozilla.org/developers/addon/api/key/](https://addons.mozilla.org/developers/addon/api/key/). Store as `AMO_JWT_ISSUER` + `AMO_JWT_SECRET` in the **`prod`** GitHub Environment.
4. **Verify** by pushing a `feat:` commit to `main` (after `extension/` scaffolds): release job tags + opens a release; publish-amo job pauses for your approval click.

## Governance

Full reasoning in [`adr/0009-governance.md`](./adr/0009-governance.md).

### Code ownership

[`.github/CODEOWNERS`](./.github/CODEOWNERS) auto-requests review on every PR touching matching paths. Today every line names `@mofach90`; the *shape* (path-scoped, default-then-overrides) is what's load-bearing for when a second contributor joins.

Branch protection on `main` and `develop` requires CODEOWNER review. To allow self-merge while there's only one contributor, `@mofach90` is configured as a *bypass actor* for the "Require pull request" rule on `main` only. When a second contributor joins, the bypass actor is removed and the rule becomes load-bearing without any code change.

### License

[`LICENSE`](./LICENSE) — **proprietary, all rights reserved**. The repo is publicly visible on GitHub for portfolio / hackathon-review purposes; the code itself is not freely usable, modifiable, or redistributable without explicit written permission.

External contributions are not accepted by default — a CLA or explicit license grant would need to be in place first. AMO publishing of proprietary extensions is permitted by Mozilla; the listing copy must not describe the extension as "open source."

### ADR amendment policy

| Status | Meaning |
|---|---|
| Proposed | Under discussion. Codebase doesn't yet reflect it. |
| Accepted | Locked. Codebase reflects it. |
| Superseded by ADR-00XX | Replaced by a newer ADR (number filled in). Both stay in the index. |
| Deprecated | No longer relevant, no replacement. Rare. |

**Edit in place** (commit directly to the existing ADR file): typos, broken links, formatting, status-field flips, additions to **When we'd revisit**, factual additions to **Context**.

**Must supersede** (write a new ADR, flip the old to `Superseded by ADR-00NN`): any change to **Decision**, **Alternatives considered**, or **Consequences**.

ADRs are revisited when a "When we'd revisit" trigger fires — no scheduled cadence. Numbering is gapless and never reused; superseded ADRs keep their number.

## Adding a new architectural decision

1. Copy `adr/_template.md` → `adr/00NN-short-title.md`.
2. Fill it in. Set `Status: Proposed`.
3. Add a row to `adr/README.md`.
4. When the decision is locked, flip `Status` to `Accepted`. (To *change* a previously-Accepted decision, see the ADR amendment policy in **Governance** above — most changes require a new ADR, not an edit.)

See `adr/README.md` for the rule of thumb on what deserves an ADR.
