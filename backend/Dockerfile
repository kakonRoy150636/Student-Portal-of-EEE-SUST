FROM python:3.11-slim
WORKDIR /app

# build-essential is only needed to compile wheels that have no prebuilt
# variant; drop both it and libpq-dev's headers once pip is done so the
# runtime image does not carry a compiler for an attacker to use.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir ".[dev]"

COPY . .

# Run as an unprivileged user. Root inside the container is not a container
# escape by itself, but it turns any write primitive -- a path traversal in an
# upload handler, a compromised dependency -- into a rewrite of the app code
# or the installed packages. A dedicated user removes that step.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# Production default: no --reload. Local dev overrides this in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
