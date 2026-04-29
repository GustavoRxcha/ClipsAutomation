#!/bin/bash
# entrypoint.sh — Prepara o ambiente e inicia o cron em foreground.
set -e

# ------------------------------------------------------------
# Repassa variáveis de ambiente do container para o cron.
# Cron não herda o ambiente do processo pai — sem isso as
# variáveis do .env (YOUTUBE_API_KEY, etc.) ficariam invisíveis.
# ------------------------------------------------------------
printenv | grep -v "^_=" > /etc/environment

# ------------------------------------------------------------
# Garante diretórios de runtime
# ------------------------------------------------------------
mkdir -p /app/logs /app/output_tiktok

# ------------------------------------------------------------
# Cria historico_videos.json vazio se não existir.
# (Docker cria um diretório no lugar do arquivo quando o bind
# mount aponta para um arquivo inexistente no host — corrige isso.)
# ------------------------------------------------------------
if [ -d /app/historico_videos.json ]; then
    rmdir /app/historico_videos.json
fi
if [ ! -f /app/historico_videos.json ]; then
    echo "[]" > /app/historico_videos.json
fi

# ------------------------------------------------------------
# Valida credenciais obrigatórias (aviso, não aborta)
# ------------------------------------------------------------
for f in client_secrets.json token.json; do
    if [ ! -f "/app/$f" ]; then
        echo "[!] Aviso: /app/$f não encontrado — monte-o como volume antes de usar."
    fi
done

echo "[*] Container ClipsAutomation iniciado."
echo "[*] Cron ativo — main.py roda diariamente às 07:00 (TZ=${TZ})."

# Inicia cron em foreground (mantém o container vivo)
exec cron -f
