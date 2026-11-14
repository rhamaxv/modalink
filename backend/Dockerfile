FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# app/ harus sudah ada sebelum pip install, dan urutannya tidak bisa dibalik:
# pyproject.toml menyebut `packages = ["app"]`, dan setuptools memeriksa
# direktori itu sungguhan ada saat menyusun metadata, jauh sebelum ia menyalin
# apa pun. Versi sebelumnya menyalin pyproject.toml sendirian demi cache layer
# dependency, dan build-nya selalu mati di "error: package directory 'app' does
# not exist" — tidak pernah ketahuan karena image prod memang belum pernah
# di-build sampai selesai sebelum deploy pertama.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

COPY alembic ./alembic
COPY alembic.ini ./

# Migrasi dijalankan saat start, bukan saat build, supaya image tidak butuh database.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
