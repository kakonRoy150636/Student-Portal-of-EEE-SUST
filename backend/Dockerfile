FROM python:3.11-slim

# Runtime deps only: build-essential/libpq-dev were pulled in to compile
# wheels that all ship prebuilt, leaving a full toolchain in the runtime
# image. libpq5/curl are the real runtime needs (asyncpg links nothing, but
# the healthcheck below uses curl).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, from the pins, so editing application code does not
# invalidate the layer. requirements-dev.txt includes the test extras, which
# is deliberate: `docker compose exec backend pytest` is the documented way to
# run the suite.
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Run as a non-root user. The container previously ran as root, so anything
# that compromised the process had root inside the image.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# Production default: no --reload. Local dev overrides this in compose.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
