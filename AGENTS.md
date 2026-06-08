# Cran Code

> Forked from [MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli). Maintained independently by the NLPark-Cran team for the crys.tt2.li collaborative coding platform.

---

## CRITICAL: What must NEVER change (compact-proof constraints)

### 1. Branding rules
- **Frontend (user-visible)**: ALL Kimi/Kimi Code branding → `Cran` / `Cran Code`.
  - HTML titles, logo alt text, brand component names, banner ASCII art, CLI help text, API docstrings.
  - localStorage/sessionStorage keys: `cran_` prefix (e.g. `cran_auth_token`, `cran-theme`).
  - Custom event names: `cran:` prefix (e.g. `cran:config-update`).
- **Backend API requests**: `USER_AGENT` in `src/cran_code/constant.py` MUST stay as `KimiCLI/{version}`.
  - `get_user_agent()` must NOT be renamed or changed.
  - This is required for Kimi Token Plan backend compatibility.
- **LLM ProviderType enum**: value `kimi` is a provider key, NOT branding. Do NOT change.

### 2. Package / command identity (MIGRATED — do not revert)
- Package name: `cran-code` (was `kimi-cli`).
- CLI commands: `cran` / `cran-code` (was `kimi` / `kimi-cli`).
- Python module: `cran_code` (was `kimi_cli`). Directory: `src/cran_code/`.
- Config directory: `~/.cran/` (was `~/.kimi/`).
- Environment variables: `CRAN_*` prefix (was `KIMI_*`).
  - Exception: Kimi-platform OAuth vars (`KIMI_CODE_*`, `KIMI_CODE_CLIENT_ID`, etc.) are kept as-is because they refer to Kimi's official OAuth service.

### 3. Database
- Path: `~/.cran/cran.db` (SQLite, via SQLAlchemy 2.0 async + aiosqlite).
- Tables: `users`, `teams`, `team_members`, `projects`, `project_members`, `activities`.
- Auto-created on first startup via `init_db()` in FastAPI lifespan.

### 4. Kimi API configuration (local deployment only)
- **Model**: `kimi-for-coding` (Kimi Code subscription plan API).
- **Endpoint**: `https://api.kimi.com/coding/v1`.
- **API key**: Pre-filled in `~/.cran/config.toml` on the deployment server ONLY.
- **RED LINE**: API key MUST NOT be committed to the Git repo.
  - `~/.cran/` is already `.gitignore`d, but NEVER add config templates or scripts that embed the key.
  - If building a setup script, it must prompt the user for their own key or leave the field empty.
- **Why `kimi-for-coding`**: This is the Kimi subscription plan model identifier, different from the regular `kimi` model.

---

## Completed work (as of main branch)

### Phase 0: Backend infrastructure
- [x] SQLAlchemy 2.0 async ORM with aiosqlite
- [x] Models: `User`, `Team`, `TeamMember`, `Project`, `ProjectMember`, `Activity`
- [x] JWT auth: `python-jose` + `passlib[bcrypt]`
- [x] v2 API routes registered in FastAPI app:
  - `POST /api/v2/auth/register`
  - `POST /api/v2/auth/login`
  - `GET /api/v2/users/me`
  - `GET/POST /api/v2/teams`
  - `GET/POST /api/v2/projects`

### Phase 1a: Frontend auth + v1/v2 bridging
- [x] react-router-dom installed
- [x] `RootApp.tsx` with `BrowserRouter` + auth-gated routes
- [x] `LoginPage.tsx` with login/register toggle
- [x] `useAuthStore` (Zustand + localStorage persistence)
- [x] `v2Api` hand-written client in `web/src/lib/api/v2.ts`
- [x] `lib/auth.ts` bridges v2 JWT into v1 API calls (`getAuthToken()` prefers JWT-format tokens)
- [x] v1 `AuthMiddleware` skips `/api/v2/` and falls back to v2 JWT decode
- [x] v1 WebSocket `session_stream` accepts v2 JWT in `?token=` query param

### Package migration
- [x] Renamed `src/kimi_cli/` → `src/cran_code/`
- [x] Updated `pyproject.toml`: name, scripts, module-name, workspace sources
- [x] Batch-replaced all Python imports `kimi_cli` → `cran_code`
- [x] Batch-replaced env vars `KIMI_*` → `CRAN_*` (except OAuth)
- [x] Batch-replaced config dir `~/.kimi/` → `~/.cran/`
- [x] Updated Makefile, AGENTS.md
- [x] Rebuilt frontend static assets

---

## Roadmap (remaining)

### Phase 1b: Team/Project UI
- [x] `TeamPage.tsx` — team list, create team, team detail
- [x] `ProjectPage.tsx` — project list, create project, project detail
- [ ] Team selector in top navigation
- [ ] Member management panel (add/remove members, role assignment)
- [ ] Activity stream sidebar

### Phase 2: IDE core (Cursor parity)
- [ ] Monaco Editor integration
- [ ] File tree component (recursive directory tree)
- [ ] Multi-tab interface
- [ ] Inline diff (Accept/Reject AI changes)
- [ ] @-mentions / file reference in prompt composer

### Phase 3: Real-time collaboration
- [ ] Yjs + WebSocket integration
- [ ] Multi-user cursor sync in editor
- [ ] Comment system on code lines
- [ ] Activity feed (human + AI actions)

### Phase 4: Professional extensions
- [ ] xterm.js integrated terminal
- [ ] Git UI (branch, commit, diff, staging)
- [ ] LSP client integration
- [ ] Settings/keybindings panel

### Phase 5: Performance
- [ ] Upgrade Vite 7 → 8
- [ ] Route-level code splitting
- [ ] React Compiler (React 19 built-in)

---

## Quick commands

### Development
```bash
make prepare      # sync deps + install git hooks
make format       # ruff format all
make check        # ruff + pyright + ty
make test         # pytest
make build        # uv build
make build-bin    # PyInstaller
```
Direct execution: `uv run ...`

### Install / Update
```bash
uv tool install .            # from source
uv tool upgrade cran-code --no-cache
```

### Start Web UI
```bash
# Local dev
cran web --no-open --public

# Production (crys.tt2.li) — cran-code runs on port 5496
# (kimi-cli original preserved on 5494, do not kill)
cran web --host 0.0.0.0 --port 5496 --public --no-open \
  --allowed-origins "https://crys.tt2.li"
```

### Frontend build
```bash
cd web
npx tsc -b --noEmit                                      # type check
NODE_OPTIONS="--max-old-space-size=1536" npx vite build  # build (2GB RAM limit)
cp -r dist ../src/cran_code/web/static                   # bundle
# Note: static assets are gitignored; use `git add -f` when committing rebuilds
```

---

## Tech stack

### Backend
- Python 3.12+ (tooling targets 3.14)
- CLI: Typer
- Async: asyncio
- LLM: kosong (workspace package)
- OS abstraction: pykaos (workspace package)
- MCP: fastmcp
- Logging: loguru
- Package: uv + uv_build; PyInstaller for binaries
- Tests: pytest + pytest-asyncio
- Lint/format: ruff; types: pyright + ty
- Web: FastAPI + uvicorn
- DB: SQLAlchemy 2.0 (async) + aiosqlite + alembic
- Auth: passlib[bcrypt] + python-jose[cryptography]

### Frontend
- React 19 + TypeScript 5.9
- Vite 7 (target: Vite 8)
- Tailwind CSS v4
- shadcn/ui + Radix UI primitives
- AI SDK v5 (`@ai-elements`)
- Routing: react-router-dom v7
- State: Zustand, SWR
- Highlighting: Shiki, CodeMirror
- Diagrams: Mermaid, XYFlow

### Collaboration (planned)
- CRDT: Yjs
- Editor binding: y-monaco
- Transport: native WebSocket or Hocuspocus

---

## Architecture

### Backend structure
```
src/cran_code/
  cli/           # Typer CLI entrypoints
  soul/          # Core agent loop (KimiSoul, context, compaction, approvals)
  tools/         # Built-in tools (shell, file, web, agent, todo, plan, etc.)
  ui/            # Shell UI, print UI, ACP wire
  web/           # FastAPI web UI backend
    api/         # v1 API (config, sessions, work-dirs, open-in)
    api_v2/      # v2 API (auth, users, teams, projects)
    auth_v2/     # JWT + password hashing
    db/          # SQLAlchemy models + connection
    static/      # Bundled frontend build output
  wire/          # Wire protocol between soul and UI
  acp/           # ACP server for IDE integrations
  agents/        # YAML agent specs + system prompts
  config.py      # TOML config loader
  llm.py         # Model/provider selection
  app.py         # KimiCLI app factory
  constant.py    # VERSION, USER_AGENT (keep KimiCLI), NAME
```

### Frontend structure
```
web/src/
  App.tsx                    # Main chat UI (sessions sidebar + workspace)
  RootApp.tsx                # Router entry (BrowserRouter, auth gate)
  bootstrap.tsx              # React root render
  pages/LoginPage.tsx        # Auth page
  stores/auth.ts             # Zustand auth store
  lib/api/v2.ts              # Hand-written v2 API client
  lib/api/                   # OpenAPI-generated v1 API client
  features/
    sessions/                # Session list sidebar
    chat/                    # Chat workspace, composer, message list
  components/
    cran-cli-brand.tsx       # Brand component (was kimi-cli-brand)
    ui/                      # shadcn/ui components
  hooks/
    useSessionStream.ts      # WebSocket + message state reducer
    useGlobalConfig.ts       # Config polling
```

### Database schema (simplified)
```
users
  id (PK), email (unique), username (unique), password_hash,
  display_name, avatar_url, role (user|admin), is_active,
  created_at, updated_at

teams
  id (PK), name, slug (unique), description, owner_id (FK users),
  created_at, updated_at

team_members
  id (PK), team_id (FK), user_id (FK), role (owner|admin|member),
  joined_at

projects
  id (PK), team_id (FK), name, slug, description,
  work_dir, git_repo_url, default_model, created_by (FK users),
  created_at, updated_at

project_members
  id (PK), project_id (FK), user_id (FK), role (owner|admin|member),
  joined_at

activities
  id (PK), project_id (FK), user_id (FK, nullable),
  type (enum), payload (JSON text), created_at
```

---

## Deployment

- **Domain**: `crys.tt2.li` → `45.154.13.123`
- **Ports**: `5494` (kimi-cli original, preserved) / `5496` (cran-code)
- **Reverse proxy**: Nginx (configured) → `127.0.0.1:5496`
- **Nginx** (simplified):
  ```nginx
  server {
      listen 443 ssl;
      server_name crys.tt2.li;
      location / {
          proxy_pass http://127.0.0.1:5496;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
      }
  }
  ```
- **Static files**: `src/cran_code/web/static/` served by FastAPI `StaticFiles(html=True)`
- **Allowed origins**: MUST explicitly set `--allowed-origins "https://crys.tt2.li"` in public mode
- **Auth**: v2 uses JWT (localStorage `cran_v2_auth_token`). v1 legacy token still active for sessions API.
- **Auth bridging**: v1 `AuthMiddleware` and WebSocket `session_stream` accept v2 JWT tokens so v2-authed users can use v1 chat features without a separate v1 session.
- **Python 3.14 compat**: `passlib` bcrypt backend detection crashes on Python 3.14. `src/cran_code/web/auth_v2/password.py` uses `bcrypt` directly instead of `passlib`.

---

## Conventions

- Python >=3.12; line length 100.
- Ruff rules: E, F, UP, B, SIM, I.
- Tests: `tests/test_*.py` with pytest + pytest-asyncio.
- **Versioning**: minor-bump-only (`MAJOR.MINOR.0`). Never bump patch.
- Commits: Conventional Commits (`feat`, `fix`, `test`, `refactor`, `chore`, `style`, `docs`, `perf`, `build`, `ci`, `revert`).

## Git
- Remote: `https://github.com/NLPark-Cran/cran-code.git`
- Branch: `main`
- Token-based HTTPS push configured ( PAT in git remote URL).

## Release
1. Pull latest `main`.
2. Branch `bump-X.Y`.
3. Update `CHANGELOG.md` (add `## X.Y (YYYY-MM-DD)` below `## Unreleased`).
4. Update `pyproject.toml` version.
5. `uv sync` to align `uv.lock`.
6. Commit, open PR, merge.
7. `git tag X.Y && git push --tags`
8. GitHub Actions releases automatically.
