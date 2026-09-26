FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Roda como usuário sem privilégios (exigência básica da maioria dos PaaS).
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# As migrações são idempotentes (conferem antes de alterar). Rodar a cada
# deploy garante que o banco tenha as colunas que o código novo usa; se
# falharem, o erro fica no log e a API sobe mesmo assim.
CMD ["sh", "-c", "python -m app.db.migrations.run_migrations || echo 'ATENCAO: migracoes falharam'; exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
