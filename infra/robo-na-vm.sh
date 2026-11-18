#!/bin/sh
# Coloca o robô RPA (repositório SemestralRpa) para rodar na VM, ao lado do app.
#
# Rode uma vez, depois do atualizar-vm.sh:
#   scp -i ~/.ssh/foradopico_rsa infra/robo-na-vm.sh azureuser@SEU-HOST:/tmp/
#   ssh -i ~/.ssh/foradopico_rsa azureuser@SEU-HOST "sudo sh /tmp/robo-na-vm.sh"
#
# O robô roda em modo agendador (python -m src.main scheduler): monitora as Linhas
# 1 e 3 no site do Metrô a cada 5 min, importa planilhas e envia agendas.
# Os e-mails ficam em modo console (salvos como .eml no volume), sem senha de SMTP.
set -eu
REPO="${1:-https://github.com/haruoooo/SemestralRpa.git}"
cd /opt/foradopico

[ -f .env ] || { echo "Rode antes o atualizar-vm.sh (ele cria /opt/foradopico/.env)." >&2; exit 1; }
ROBOT_API_KEY=$(sed -n 's/^ROBOT_API_KEY=//p' .env)
[ -n "$ROBOT_API_KEY" ] || { echo "ROBOT_API_KEY vazio em /opt/foradopico/.env" >&2; exit 1; }
docker network inspect foradopico_default >/dev/null 2>&1 || { echo "O app não está rodando (rede foradopico_default ausente)." >&2; exit 1; }

command -v git >/dev/null || { apt-get update -qq && apt-get install -y -qq git; }
rm -rf robo-src
git clone --depth 1 "$REPO" robo-src

cat > robo-src/Dockerfile.foradopico <<'DOCKERFILE'
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /robo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN rm -f .env \
    && useradd --system --uid 10002 --no-create-home --shell /usr/sbin/nologin robo \
    && mkdir -p data/input data/output data/runtime logs landingZone \
    && chown -R 10002 data logs landingZone
USER 10002
CMD ["python", "-m", "src.main", "scheduler"]
DOCKERFILE

docker build -q -t foradopico-robo -f robo-src/Dockerfile.foradopico robo-src

if [ ! -f robo.env ]; then
  umask 077
  cat > robo.env <<ENV
PRODUCT_API_MODE=http
PRODUCT_API_URL=http://app:8000
PRODUCT_API_KEY=${ROBOT_API_KEY}
LINE_STATUS_SOURCE=metroWebsite
NOTIFIER_MODE=console
MAIL_MIN_INTERVAL_SECONDS=0
LOG_SALT=$(openssl rand -hex 24)
ENV
fi

docker rm -f foradopico-robo >/dev/null 2>&1 || true
docker run -d --name foradopico-robo --restart unless-stopped \
  --network foradopico_default --env-file robo.env \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -v robo-dados:/robo/data -v robo-logs:/robo/logs -v robo-pouso:/robo/landingZone \
  foradopico-robo >/dev/null

echo "Robô no ar. Acompanhe com:  sudo docker logs -f foradopico-robo"
echo "Para importar a planilha de demonstração:"
echo "  sudo docker exec foradopico-robo cp data/fixtures/scheduleDemoSmall.xlsx data/input/"
