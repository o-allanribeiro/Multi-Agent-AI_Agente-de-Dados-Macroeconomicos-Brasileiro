# ---------------------------------------------------------------------------
# Agente Macro-BR — Dockerfile de produção
# Imagem base: python:3.11-slim (Debian Bookworm slim)
# ---------------------------------------------------------------------------

# ── Stage 1: dependências ──────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Instala apenas o necessário para compilar extensões nativas
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-aws.txt ./

# Instala em --user para copiar ao stage final
RUN pip install --upgrade pip \
    && pip install --user --no-cache-dir -r requirements.txt \
    && pip install --user --no-cache-dir -r requirements-aws.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Cria usuário não-root (boas práticas de segurança)
RUN groupadd --gid 1001 agente \
    && useradd --uid 1001 --gid agente --no-create-home agente

WORKDIR /app

# Copia pacotes instalados pelo builder
COPY --from=builder /root/.local /home/agente/.local
ENV PATH=/home/agente/.local/bin:$PATH

# Copia código-fonte
COPY src/ ./src/
COPY config/ ./config/

# Cria diretórios de runtime com permissões corretas
RUN mkdir -p output logs \
    && chown -R agente:agente /app

USER agente

# Configura Python e diretórios de cache de libs
ENV PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    MPLCONFIGDIR=/tmp/matplotlib

EXPOSE 8000

# Health check para ECS / docker-compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
