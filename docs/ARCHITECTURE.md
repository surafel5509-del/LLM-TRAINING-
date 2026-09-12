# Architecture

The system is split into a React/Vite UI, FastAPI control plane, SQL persistence, local artifact storage, and an isolated Python training process.

Training never runs in the web request thread. The API creates a `TrainingRun`, then launches a child process. The child process owns the PyTorch model and writes checkpoints/artifacts under `storage/runs/<run-id>` while persisting metrics/state through SQLAlchemy.

SQLite is the default local database. PostgreSQL is supported by setting `DATABASE_URL`. Supabase Postgres is supported as a trusted backend database, but no existing cloud project is modified automatically.

The control plane is intentionally small and explicit. Unsupported features are documented rather than simulated.
