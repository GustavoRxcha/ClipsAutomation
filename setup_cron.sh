#!/usr/bin/env bash
# setup_cron.sh — Instala o job do ClipsAutomation no crontab da VPS
#
# Nota: o upload para o TikTok não roda na VPS.
#       Ele é executado no Mac local via launchd (com.clipsautomation.tiktok.plist).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_MAIN="$PROJECT_DIR/logs/main.log"

echo "============================================"
echo "  ClipsAutomation — Instalação do Crontab"
echo "============================================"
echo ""

if [ ! -f "$PYTHON" ]; then
    echo "[-] venv/bin/python3 não encontrado em $PROJECT_DIR"
    echo "    Execute primeiro: bash setup_vps.sh"
    exit 1
fi

mkdir -p "$PROJECT_DIR/logs"

CRON_MAIN="0 7 * * * $PYTHON $PROJECT_DIR/main.py >> $LOG_MAIN 2>&1"

CRONTAB_ATUAL="$(crontab -l 2>/dev/null || true)"

CRONTAB_NOVO="$(
    echo "$CRONTAB_ATUAL" \
    | grep -v "ClipsAutomation" \
    | grep -v "$PROJECT_DIR/main.py"
)"

CRONTAB_NOVO="${CRONTAB_NOVO}
# --- ClipsAutomation ---
$CRON_MAIN
# -----------------------"

echo "$CRONTAB_NOVO" | crontab -

echo "[+] Crontab atualizado:"
echo ""
echo "    Pipeline principal (todo dia às 07:00):"
echo "      $CRON_MAIN"
echo ""
echo "    Log: $LOG_MAIN"
echo ""
echo "[+] Crontab instalado com sucesso."
echo ""
echo "    ATENÇÃO: o upload para o TikTok roda no Mac via launchd."
echo "    Para ativá-lo no Mac, execute:"
echo "      launchctl bootstrap gui/\$(id -u) com.clipsautomation.tiktok.plist"
echo ""
