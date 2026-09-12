# Deployment

For local development, SQLite is sufficient. For production, set `DATABASE_URL` to PostgreSQL and mount persistent storage for datasets and checkpoints.

Run the backend behind a process supervisor and keep training workers isolated from the HTTP process. Store secrets in environment variables or a secret manager.

Supabase can provide managed PostgreSQL. Use a trusted server-side database connection; never expose a Supabase secret/service key in the browser. The repository migration enables RLS and revokes public Data API access because the current backend is a trusted server-side application.
