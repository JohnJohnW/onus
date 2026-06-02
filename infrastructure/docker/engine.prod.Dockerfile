# Production image for the Onus engine (FastAPI).
# Unlike the dev image, the source is baked in (not bind-mounted) and there is no
# --reload. Build context is ./engine (see docker-compose.prod.yml).
FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary, bcrypt and cryptography ship manylinux wheels, so no system
# build toolchain is required.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply migrations as the owner (ALEMBIC_DATABASE_URL), then serve as onus_app.
# A single worker keeps the in-memory per-account login throttle coherent; if you
# scale to multiple workers/instances, front the API with a shared edge rate limiter
# (see docs/deployment/README.md).
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]
