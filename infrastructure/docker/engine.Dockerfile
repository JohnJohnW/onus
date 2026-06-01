# Development image for the Onus engine (FastAPI).
# Pinned to the CI Python version (3.11). The source tree is bind-mounted at
# runtime (see docker-compose.yml) so uvicorn --reload picks up changes.
FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary, bcrypt and cryptography ship manylinux wheels, so no system
# build toolchain is required here.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
