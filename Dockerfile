# syntax=docker/dockerfile:1

# --- Etapa 1: build do front (não vai para a imagem final) ---
FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- Etapa 2: imagem final, só com o necessário para rodar ---
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=/app/static

# Aplica as correções de segurança do sistema que saíram depois da imagem base.
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y install --no-install-recommends zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY api/requirements.txt ./
# Instala as dependências e remove o pip: ele não é usado em execução e traz
# bibliotecas embutidas (urllib3, msgpack, setuptools) que só aumentam a
# superfície de ataque da imagem.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

COPY api/app ./app
COPY api/data ./data
COPY --from=web /web/dist ./static

# Usuário sem privilégios e sem shell: a aplicação nunca roda como root.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
