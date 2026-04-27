# ADR 0005 — Code conventions (formatter, linter, naming, editor baseline)

- **Status**: Accepted
- **Date**: 2026-04-26
- **Deciders**: Mohamed (project owner)

## Context

With the Git workflow locked in Round B, the next layer is "what does well-formatted, well-linted code look like in this repo" and "what does my editor do automatically when I press save." This is the layer enforced *before* a commit lands rather than discovered in code review.

Constraints driving the decision:

- **Two languages.** Python (`backend/`, `scripts/`) and TypeScript (`extension/`) — tooling is per-language.
- **One contributor today on Zed**, possibly more later on different editors. The baseline must work editor-agnostically; the Zed-specific layer is a bonus, not a hard dependency.
- **Stretch goal: enterprise-pattern muscle memory** ([feedback memory](../README.md): canonical large-team versions over minimum-viable shortcuts).
- **CI enforcement is Round E.** This round picks the tools and writes the configs; the pre-commit hooks and CI gates land later.

## Decision

### Formatters and linters

| Language | Formatter | Linter | Config lives in |
|----------|-----------|--------|-----------------|
| Python   | `ruff format` | `ruff check` | `pyproject.toml` (per project: `backend/`, `scripts/`) |
| TypeScript | `prettier` | `eslint` | `.prettierrc` + `eslint.config.js` (in `extension/`) |

**Python — `ruff` for both.** Single tool, single config block, ~100× faster than the legacy black + isort + flake8 stack. Same vendor (Astral) as `uv`, so one toolchain end-to-end on the Python side. Modern default for new projects in 2025+.

**TypeScript — `prettier` + `eslint`.** Dominant 2020s pairing. Industry-standard for ~7 years; first-class IDE/CI integration; `eslint`'s plugin ecosystem (a11y, security, import-order, react if needed) is the value-add `prettier` doesn't try to replace.

### Naming conventions

The language-mandated parts (`snake_case` for Python, `camelCase` for TypeScript) are non-decisions — `ruff` and `eslint` will reject violations. The decisions are the bits *outside* what the formatter automatically enforces:

| Concept | Python | TypeScript |
|---------|--------|------------|
| Variables / functions | `snake_case` | `camelCase` |
| Classes / types | `PascalCase` | `PascalCase` |
| Constants | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| File names | `snake_case.py` (PEP 8) | **`kebab-case.ts`** |
| Folder names | `kebab-case` | `kebab-case` |
| Test files | **`test_<module>.py`** | **`<module>.test.ts`** |
| Private members | `_leading_underscore` | `#privateField` or convention |
| Branches (locked Round B) | `<type>/<short-kebab-desc>` | same |

The three **bolded** rows are this round's actual picks; the rest is language standard.

### EditorConfig (`.editorconfig` at repo root)

Editor-agnostic baseline read by Zed, VS Code, JetBrains, vim, neovim, Emacs, Sublime, GitHub's web view, and most other editors:

- `charset = utf-8`
- `end_of_line = lf`
- `insert_final_newline = true`
- `trim_trailing_whitespace = true`
- `indent_style = space`
- `indent_size = 4` for Python files; `2` for TS / JSON / YAML / TOML
- `trim_trailing_whitespace = false` for Markdown (two trailing spaces = `<br>`)
- `indent_style = tab` for `Makefile` (Make requires tabs)

### Zed editor settings (`.zed/settings.json`)

Committed at repo root. Pins:

- `format_on_save: "on"` (global)
- Python → `ruff` as language-server formatter; `source.organizeImports.ruff` + `source.fixAll.ruff` as code actions on format
- TypeScript / TSX / JavaScript / JSON → `prettier` as formatter; `source.fixAll.eslint` as code action on format
- Markdown → `format_on_save: "off"` (prettier rewrites tables in surprising ways; format on demand, not on save)

Non-Zed users get `.editorconfig` + the per-project tool configs (`pyproject.toml`, `.prettierrc`, `eslint.config.js`); they're free to wire up their own editor.

## Alternatives considered

### Python: `black` + `ruff` (split tooling)

Black for formatting, ruff for linting. **Rejected.** Black has the longer track record (7 years vs ruff-format's 1) and is battle-tested at Meta/Microsoft scale, but ruff has crossed the line from "exciting newcomer" to "default for new Python projects in 2025+." Single-vendor (Astral) toolchain with `uv` is a tangible benefit. If `ruff format` ever bites us with an edge-case difference from black, swapping back is a one-line config change.

### Python: `black` + `isort` + `flake8` (legacy three-tool)

**Rejected.** Three tools, three configs, ~50× slower than ruff, being phased out everywhere. No one starts a 2026 Python project on this stack.

### TypeScript: `biome` (all-in-one)

Rust-based, single config, very fast, aiming to replace prettier+eslint together. **Rejected** because it's not yet the enterprise canonical pick — plugin ecosystem is smaller, eslint's mature plugin world (a11y, react, import-order, security rules) doesn't have a complete biome equivalent yet, and most senior TS engineers reach for prettier+eslint by default. Worth revisiting in 12–18 months.

### TypeScript file naming: `camelCase`

`autoSeek.ts` matches the primary export symbol exactly. **Rejected** because case-mismatch bugs between macOS/Windows (case-insensitive filesystems) and Linux CI (case-sensitive) are a real footgun, and `kebab-case` is the canonical large-team TS pattern, especially in framework-driven codebases (which WXT is). Folder names and branch names are already kebab-case; consistency wins.

### Test file naming: `*.spec.ts`

Mocha / Karma / Angular-legacy convention. **Rejected** because Vitest (Round D's likely pick) and Jest both default to `*.test.ts`, and the spec-vs-test split is fading outside Angular shops. No reason to swim upstream.

### Don't commit editor settings (`.editorconfig` only)

Every contributor configures their own editor. Editor-agnostic and respects personal preferences. **Rejected** because the shared format-on-save guarantee is worth more than purity here — it removes an entire class of "format violation slipped through to PR" bugs at zero cost to non-Zed users. Adopting the canonical large-team pattern.

### Commit `.vscode/settings.json` instead of `.zed/`

Mohamed uses Zed, not VS Code. Pre-building VS Code config for hypothetical future contributors violates the "don't design for hypothetical future requirements" principle. **Rejected.** A future VS Code contributor can add their own settings file then.

## Consequences

### Good

- **Zero-config-on-clone for Mohamed.** `pnpm install` + `uv sync` + open in Zed → format-on-save with ruff and prettier just works. No "did you remember to enable format-on-save?" bug class.
- **Editor-agnostic baseline.** Anyone joining on VS Code / JetBrains / vim gets correct indentation, line endings, and charset from `.editorconfig` automatically; format-on-save is a 30-second per-editor setup, not an "I have to re-derive the project conventions" task.
- **Single Astral toolchain on Python.** `uv` for deps + `ruff` for format/lint = one vendor, one mental model, one place to file bugs.
- **Tooling enforcement, not human discipline.** Style debates are settled by config, not code review. Round E will make this CI-enforced; until then, format-on-save is the local gate.
- **Test discovery is automatic.** `pytest` finds `test_*.py` by default; Vitest finds `*.test.ts` by default. No custom glob patterns to maintain.

### Bad

- **`.zed/settings.json` is dead weight for non-Zed contributors.** A future VS Code user reads it and ignores it — minor noise in `git status` if they accidentally edit it. Mitigated by `.gitignore`-ing per-user editor state files (`.idea/`, `.vscode/` future) but committing the project-level `.zed/settings.json` we agreed on.
- **`ruff format` is younger than `black`.** A subtle formatting difference *could* surface as a surprise. Recovery: a one-line config change to swap formatters; ruff's lint side stays.
- **Two configs for TypeScript** (`.prettierrc` + `eslint.config.js`). The integration story is mature (`eslint-config-prettier` disables eslint rules that conflict with prettier) but is one more thing to keep in sync if either tool changes its defaults.

### Neutral

- **Per-project `pyproject.toml` for `backend/` and `scripts/`.** Each Python project has its own; ruff config is duplicated. Acceptable given Round A's "no `shared/` until Rule of Three" decision — when scripts and backend share enough config to warrant DRY-ing, we extract to a root config or a shared package.
- **Markdown not auto-formatted.** Prettier on Markdown can rewrite tables in unexpected ways and we have a lot of hand-laid documentation. Manual format on demand only.

## When we'd revisit this

- **`ruff format` bites on a real edge case.** **Action:** swap to `black` for the format phase, keep `ruff` for lint. One-line `pyproject.toml` change.
- **`biome` reaches enterprise canonical status** (large eslint plugins port over; major framework defaults switch). **Action:** evaluate consolidating to biome; new ADR amendment if migrated.
- **Second contributor joins and uses VS Code / JetBrains.** **Action:** add `.vscode/settings.json` or `.idea/` configs alongside the existing `.zed/`; do not replace.
- **Markdown formatting drift becomes a problem.** **Action:** add a `markdownlint` pre-commit step instead of turning prettier-on-save back on (markdownlint is structural, prettier is layout-rewriting).
