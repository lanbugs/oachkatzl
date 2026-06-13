# Contributing to oachkatzl

Thank you for taking the time to contribute! Every bug report, feature idea, documentation fix, and pull request makes oachkatzl better for everyone.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Guidelines](#coding-guidelines)
- [Running Tests](#running-tests)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)

---

## Code of Conduct

Be respectful and constructive. We welcome contributors of all experience levels.

---

## Ways to Contribute

- **Bug reports** — open a [GitHub issue](https://github.com/lanbugs/oachkatzl/issues)
- **Feature requests** — open a [GitHub issue](https://github.com/lanbugs/oachkatzl/issues) with the `enhancement` label
- **Pull requests** — bug fixes, new features, documentation improvements
- **Spreading the word** — star the repo, write a blog post, tell your team

---

## Development Setup

### Prerequisites

| Tool | Minimum version |
|------|----------------|
| Docker + Docker Compose | 24+ |
| Python | 3.12+ |
| Node.js | 20+ |
| Git | any recent |

### 1. Clone the repository

```bash
git clone https://github.com/lanbugs/oachkatzl.git
cd oachkatzl
```

### 2. Start infrastructure services

```bash
docker compose up mongo redis -d
```

### 3. Backend

```bash
cd backend
cp .env.example .env
# Edit .env — set OACHKATZL_ENCRYPTION_KEY, OACHKATZL_JWT_SECRET, admin credentials

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# API server
flask --app wsgi run --debug

# In separate terminals:
celery -A app.celery_app worker -l info
celery -A app.celery_app beat   -l info
```

API docs are available at `http://localhost:5000/api/docs`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vue dev server proxies API and WebSocket requests to the Flask backend.  
Open `http://localhost:5173` in your browser.

### 5. Full stack via Docker (alternative)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env
docker compose up --build
```

Web UI → `http://localhost:8888` · API docs → `http://localhost:8888/api/docs`

---

## Project Structure

```
backend/
  app/
    blueprints/       Thin route handlers (one per resource)
    services/         Business logic — keep it here, not in blueprints
    models/           MongoEngine document definitions
    tasks/            Celery task definitions
    schemas/          Marshmallow/APIFlask schemas
  wsgi.py
  requirements.txt

frontend/
  src/
    views/            Page-level Vue components
    components/       Reusable UI components
    stores/           Pinia stores
    router/           Vue Router configuration

nginx/                Reverse proxy config
docker-compose.yml    Build-from-source
docker-compose.hub.yml Pre-built images from Docker Hub
```

---

## Coding Guidelines

### General

- **No CDN dependencies** — all assets must be self-hosted or bundled.
- **RBAC is always enforced server-side** — never rely solely on frontend guards.
- Business logic belongs in `services/`, not in blueprints or Celery tasks.

### Python (backend)

- Follow **PEP 8**; enforced via [`ruff`](https://github.com/astral-sh/ruff).
- Run before committing:
  ```bash
  ruff check .
  ruff format .
  ```
- Keep blueprints thin — route handlers should call a service function and return a schema-serialized response.
- Encrypt all secrets at rest using Fernet (`OACHKATZL_ENCRYPTION_KEY`).

### Vue / JavaScript (frontend)

- Use the **Composition API** with `<script setup>`.
- State management via **Pinia** stores — no global event buses.
- Styling via **TailwindCSS** utility classes.
- Run before committing:
  ```bash
  npm run lint
  ```

---

## Running Tests

### Backend

```bash
cd backend
pytest
```

Make sure your `.env` points to a running MongoDB and Redis instance (the Docker services from step 2 above work fine).

Tests should cover:
- Authentication flows (login, JWT refresh, TOTP, LDAP)
- Task startup and Celery dispatch
- RBAC permission checks for all relevant roles
- Webhook signature validation

### Frontend

```bash
cd frontend
npm run lint   # ESLint
```

---

## Submitting a Pull Request

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Write your code** following the guidelines above.

3. **Add or update tests** for any changed behaviour.

4. **Run linters and tests** locally and make sure everything passes.

5. **Commit** with a clear, imperative message:
   ```
   feat: add GPU worker pool routing
   fix: correct LDAP group sync on re-login
   docs: document artifact retention policy
   ```

6. **Open a pull request** against `main`. In the PR description, explain:
   - *What* changed and *why*
   - How you tested it
   - Any follow-up work or known limitations

7. A maintainer will review your PR. Please respond to review comments promptly — stale PRs may be closed after 30 days of inactivity.

---

## Reporting Bugs

Open an issue and include:

- **oachkatzl version** (Docker image tag or git commit)
- **Steps to reproduce** — the more specific, the better
- **Expected behaviour** vs **actual behaviour**
- Relevant log output (redact any secrets)
- Environment details (OS, Docker version, browser if UI-related)

---

## Requesting Features

Open an issue with the `enhancement` label and describe:

- The **use case** you're trying to solve
- Your **proposed solution** (optional but helpful)
- Any alternatives you have considered

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
