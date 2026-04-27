#!/usr/bin/env bash
# setup_cron.sh — Instala os jobs do ClipsAutomation no crontab
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT_DIR/venv/bin/python3"
LOG_MAIN="$PROJECT_DIR/logs/main.log"
LOG_TIKTOK="$PROJECT_DIR/logs/tiktok.log"

echo "============================================"
echo "  ClipsAutomation — Instalação do Crontab"
echo "============================================"
echo ""

# Valida que o venv existe
if [ ! -f "$PYTHON" ]; then
    echo "[-] venv/bin/python3 não encontrado em $PROJECT_DIR"
    echo "    Execute primeiro: bash setup_vps.sh"
    exit 1
fi

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# ---------------------------------------------------------------------------
# Monta as duas linhas de cron
# ---------------------------------------------------------------------------
CRON_MAIN="0 7 * * * $PYTHON $PROJECT_DIR/main.py >> $LOG_MAIN 2>&1"
CRON_TIKTOK="0 0,3,6,9,12,15,18,21 * * * $PYTHON $PROJECT_DIR/tiktok_runner.py >> $LOG_TIKTOK 2>&1"

# ---------------------------------------------------------------------------
# Injeta no crontab sem duplicar entradas existentes
# ---------------------------------------------------------------------------
# Lê crontab atual (ignora erro se estiver vazio)
CRONTAB_ATUAL="$(crontab -l 2>/dev/null || true)"

# Remove linhas antigas do projeto (se houver), depois adiciona as novas
CRONTAB_NOVO="$(
    echo "$CRONTAB_ATUAL" \
    | grep -v "ClipsAutomation" \
    | grep -v "$PROJECT_DIR/main.py" \
    | grep -v "$PROJECT_DIR/tiktok_runner.py"
)"

# Adiciona marcadores e as novas entradas
CRONTAB_NOVO="${CRONTAB_NOVO}
# --- ClipsAutomation ---
$CRON_MAIN
$CRON_TIKTOK
# -----------------------"

echo "$CRONTAB_NOVO" | crontab -

# ---------------------------------------------------------------------------
# Confirmação
# ---------------------------------------------------------------------------
echo "[+] Crontab atualizado:"
echo ""
echo "    Pipeline principal (todo dia às 07:00):"
echo "      $CRON_MAIN"
echo ""
echo "    TikTok runner (a cada 3 horas — 0h, 3h, 6h ... 21h):"
echo "      $CRON_TIKTOK"
echo ""
echo "    Logs:"
echo "      main.py      → $LOG_MAIN"
echo "      tiktok_runner → $LOG_TIKTOK"
echo ""
echo "[+] Crontab instalado com sucesso."
echo ""
