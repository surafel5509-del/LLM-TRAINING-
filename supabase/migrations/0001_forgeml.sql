create table if not exists projects(id uuid primary key default gen_random_uuid(),name text not null,created_at timestamptz not null default now());
create table if not exists datasets(id uuid primary key default gen_random_uuid(),project_id uuid not null references projects(id),name text not null,path text not null,format text not null,rows integer,columns integer,created_at timestamptz not null default now());
create table if not exists models(id uuid primary key default gen_random_uuid(),project_id uuid not null references projects(id),name text not null,task text not null,architecture jsonb not null,created_at timestamptz not null default now());
create table if not exists training_runs(id uuid primary key default gen_random_uuid(),project_id uuid not null references projects(id),dataset_id uuid not null references datasets(id),model_id uuid not null references models(id),status text not null,config jsonb not null,error text,started_at timestamptz,finished_at timestamptz);
create table if not exists metrics(id uuid primary key default gen_random_uuid(),run_id uuid not null references training_runs(id),epoch integer not null,split text not null,loss double precision not null,metric double precision,learning_rate double precision,samples_per_sec double precision);
create table if not exists checkpoints(id uuid primary key default gen_random_uuid(),run_id uuid not null references training_runs(id),epoch integer not null,path text not null,is_best boolean not null default false,created_at timestamptz not null default now());
create table if not exists model_versions(id uuid primary key default gen_random_uuid(),model_id uuid not null references models(id),run_id uuid not null references training_runs(id),version integer not null,checkpoint_path text not null,metrics jsonb not null,created_at timestamptz not null default now(),unique(model_id,version));
create table if not exists evaluations(id uuid primary key default gen_random_uuid(),run_id uuid not null references training_runs(id),metrics jsonb not null,created_at timestamptz not null default now());

alter table projects enable row level security;
alter table datasets enable row level security;
alter table models enable row level security;
alter table training_runs enable row level security;
alter table metrics enable row level security;
alter table checkpoints enable row level security;
alter table model_versions enable row level security;
alter table evaluations enable row level security;

-- Internal backend tables: access is intentionally denied through the public Data API.
-- The FastAPI service should use a trusted server-side Postgres connection.
revoke all on projects,datasets,models,training_runs,metrics,checkpoints,model_versions,evaluations from anon,authenticated;
