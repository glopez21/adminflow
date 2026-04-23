FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY .venv .venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s -- retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

USER 1000:1000

CMD ["python", "-m", "src.api.main"]