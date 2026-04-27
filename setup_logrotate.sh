#!/usr/bin/env bash
# setup_logrotate.sh — Instala config de rotação de logs do ClipsAutomation
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGROTATE_CONF="/etc/logrotate.d/clipsautomation"

echo "============================================"
echo "  ClipsAutomation — Setup Logrotate"
echo "============================================"
echo ""

# Valida que está rodando como root
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Este script precisa ser executado como root (use sudo)."
    exit 1
fi

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# ---------------------------------------------------------------------------
# Gera o arquivo de configuração do logrotate
# ---------------------------------------------------------------------------
cat > "$LOGROTATE_CONF" <<EOF
$PROJECT_DIR/logs/main.log
$PROJECT_DIR/logs/tiktok.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF

# ---------------------------------------------------------------------------
# Confirmação
# ---------------------------------------------------------------------------
echo "[+] Configuração instalada em: $LOGROTATE_CONF"
echo ""
echo "    Arquivos rotacionados:"
echo "      $PROJECT_DIR/logs/main.log"
echo "      $PROJECT_DIR/logs/tiktok.log"
echo ""
echo "    Política:"
echo "      - Rotação diária"
echo "      - Histórico de 7 dias"
echo "      - Compressão gzip (com delaycompress)"
echo "      - Sem erro se o log não existir (missingok)"
echo "      - Ignora logs vazios (notifempty)"
echo ""
echo "[+] Logrotate configurado com sucesso."
echo ""
