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

## Conventions

The remaining conventions land in subsequent rounds:

- **Git workflow** (branching, commits, PRs) — Round B
- **Code style** (naming, formatter, linter) — Round C
- **Testing** — Round D
- **CI/CD** — Round E
- **Docs & governance** — Round F

This file gets updated as each round lands.

## Adding a new architectural decision

1. Copy `adr/_template.md` → `adr/00NN-short-title.md`.
2. Fill it in. Set `Status: Proposed`.
3. Add a row to `adr/README.md`.
4. When the decision is locked, flip `Status` to `Accepted`.

See `adr/README.md` for the rule of thumb on what deserves an ADR.
