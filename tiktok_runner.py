"""
tiktok_runner.py — Envia o próximo clipe da fila output_tiktok/ para o TikTok.

Uso:
    python tiktok_runner.py

Execute este script manualmente (ou via cron/launchd a cada 3 horas) para postar
um clipe por vez, evitando bloqueios anti-bot do TikTok por múltiplos uploads
em sequência.
"""

import os
import sys

# Garante que imports relativos a src/ funcionem independente de onde o script é chamado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from src.uploader_tiktok import executar_ciclo_tiktok

if __name__ == "__main__":
    executar_ciclo_tiktok()
