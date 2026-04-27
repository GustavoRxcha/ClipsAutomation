"""
tiktok_runner.py — Envia o próximo clipe da fila output_tiktok/ para o TikTok.

Uso normal (cron / launchd a cada 3 horas):
    python tiktok_runner.py

Autenticação:
    O bot usa TIKTOK_SESSION_ID do .env.
    Quando o sessionid expirar (~60-90 dias):
        1. Acesse tiktok.com no seu browser e faça login
        2. F12 → Application → Cookies → tiktok.com → copie o valor de "sessionid"
        3. Atualize TIKTOK_SESSION_ID no .env
"""

import os
import sys

# Garante que imports relativos a src/ funcionem independente de onde o script é chamado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

if __name__ == "__main__":
    args = sys.argv[1:]

    from src.uploader_tiktok import executar_ciclo_tiktok
    executar_ciclo_tiktok()
