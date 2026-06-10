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
- **Inventories, repositories, environments & key store** — encrypted credentials for SSH keys, username/password pairs and Ansible Vault passwords.
- **Survey variables** — interactive input prompts shown before a task runs, including support for secret fields.
- **Schedules** — cron-based recurring runs powered by Celery Beat.
- **Integrations & webhooks** — trigger templates via incoming webhooks authenticated with HMAC signatures or tokens, with flexible matchers and value extraction from the payload.
- **Notifications** — send alerts to Email, Slack, Telegram, Teams, Rocket.Chat, DingTalk or Gotify.
- **Authentication** — local login, JWT access tokens, per-user API tokens, **2FA/TOTP** with recovery codes, LDAP and OIDC.
- **Dashboard, activity log, views, backup/restore** and auto-generated OpenAPI documentation out of the box.

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

| Variable                                | Description                                              |
|-----------------------------------------|----------------------------------------------------------|
| `OACHKATZL_MONGO_URI`                   | MongoDB connection string                                |
| `OACHKATZL_REDIS_URL`                   | Redis URL (broker, backplane, pub/sub)                   |
| `OACHKATZL_JWT_SECRET`                  | Secret used to sign JWT tokens                           |
| `OACHKATZL_ENCRYPTION_KEY`             | Fernet key for encrypting secrets stored in the database |
| `OACHKATZL_ADMIN_USER/_PASSWORD/_EMAIL` | Bootstrap admin account created on first start           |
| `OACHKATZL_TOTP_ISSUER`                | Issuer name shown in 2FA authenticator apps              |
| `OACHKATZL_REQUIRE_2FA`                | Enforce 2FA for all users (`true`/`false`)               |

The full list of variables is in [`.env.example`](.env.example).
For the Docker Hub option place the file as `.env` next to `docker-compose.yml`; for the build-from-source option use `backend/.env`.

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
