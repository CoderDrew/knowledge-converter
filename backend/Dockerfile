# Conversion API container. Build from backend/:  docker build -t knowledge-converter-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    KC_WORK_DIR=/tmp/kc-work

RUN useradd --create-home --uid 10001 converter
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY knowledge_engine ./knowledge_engine
COPY api ./api

USER converter
EXPOSE 8000

# One worker process: the job store and rate limiter are per-process.
# Scale with KC_MAX_CONCURRENT (isolated conversion subprocesses), not uvicorn workers.
# Client IPs from a trusted proxy are read by the app itself (KC_TRUST_PROXY_HEADERS),
# so uvicorn's own forwarded-header handling stays off.
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
