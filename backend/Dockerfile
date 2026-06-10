# ── Stage 1: build wheels ──────────────────────────────────────────────────
FROM python:3.12-alpine AS builder

# Build-time deps for cryptography, argon2-cffi, gevent (C-extensions)
RUN apk add --no-cache build-base libffi-dev openssl-dev

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/deps -r requirements.txt

# ── Stage 2: final image (api / beat) ──────────────────────────────────────
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Runtime deps only: git (GitPython), curl (healthchecks)
RUN apk add --no-cache git curl

# Copy installed packages from builder
COPY --from=builder /deps /usr/local

WORKDIR /app
COPY . .

EXPOSE 5000
