<div align="center">

<img src="frontend/src/assets/logo.svg" alt="Oachkatzl" width="96" height="96" />

# Oachkatzl

**An open-source web UI and REST API for running automation** —
Ansible playbooks, shell scripts, python and more ...

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Vue](https://img.shields.io/badge/vue-3-42b883.svg)
![Docker](https://img.shields.io/badge/docker-compose-2496ED.svg)

</div>

---

## ✨ Features

- **Projects & RBAC** — everything lives inside a project, with clearly defined roles (`owner`, `manager`, `task_runner`, `guest`).
- **Task templates** — run `ansible`, `bash`, `python` or any admin-defined **custom app**; template types cover `task`, `build` and `deploy` workflows.
- **Live log streaming** — stdout and stderr delivered in real time over WebSockets, with the full output archived in MongoDB for later retrieval.
- **Inventories, repositories, environments & key store** — encrypted credentials for SSH keys (plain, with username, or with become password), username/password pairs and Ansible Vault passwords. Ansible connection variables (`ansible_user`, `ansible_password`, `ansible_become_password`) are injected automatically from the inventory key configuration.
- **Custom Credentials** — admin-defined credential types with a free-form input schema and injector rules; inject values as environment variables, Ansible extra vars, or temporary files. Multiple credentials can be attached to a single template.
- **Survey variables** — interactive input prompts shown before a task runs, supporting `string`, `int`, `enum`, `secret`, `bool` and visual separator types.
- **Task replay** — re-run any completed task with the exact same survey answers, environment settings and git revision (commit hash is pinned automatically). Sensitive field names are masked in the run-parameter display.
- **Workflows** — chain templates into a directed graph with per-edge conditions (`on success`, `on failure`, `always`); AND-join semantics, interactive drag-and-drop canvas editor, live run view with per-node status, and a single summary notification per run.
- **Approval Gates** — place a dedicated gate node anywhere in a workflow to pause execution and wait for a human decision. A modal dialog prompts the operator to *Proceed* (workflow continues) or *Cancel* (workflow stops). Title and description text are sourced from a JSON artifact uploaded by the preceding task; if no artifact is provided, a default "Proceed?" prompt is shown.
- **Remote Approval Gates** — like an Approval Gate, but the decision happens outside the UI. Configure a list of recipients; when the node is reached each person receives an email with unique approve/reject links that work without logging in. The first response wins — subsequent recipients see who already decided. The workflow continues (approve) or stops (reject) automatically. Decisions are recorded in the run log with email address and timestamp.
- **Artifact Cache** — tasks upload files and JSON to a project-scoped cache via a token-authenticated REST API (`OACHKATZL_ARTIFACT_TOKEN` / `OACHKATZL_ARTIFACT_URL` injected automatically). Workflow nodes share one token so downstream tasks can consume upstream artifacts. Browse, download and CSV-export directly from the UI. Configurable data retention.
- **Workflow action nodes** — lightweight nodes that run inside the workflow engine without spawning a full task:
  - **List Generator** — converts a JSON array artifact into a CSV or XLSX file and stores it back in the artifact cache.
  - **PDF Generator** — renders a Markdown or HTML artifact to a PDF (via WeasyPrint) and stores it in the cache; supports custom CSS and page-size settings.
  - **Send Mail** — sends an email with optional artifact attachment; subject and body can reference artifact content.
  - **Transfer File** — pushes an artifact to a remote destination via **SFTP** (password or SSH key) or **SMB** (including domain auth). Credentials come from a Custom Credential type; the remote path supports dynamic tokens (`{date}`, `{datetime}`, `{workflow_run_id}` …) and missing directories are created automatically.
- **Custom Worker Pools** — route specific templates or custom app types to dedicated worker images. Define named pools in Admin → Worker Pools; each pool corresponds to a Celery queue. A worker container joins a pool by setting `OACHKATZL_WORKER_QUEUES=<slug>`. Pool resolution follows a priority chain: template pool → custom app default pool → built-in `celery` queue.
- **pip package proxy** — optional [devpi](https://devpi.net/) caching proxy included in the Docker Compose stack. Set `OACHKATZL_PIP_INDEX_URL` on any worker and packages are fetched from PyPI once, then served locally. Remote workers in distributed setups point to the same proxy over the network; if the proxy is unavailable the worker falls back to PyPI automatically.
- **Schedules** — cron-based recurring runs powered by Celery Beat.
- **Integrations & webhooks** — trigger templates via incoming webhooks authenticated with HMAC signatures or tokens, with flexible matchers and value extraction from the payload.
- **Notifications** — send alerts to Email, Slack, Telegram, Teams, Rocket.Chat, DingTalk or Gotify; workflow runs fire a single summary notification instead of one per task.
- **Authentication** — local login, JWT access tokens, per-user API tokens, **2FA/TOTP** with recovery codes and LDAP.
- **Dashboard, activity log, views, backup/restore** and auto-generated OpenAPI documentation out of the box.

---

## 🧱 Tech Stack

| Layer            | Technology                                               |
|------------------|----------------------------------------------------------|
| Backend          | Python 3.12+, **APIFlask** (Flask + marshmallow + OpenAPI) |
| Database         | **MongoDB 7+** via **mongoengine**                       |
| Broker / Cache   | **Redis 7+** (Celery broker, result backend, SocketIO backplane) |
| Task queue       | **Celery** workers + **Celery Beat** for scheduling      |
| Realtime         | **Flask-SocketIO** (log streaming over Redis Pub/Sub)    |
| Frontend         | **Vue 3** (`<script setup>`), **Pinia**, **Vue Router**, **TailwindCSS**, **Vite** |
| Deployment       | **Docker** + **docker-compose** (multi-container)        |



## 🏗️ Architecture

```
 Browser (Vue SPA)
   │  REST (/api) + SocketIO (/socket.io)
   ▼
 API server (APIFlask + SocketIO) ──▶ MongoDB
   │  enqueue                       ▲ persistence / log archive
   ▼                                │
 Redis (broker · backplane · pub/sub)
   ▲ consume          ▲ schedules
   │                  │
 Celery worker(s)   Celery Beat
 (git clone, subprocess exec, ansible/bash/python)
```

The **API server** creates a `Task` record and enqueues it (`run_task.delay`). A
**Celery worker** picks it up, clones the repository, runs the subprocess and publishes
every output line to the Redis channel `task:<id>`. The SocketIO hub forwards those
lines to the task room in real time, while the complete log is archived in MongoDB for
future access.

## 🚀 Quickstart

All `OACHKATZL_*` variables are read exclusively from a `.env` file — there are no
hardcoded values in the compose files. Fill in at least `OACHKATZL_ENCRYPTION_KEY`
and `OACHKATZL_JWT_SECRET` before starting.

### Option A — Docker Hub (recommended)

Pull the pre-built images from [Docker Hub](https://hub.docker.com/u/lanbugsde) — no local build required.

```bash
# 1. Download the compose file and the example env file
curl -fsSL https://raw.githubusercontent.com/lanbugs/oachkatzl/main/docker-compose.hub.yml -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/lanbugs/oachkatzl/main/.env.example -o .env

# 2. Generate secrets and set them in .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → OACHKATZL_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_hex(32))"                                   # → OACHKATZL_JWT_SECRET

# 3. Start the stack
docker compose up -d
```

### Option B — Build from source

```bash
# 1. Clone the repo
git clone https://github.com/lanbugs/oachkatzl.git
cd oachkatzl

# 2. Prepare the environment file
cp backend/.env.example backend/.env

# 3. Generate secrets and set them in backend/.env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # → OACHKATZL_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_hex(32))"                                   # → OACHKATZL_JWT_SECRET

# 4. Build and start the stack
docker compose up --build
```

| Service  | URL                            |
|----------|--------------------------------|
| Web UI   | http://localhost:8888          |
| API docs | http://localhost:8888/api/docs |

**First login:** use the credentials defined in `OACHKATZL_ADMIN_USER` and `OACHKATZL_ADMIN_PASSWORD`.
If you leave `OACHKATZL_ADMIN_PASSWORD` at its default value (`changeme`), a random password is
generated on first start and printed to the container log:

```bash
docker compose logs api | grep "Admin password"
```

### ⚙️ Key Environment Variables

| Variable                                  | Description                                                                                           |
|-------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `OACHKATZL_MONGO_URI`                     | MongoDB connection string                                                                             |
| `OACHKATZL_REDIS_URL`                     | Redis URL (broker, backplane, pub/sub)                                                                |
| `OACHKATZL_JWT_SECRET`                    | Secret used to sign JWT tokens                                                                        |
| `OACHKATZL_ENCRYPTION_KEY`                | Fernet key for encrypting secrets stored in the database                                              |
| `OACHKATZL_ADMIN_USER/_PASSWORD/_EMAIL`   | Bootstrap admin account created on first start                                                        |
| `OACHKATZL_TOTP_ISSUER`                   | Issuer name shown in 2FA authenticator apps                                                           |
| `OACHKATZL_REQUIRE_2FA`                   | Enforce 2FA for all users (`true`/`false`)                                                            |
| `OACHKATZL_BASE_URL`                      | External URL of the instance (used in artifact URL injection)                                         |
| `OACHKATZL_INTERNAL_API_URL`              | Internal Docker URL of the API container (default: `http://api:5000`)                                 |
| `OACHKATZL_PIP_INDEX_URL`                 | pip `--index-url` for Python tasks — point to devpi or any PEP 503 proxy; leave empty for direct PyPI |
| `OACHKATZL_WORKER_QUEUES`                 | Celery queue(s) a worker container consumes. Default: `celery`. Set to a Worker Pool slug (e.g. `gpu`) to create a dedicated worker for that pool. Comma-separate multiple queues. |

The full list of variables is in [`.env.example`](.env.example).
For the Docker Hub option place the file as `.env` next to `docker-compose.yml`; for the build-from-source option use `backend/.env`.

---

## 🛠️ Local Development

Start Mongo and Redis first: `docker compose up mongo redis`.

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

flask --app wsgi run --debug                  # API server
celery -A app.celery_app worker -l info       # task worker
celery -A app.celery_app beat -l info         # scheduler

pytest                                        # tests
ruff check . && ruff format .                 # lint + format
```

**Frontend**

```bash
cd frontend
npm install
npm run dev        # Vite dev server
npm run build      # production build
npm run lint
```

## 🖥️ Custom Worker Pools

By default every task runs on the built-in `celery` queue. **Worker Pools** let you route specific templates or app types to dedicated worker containers — useful when some tasks need GPU drivers, extra binaries (Terraform, kubectl …), isolated network access, or a different Python environment.

### How it works

```
Template A  ──→  pool "gpu"        ──→  worker-gpu container
Template B  ──→  pool "terraform"  ──→  worker-terraform container
Template C  ──→  (default)         ──→  standard worker container
```

### Quick setup

1. **Define a pool** — open **Settings → Worker Pools** in the sidebar and click *New pool*. Set a slug (e.g. `gpu`).
2. **Build a custom worker image** — use the official worker image as a base and add your tools:
   ```dockerfile
   FROM lanbugsde/oachkatzl-worker:latest
   RUN apt-get update && apt-get install -y terraform && rm -rf /var/lib/apt/lists/*
   ```
3. **Add a worker service** in `docker-compose.yml`:
   ```yaml
   worker-terraform:
     image: my-terraform-worker:latest
     command: >-
       sh -c "celery -A worker.celery worker -l info -c 2 -Q $$OACHKATZL_WORKER_QUEUES"
     env_file: .env
     environment:
       OACHKATZL_WORKER_QUEUES: "terraform"
     depends_on:
       mongo: { condition: service_healthy }
       redis: { condition: service_healthy }
     volumes:
       - /tmp/oachkatzl:/tmp/oachkatzl
   ```
4. **Assign the pool** on a template (dropdown in the template editor) or as the default on a Custom App (Settings → Custom Apps).

### Pool resolution order

| Priority | Source | Wins when |
|----------|--------|-----------|
| 1 (highest) | Template's worker pool field | Pool is set directly on the template |
| 2 | Custom App's default pool | Template uses a custom app type that has a pool |
| 3 (default) | Built-in `celery` queue | No pool set anywhere |

> **Note:** if a pool has no running worker, tasks remain in `waiting` status indefinitely. Always ensure at least one worker container is started for every active pool.

---

## 📦 Project Structure

```
backend/                APIFlask app, mongoengine models, Celery tasks, services
frontend/               Vue 3 + Tailwind SPA (Vite)
nginx/                  reverse proxy configuration
docker-compose.yml      build-from-source compose file
docker-compose.hub.yml  Docker Hub compose file (pre-built images)
```

## 🤝 Contributing

Pull requests are welcome. Please follow the existing style: Python code according to PEP 8
(enforced by `ruff`), business logic in `services/`, thin blueprints, RBAC always enforced
server-side — and absolutely **no CDN**. Include tests for auth flows, task startup, RBAC
checks and webhook matchers.

## 📄 License

[MIT](LICENSE)

---

## 🐿️ The Story Behind the Name "Oachkatzl"

*Oachkatzl* is the Bavarian and Austrian dialect word for **squirrel** (*Eichhörnchen* in standard German) —
best known as the first half of the nearly impossible tongue-twister *"Oachkatzlschwoaf"* (squirrel's tail).

As it turns out, a squirrel makes a surprisingly fitting mascot for an automation orchestrator:

- 🌰 **It diligently collects nuts** — your playbooks and inventories — and **stashes them away** for exactly the right moment.
- 🌳 **It leaps from branch to branch** — your server nodes — with speed and precision, never missing a step.
- 🔭 **From the top of the tree it keeps a perfect overview of its territory** — your dashboard.

Fast, organized, always watching over its domain. That's Oachkatzl. 🐿️
