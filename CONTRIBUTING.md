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
- `release.yml` — semantic-release on `main` (Round F)

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

## Conventions still to lock

The remaining conventions land in subsequent rounds:

- **Docs & governance** (CHANGELOG, semver, CODEOWNERS, ADR cadence, release.yml workflow) — Round F

This file is updated as each round lands.

## Adding a new architectural decision

1. Copy `adr/_template.md` → `adr/00NN-short-title.md`.
2. Fill it in. Set `Status: Proposed`.
3. Add a row to `adr/README.md`.
4. When the decision is locked, flip `Status` to `Accepted`.

See `adr/README.md` for the rule of thumb on what deserves an ADR.
