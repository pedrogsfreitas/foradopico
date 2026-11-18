#!/bin/sh
# Atualiza uma VM criada antes de o MVP ter banco e chaves.
# Rode uma única vez, a partir da sua máquina (PowerShell ou bash):
#   scp -i ~/.ssh/foradopico_rsa infra/atualizar-vm.sh azureuser@SEU-HOST:/tmp/
#   ssh -i ~/.ssh/foradopico_rsa azureuser@SEU-HOST "sudo sh /tmp/atualizar-vm.sh"
# O que faz: gera as chaves do MVP na própria VM (/opt/foradopico/.env),
# acrescenta o volume de dados ao compose e recria o container do app.
set -eu
cd /opt/foradopico

if [ ! -f .env ]; then
  umask 077
  printf 'ROBOT_API_KEY=%s\nSENSOR_API_KEY=%s\nHR_ACCESS_CODE=%s\nLLM_API_URL=\n' \
    "$(openssl rand -hex 24)" "$(openssl rand -hex 24)" "$(openssl rand -hex 8)" > .env
  echo "Chaves geradas em /opt/foradopico/.env"
else
  echo "/opt/foradopico/.env já existe; mantido."
fi

IMAGE=$(sed -n 's/^ *image: *\(ghcr\.io[^ ]*\) *$/\1/p' compose.yml | head -n 1)
[ -n "$IMAGE" ] || { echo "Não encontrei a imagem do app em compose.yml" >&2; exit 1; }
cp compose.yml "compose.yml.anterior"

cat > compose.yml <<YAML
services:
  app:
    image: ${IMAGE}
    restart: unless-stopped
    env_file:
      - /opt/foradopico/.env
    volumes:
      - app-data:/data
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    expose:
      - "8000"

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /opt/foradopico/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    security_opt:
      - no-new-privileges:true
    depends_on:
      - app

volumes:
  app-data:
  caddy-data:
  caddy-config:
YAML

docker compose -f compose.yml pull --quiet app
docker compose -f compose.yml up -d --remove-orphans
echo
echo "Pronto. Para ver as chaves (não compartilhe em canais públicos):"
echo "  sudo cat /opt/foradopico/.env"
