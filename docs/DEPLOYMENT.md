# Deployment

## Production architecture

ForgeML is intentionally deployed as two services:

1. **Frontend — Vercel**: React + Vite static application.
2. **Backend — persistent container/service**: FastAPI + PyTorch training workers + PostgreSQL + durable storage.

Do not move the training worker into a Vercel Function. Training can run for many minutes, requires CPU resources, persists checkpoints, and uses a separate worker process. A serverless request runtime is the wrong execution boundary for that workload.

## Vercel

The repository root contains `vercel.json` and is configured to build the frontend with:

```text
npm --prefix frontend install
npm --prefix frontend run build
```

The output is `frontend/dist`.

Create a Vercel project connected to this repository and configure:

```text
VITE_API_URL=https://api.example.com/api
```

Use separate values for Preview and Production environments. Never put database credentials, service keys, signing secrets or other private credentials in `VITE_*` variables because Vite embeds them into browser assets.

## Backend

For production:

- Set `DATABASE_URL` to PostgreSQL.
- Set `STORAGE_ROOT` to a persistent volume or replace filesystem persistence with object storage.
- Set `CORS_ORIGINS` to the exact Vercel deployment origins that are allowed to call the API.
- Run Alembic migrations before starting the API.
- Run the API behind HTTPS and a process supervisor/container orchestrator.
- Keep training workers isolated from the HTTP process.
- Persist checkpoints and dataset artifacts independently of container lifecycle.
- Add authentication/authorization and tenant isolation before exposing the service publicly.

## Container

The existing Docker Compose stack is suitable for development and integration testing. For production, use a managed PostgreSQL service and durable artifact storage rather than relying on the container filesystem.

## Supabase option

Supabase can provide managed PostgreSQL. Use a trusted server-side database connection; never expose a Supabase secret/service key in the browser. The repository migration enables RLS and revokes public Data API access because the current backend is a trusted server-side application.

If Supabase is selected for production, apply the migration only to the intended ForgeML project. Do not apply it to unrelated existing projects.

## Deployment readiness status

### Ready

- Vercel build configuration.
- Frontend environment template.
- SPA fallback and baseline security headers.
- Backend API contract documentation.
- Docker-based backend deployment path.
- Database migration path.
- CI build/test path.

### Still required before public production launch

- Authentication and authorization.
- Per-user/per-tenant data isolation.
- Durable object storage for datasets/checkpoints.
- Queue-based training workers with retry/recovery semantics.
- Rate limiting and abuse protection.
- Centralized structured logs and audit events.
- Production monitoring/alerts.
- Full integration/E2E acceptance suite.
- Backup/restore drill.
