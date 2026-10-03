# Two-stage build. The builder carries a compiler so wheels without prebuilt
# variants can be compiled; the runtime stage copies only the installed
# packages, so build-essential never ships to production.
FROM python:3.11-alpine AS builder
WORKDIR /app

RUN apk add --no-cache build-base postgresql-dev

COPY pyproject.toml .
# `app` must exist before `pip install .`, because setuptools needs the package
# to be present to build the wheel.
COPY app ./app
RUN pip install --no-cache-dir --prefix=/install "."

FROM python:3.11-alpine
WORKDIR /app

# libpq is the runtime half of postgresql-dev, needed by asyncpg binaries.
RUN apk upgrade --no-cache \
 && apk add --no-cache libpq

COPY --from=builder /install /usr/local

# Packaging tools are build-time dependencies only. Removing them also avoids
# shipping setuptools' vendored copies of wheel and jaraco.context.
RUN python -m pip uninstall --yes setuptools wheel \
 && rm -rf /root/.cache

COPY . .

# Run as an unprivileged user. Root inside the container is not a container
# escape by itself, but it turns any write primitive -- a path traversal in an
# upload handler, a compromised dependency -- into a rewrite of the app code
# or the installed packages. A dedicated user removes that step.
RUN adduser -D -s /sbin/nologin appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# Production default: no --reload. Local dev overrides this in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
