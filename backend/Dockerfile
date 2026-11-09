FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
# Instal dependency lebih dulu, lalu baru source di bawah: perubahan pada app/
# tidak memaksa ulang instalasi seluruh dependency di layer cache Docker.
RUN pip install --no-cache-dir .

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Migrasi dijalankan saat start, bukan saat build, supaya image tidak butuh database.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
