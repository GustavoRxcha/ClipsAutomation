# ============================================================
# ClipsAutomation — VPS pipeline (main.py)
# TikTok uploader (tiktok_runner.py) roda no Mac, não aqui.
# ============================================================

FROM python:3.11-slim

# ------------------------------------------------------------
# Dependências de sistema
# ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        cron \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Fuso horário padrão (sobrescreva com TZ= no .env se necessário)
ENV TZ=America/Sao_Paulo

WORKDIR /app

# ------------------------------------------------------------
# Dependências Python (sem tiktok-uploader — exclusivo do Mac)
# ------------------------------------------------------------
COPY requirements-vps.txt .
RUN pip install --no-cache-dir -r requirements-vps.txt

# ------------------------------------------------------------
# Código fonte
# (credenciais e runtime dirs são montados como volumes)
# ------------------------------------------------------------
COPY . .

# Diretório de cache dos modelos do Whisper (faster-whisper usa HF_HOME)
ENV HF_HOME=/app/models

# ------------------------------------------------------------
# Crontab — espelha o setup_cron.sh (todo dia às 07:00)
# ------------------------------------------------------------
RUN echo "0 7 * * * root cd /app && /usr/local/bin/python main.py >> /app/logs/main.log 2>&1" \
    > /etc/cron.d/clipsautomation \
    && chmod 0644 /etc/cron.d/clipsautomation

# ------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
