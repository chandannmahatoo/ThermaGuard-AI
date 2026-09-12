# ThermaGuard AI — run doc

This workspace is the main checkout, so its uncommitted artifacts already exist here.
The steps below reproduce them in a **fresh checkout** of the same repo.

## 1. Reproduce the uncommitted artifacts

Backend (Python 3.14):

1. Create the virtualenv: `python3 -m venv .venv` then `./.venv/bin/pip install -r backend/requirements.txt`.
2. Create `backend/.env` from `backend/.env.example` and fill real credentials manually
   (JWT_SECRET, FIRMS_MAP_KEY, COPERNICUS_*, GEMINI_*, SMTP_*).
   **Never copy secret values into this doc or any tracked file.** The file is git-ignored.
3. Run the server from the **repo root** (the SQLite path `sqlite:///./thermaguard.db`
   is CWD-relative; the real events DB lives at the root): `PYTHONPATH=backend`.

Frontend (Node 22):

1. `npm --prefix frontend ci` (lockfile-driven).
2. Copy `frontend/.env.local` from the main checkout (git-ignored). It contains only
   public base URLs:
   - `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1`
   - `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`
   These are build-time variables — set them **before** `npm --prefix frontend run build`.
3. `npm --prefix frontend run build` (also run `typecheck` first if validating).

## 2. Run the server

Defaults: backend `:8000`, frontend `:3000`. If a port is taken, pick a free one and
pass `--port` to uvicorn / `next start` (and adapt the frontend env URLs + rebuild).

Current detached instances run under launchd (they outlive the conversation):

```sh
# Backend
launchctl submit -l thermaguard-backend -o /tmp/thermaguard-backend.log -e /tmp/thermaguard-backend.err -- \
  /bin/sh -c "cd <repo-root> && PYTHONPATH=backend exec ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000"

# Frontend (npx needs node on PATH; launchd's PATH is minimal)
launchctl submit -l thermaguard-fe -o /tmp/thermaguard-fe.log -e /tmp/thermaguard-fe.err -- \
  /bin/sh -c "cd <repo-root>/frontend && PATH=/opt/homebrew/opt/node@22/bin:\$PATH exec npx next start --hostname 127.0.0.1 --port 3000"
```

Stop with `launchctl remove thermaguard-backend` / `launchctl remove thermaguard-fe`.
Foreground alternative: `PYTHONPATH=backend ./.venv/bin/uvicorn app.main:app --port 8000`
and `npm --prefix frontend start`.

Health checks: `GET http://127.0.0.1:8000/health` → `{"status":"ok",...}`;
`GET http://127.0.0.1:3000/` → 200 (login screen on first visit).
