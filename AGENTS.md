# Cran Code

> Forked from [MoonshotAI/cran-code](https://github.com/MoonshotAI/cran-code). This project is being maintained independently by the NLPark-Cran team for the crys.tt2.li collaborative coding platform.

## Project identity constraints (CRITICAL — do not drift)

### Branding rule
- **Frontend (user-visible)**: ALL Kimi/Kimi Code branding must be replaced with `Cran` / `Cran Code`.
  - HTML titles, logo alt text, brand component names, banner ASCII art, CLI help text, API docstrings.
  - localStorage/sessionStorage keys: use `cran_` prefix (e.g. `cran_auth_token`, `cran-theme`).
  - Custom event names: use `cran:` prefix (e.g. `cran:config-update`).
- **Backend API requests (MUST preserve)**: `USER_AGENT` in `src/kimi_cli/constant.py` must stay as `KimiCLI/{version}`.
  - This is required for compatibility with the Kimi Token Plan backend.
  - Do NOT rename `get_user_agent()` or change its return format.
- **Internal Python identifiers**: backend class names like `KimiCLI`, `KimiCLIRunner`, `KimiCLISession` do NOT need to be renamed unless they leak to the frontend.

### What NOT to change
- `src/kimi_cli/constant.py:get_user_agent()` → must return `f"KimiCLI/{get_version()}"`.
- LLM ProviderType enum value `kimi` in API schemas → this is a provider key, not branding.
- Package name `cran-code` and CLI entry command `kimi` → keep as-is until an explicit migration decision is made.
- User config path `~/.cran/config.toml` and share dir `~/.cran/` → keep for now to avoid breaking existing sessions.

## Quick commands

### Development
- `make prepare` — sync deps for all workspace packages and install git hooks
- `make format` / `make check` / `make test` / `make ai-test`
- `make build` / `make build-bin`
- If running tools directly, use `uv run ...`.

### Update (current workflow)
```bash
uv tool upgrade cran-code --no-cache
```

### Start web UI (current workflow)
```bash
cran web --no-open --public
```

For crys.tt2.li deployment, use:
```bash
cran web --host 0.0.0.0 --port 5494 --public --no-open \
  --allowed-origins "https://crys.tt2.li"
```

## Project overview

Cran Code is a Python CLI agent for software engineering workflows, forked from Kimi Code CLI. It supports:
- Interactive shell UI
- Web UI (the primary focus for crys.tt2.li collaboration)
- ACP server mode for IDE integrations
- MCP tool loading

## Tech stack

### Backend
- Python 3.12+ (tooling configured for 3.14)
- CLI framework: Typer
- Async runtime: asyncio
- LLM framework: kosong
- MCP integration: fastmcp
- Logging: loguru
- Package management/build: uv + uv_build; PyInstaller for binaries
- Tests: pytest + pytest-asyncio; lint/format: ruff; types: pyright + ty
- Web server: FastAPI + uvicorn

### Frontend (current)
- React 19 + TypeScript 5.9
- Vite 7
- Tailwind CSS v4
- shadcn/ui + Radix UI primitives
- AI SDK v5 (`@ai-elements`)
- State: Zustand, SWR
- Code highlighting: Shiki, CodeMirror
- Diagrams: Mermaid, XYFlow

### Frontend (evolution target — 2025/2026)
We are evaluating modern frontend tech for the web UI rewrite. Candidates from nearby projects (e.g. `cran-picture-book`) and the ecosystem:
- **Svelte 5 + Runes** — fine-grained reactivity, smaller bundle, `.svelte.ts` stores
- **Vite 8** — faster builds, LightningCSS by default, Rolldown integration path
- **GSAP** — advanced scroll-driven animations and UI transitions
- **Yjs + WebSocket** — real-time collaborative editing for multi-user sessions
- **PartyKit / Cloudflare Durable Objects** — lightweight real-time backends
- Consider **Tauri 2** if a desktop client is ever needed

## Architecture overview

- **CLI entry**: `src/kimi_cli/cli/__init__.py` (Typer) parses flags and routes into `KimiCLI` in `src/kimi_cli/app.py`.
- **App/runtime setup**: `KimiCLI.create` loads config (`src/kimi_cli/config.py`), chooses a model/provider (`src/kimi_cli/llm.py`), builds a `Runtime` (`src/kimi_cli/soul/agent.py`), loads an agent spec, restores `Context`, then constructs `KimiSoul`.
- **Agent specs**: YAML under `src/kimi_cli/agents/` loaded by `src/kimi_cli/agentspec.py`.
- **Tooling**: `src/kimi_cli/soul/toolset.py` loads tools by import path, injects dependencies, and runs tool calls.
- **Core loop**: `src/kimi_cli/soul/kimisoul.py` is the main agent loop.
- **Web UI backend**: `src/kimi_cli/web/` — FastAPI app, session store, auth middleware, config/sessions/work_dirs API.
- **Web UI frontend**: `web/` — React SPA. Build output is copied to `src/kimi_cli/web/static/` for bundling.

## Web UI development workflow

1. Edit frontend code in `web/src/`.
2. Run type check: `cd web && npx tsc -b --noEmit`
3. Build: `cd web && NODE_OPTIONS="--max-old-space-size=4096" npx vite build`
4. Copy `web/dist` → `src/kimi_cli/web/static`
5. Commit both source and built static files.

## Deployment constraints

- **Target domain**: `crys.tt2.li` → `45.154.13.123`
- **Web server port**: default `5494` (configurable via `--port`)
- **Allowed origins**: must explicitly include `https://crys.tt2.li` when running in public mode
- **Auth**: in public mode, the server auto-generates a bearer token. Pass it via `?token=...` query param or `Authorization: Bearer ...` header.
- **Static files**: served from `src/kimi_cli/web/static/` (mounted at `/` as fallback)

## Repo map

- `src/kimi_cli/agents/`: built-in agent YAML specs and prompts
- `src/kimi_cli/prompts/`: shared prompt templates
- `src/kimi_cli/soul/`: core runtime/loop, context, compaction, approvals
- `src/kimi_cli/tools/`: built-in tools
- `src/kimi_cli/ui/`: UI frontends (shell/print/acp/wire)
- `src/kimi_cli/web/`: Web UI backend + bundled static assets
- `src/kimi_cli/acp/`: ACP server components
- `web/`: Web UI frontend source (React + Vite)
- `packages/kosong/`, `packages/kaos/`: workspace deps
- `tests/`, `tests_ai/`: test suites

## Conventions and quality

- Python >=3.12 (ty config uses 3.14); line length 100.
- Ruff handles lint + format (rules: E, F, UP, B, SIM, I); pyright + ty for type checks.
- Tests use pytest + pytest-asyncio; files are `tests/test_*.py`.
- CLI entry points: `kimi` / `cran-code` -> `src/kimi_cli/__main__.py`.

## Git

- Remote: `https://github.com/NLPark-Cran/cran-code.git`
- Default branch: `main`
- Commit format: Conventional Commits (`feat`, `fix`, `test`, `refactor`, `chore`, `style`, `docs`, `perf`, `build`, `ci`, `revert`).
- **Versioning**: minor-bump-only (`MAJOR.MINOR.0`). Never bump patch.

## Release workflow

1. Ensure `main` is up to date.
2. Create a release branch, e.g. `bump-0.68`.
3. Update `CHANGELOG.md`: add a new `## 0.68 (YYYY-MM-DD)` section below `## Unreleased`.
4. Update `pyproject.toml` version.
5. Run `uv sync` to align `uv.lock`.
6. Commit the branch and open a PR.
7. Merge the PR, switch back to `main`, pull latest.
8. Tag and push: `git tag 0.68 && git push --tags`
9. GitHub Actions handles the release.
