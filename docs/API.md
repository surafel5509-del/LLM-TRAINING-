# API Contract

ForgeML exposes a FastAPI backend under `/api`.

## Health

- `GET /api/health` — liveness and CPU/PyTorch information.
- `GET /api/system/resources` — CPU, RAM, disk and core counts.

## Projects and datasets

- `POST /api/projects` — create a project.
- `GET /api/projects` — list projects.
- `POST /api/datasets` — upload CSV, JSON or JSONL.
- `GET /api/datasets?project_id=<id>` — list datasets.
- `POST /api/datasets/<id>/validate?target=<column>` — validate a target and report dataset diagnostics.

## Models

- `POST /api/models` — create a classification/regression MLP configuration.
- `GET /api/models?project_id=<id>` — list models.
- `GET /api/models/<id>/versions` — list completed model versions.

## Training lifecycle

- `POST /api/training/runs` — create a queued run.
- `GET /api/training/runs` — list runs.
- `POST /api/training/runs/<id>/start` — start a real CPU worker process.
- `POST /api/training/runs/<id>/pause` — request pause at an epoch boundary.
- `POST /api/training/runs/<id>/resume` — resume a paused worker.
- `POST /api/training/runs/<id>/cancel` — cancel at an epoch boundary.
- `GET /api/training/runs/<id>/metrics` — retrieve persisted train/validation metrics.
- `GET /api/training/runs/<id>/checkpoints` — retrieve persisted checkpoints.
- `GET /api/training/runs/<id>/test-metrics` — retrieve final test metrics.

## Inference

- `POST /api/models/<id>/infer` — run inference against the latest completed model version.
- `GET /api/checkpoints/<id>/download` — download a persisted checkpoint.

## Production boundary

The Vercel deployment is the React/Vite frontend. The training backend is **not** deployed as a Vercel Function because it owns long-running PyTorch processes, local checkpoint storage and database sessions. Run the backend as a persistent container/service (for example on a container host or VM) and set `VITE_API_URL` in Vercel to the public API origin.

The backend should use PostgreSQL and durable object/file storage in production. The included local filesystem + SQLite defaults are for development and deterministic local testing only.

Authentication, tenant isolation, rate limiting, distributed workers, object-storage uploads and background job queues remain explicit next-phase production requirements; they must not be represented as implemented by this API.
