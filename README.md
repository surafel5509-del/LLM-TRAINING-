# ForgeML — Real CPU AI/ML Training Platform

ForgeML is a local-first web platform for **real** machine-learning training. The current vertical slice uses FastAPI + PyTorch + Pandas/scikit-learn + React/Vite and executes training in a separate process on CPU.

## What is real
- Actual PyTorch forward pass, loss, `backward()`, optimizer step and weight updates.
- Real train/validation/test split with a reproducible seed.
- Real checkpoints containing model and optimizer state.
- Real test metrics from held-out test data.
- Real model versions and CPU/RAM measurements.
- Real inference from a saved model version.
- Pause/resume/cancel controls implemented with process-safe control files.

## Current support
Implemented: tabular CSV/JSON/JSONL, MLP classification and regression, Adam/SGD, ReLU/Tanh/GELU, dropout, CPU workers, CPU threads, checkpoints, evaluation, model versions, inference, responsive dashboard.

Explicitly not implemented yet: image/CNN datasets, sequence models, ONNX/TorchScript export, authentication/authorization, multi-user tenancy, distributed training, hyperparameter sweeps, and production object storage. The UI/API must not claim those features are available.

## Local run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

In another shell:
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker
```bash
docker compose up --build
```

## Test
```bash
pytest -q backend/tests
```

The core ML test verifies that actual optimizer execution changes model weights; it does not accept a progress bar or hard-coded metrics as proof of training.

## Supabase
A safe SQL schema is provided under `supabase/migrations/`. It is deliberately not applied to the existing Supabase project automatically because changing an unrelated existing project would be unsafe. Set `DATABASE_URL` to a trusted Supabase Postgres connection only when you intentionally choose a project.

## API
FastAPI exposes OpenAPI at `/docs` and `/openapi.json`.

See `docs/ARCHITECTURE.md`, `docs/TRAINING.md`, `docs/DATASETS.md`, `docs/MODELS.md`, `docs/TESTING.md`, and `docs/DEPLOYMENT.md` for the engineering contract and extension plan.
