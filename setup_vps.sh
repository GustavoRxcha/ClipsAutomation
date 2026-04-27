#!/usr/bin/env bash
# setup_vps.sh — Prepara Ubuntu 22.04 do zero para o ClipsAutomation
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  ClipsAutomation — Setup VPS (Ubuntu 22.04)"
echo "============================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Dependências do sistema
# ---------------------------------------------------------------------------
echo "[1/4] Atualizando pacotes e instalando dependências..."
apt update && apt install -y python3 python3-pip python3-venv ffmpeg

# ---------------------------------------------------------------------------
# 2. Ambiente virtual Python
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Criando ambiente virtual e instalando pacotes Python..."
python3 -m venv "$PROJECT_DIR/venv"
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# 3. Pastas necessárias
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Criando pastas do projeto..."
mkdir -p \
    "$PROJECT_DIR/assets" \
    "$PROJECT_DIR/temp" \
    "$PROJECT_DIR/output" \
    "$PROJECT_DIR/output_tiktok" \
    "$PROJECT_DIR/logs"
echo "      assets/ temp/ output/ output_tiktok/ logs/ — OK"

# ---------------------------------------------------------------------------
# 4. Checklist final
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Setup concluído."
echo ""
echo "============================================"
echo "  CHECKLIST — Copie manualmente para:"
echo "  $PROJECT_DIR"
echo "============================================"
echo ""
echo "  [ ] .env                  — variáveis de ambiente (baseie-se no .env.example)"
echo "  [ ] client_secrets.json   — credenciais OAuth2 do Google Cloud Console"
echo "  [ ] historico_videos.json — histórico de vídeos já processados (opcional)"
echo ""
echo "  Após copiar os arquivos, execute:"
echo "    bash $PROJECT_DIR/setup_cron.sh"
echo ""
