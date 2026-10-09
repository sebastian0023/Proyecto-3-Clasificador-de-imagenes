#!/usr/bin/env bash
# Prepara la EC2 del portal (Amazon Linux 2023) para `docker-compose.prod.yml`.
# Se corre UNA vez, con sudo, dentro de `aws ssm start-session` (Proyecto4/docs/despliegue.md):
#
#   sudo bash instalar_instancia.sh <commit-o-rama>
#
# - Docker, git y los plugins compose y buildx (con su SHA-256 verificado contra la release).
# - 2 GiB de swap: margen ante picos (build de torch, inferencia), no memoria de trabajo.
# - Clona el repositorio PUBLICO por HTTPS en /opt/p4/repo, sin tokens, fijado al commit dado.
# - /opt/p4/secretos (solo root) para los secretos que escribe `preparar_secretos.sh`.
# Es idempotente: correrlo otra vez no duplica nada.
set -euo pipefail

REF="${1:?uso: sudo bash instalar_instancia.sh <commit-o-rama>}"
REPO_URL="https://github.com/sebastian0023/Proyecto-3-Clasificador-de-imagenes.git"
COMPOSE_VERSION="v2.39.2"
BUILDX_VERSION="v0.26.1"
PLUGINS=/usr/local/lib/docker/cli-plugins

[ "$(id -u)" -eq 0 ] || { echo "Correr con sudo." >&2; exit 1; }

echo "==> Paquetes"
dnf install -y -q docker git
systemctl enable --now docker

echo "==> Plugins de Docker (compose ${COMPOSE_VERSION}, buildx ${BUILDX_VERSION})"
mkdir -p "$PLUGINS"
descargar_verificado() { # url url-del-sha256 destino
	local url="$1" sums="$2" dest="$3" tmp
	tmp="$(mktemp -d)"
	curl -fsSL "$url" -o "$tmp/bin"
	curl -fsSL "$sums" -o "$tmp/sums"
	local esperado
	esperado="$(grep -E "$(basename "$url")\$" "$tmp/sums" | awk '{print $1}' | head -1)"
	[ -n "$esperado" ] || esperado="$(awk '{print $1}' "$tmp/sums" | head -1)"
	echo "$esperado  $tmp/bin" | sha256sum -c --quiet
	install -m 0755 "$tmp/bin" "$dest"
	rm -rf "$tmp"
}
if ! docker compose version 2>/dev/null | grep -q "${COMPOSE_VERSION#v}"; then
	base="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}"
	descargar_verificado "$base/docker-compose-linux-x86_64" "$base/docker-compose-linux-x86_64.sha256" "$PLUGINS/docker-compose"
fi
if ! docker buildx version 2>/dev/null | grep -q "${BUILDX_VERSION}"; then
	base="https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}"
	descargar_verificado "$base/buildx-${BUILDX_VERSION}.linux-amd64" "$base/checksums.txt" "$PLUGINS/docker-buildx"
fi
docker compose version
docker buildx version

echo "==> Swap de 2 GiB"
if ! swapon --show | grep -q /swapfile; then
	fallocate -l 2G /swapfile
	chmod 600 /swapfile
	mkswap -q /swapfile
	swapon /swapfile
	grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi
sysctl -q vm.swappiness=10
grep -q '^vm.swappiness' /etc/sysctl.conf || echo 'vm.swappiness=10' >>/etc/sysctl.conf
free -h

echo "==> Repositorio (publico, sin credenciales) en /opt/p4/repo @ ${REF}"
install -d -m 0755 /opt/p4
install -d -m 0700 /opt/p4/secretos
if [ ! -d /opt/p4/repo/.git ]; then
	git clone --quiet "$REPO_URL" /opt/p4/repo
fi
git -C /opt/p4/repo fetch --quiet origin
git -C /opt/p4/repo -c advice.detachedHead=false checkout --quiet "$REF" 2>/dev/null ||
	git -C /opt/p4/repo -c advice.detachedHead=false checkout --quiet "origin/$REF"
echo "Commit desplegado: $(git -C /opt/p4/repo rev-parse HEAD)"

echo "==> Listo. Siguiente: sudo bash /opt/p4/repo/Proyecto4/deploy/preparar_secretos.sh"
