"""
tiktok_runner.py — Envia o próximo clipe da fila para o TikTok.

Modo local (padrão):
    Lê clipes de output_tiktok/ na máquina local.

Modo VPS (quando VPS_HOST está configurado no .env):
    Baixa o clipe mais antigo da VPS via SCP, faz upload, e apaga da VPS.

Uso (launchd a cada 2 horas):
    python tiktok_runner.py

Retry automático:
    Em caso de falha (ex: timeout SSH), aguarda 20 minutos e tenta novamente.
    Máximo de 3 tentativas por execução antes de abortar.

Autenticação TikTok:
    Quando o sessionid expirar (~60-90 dias):
        1. Acesse tiktok.com no seu browser e faça login
        2. F12 → Application → Cookies → tiktok.com → copie o valor de "sessionid"
        3. Atualize TIKTOK_SESSION_ID no .env
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

MAX_TENTATIVAS = 3
ESPERA_RETRY_SEGUNDOS = 20 * 60  # 20 minutos

if __name__ == "__main__":
    VPS_HOST      = os.getenv("VPS_HOST", "").strip()
    VPS_USER      = os.getenv("VPS_USER", "root").strip()
    VPS_KEY_PATH  = os.getenv("VPS_KEY_PATH", "").strip()
    VPS_REMOTE_DIR = os.getenv("VPS_REMOTE_DIR", "/root/ClipsAutomation/output_tiktok").strip()

    if VPS_HOST:
        # ----------------------------------------------------------------
        # Modo VPS: baixa da VPS, faz upload, apaga da VPS em caso de êxito
        # ----------------------------------------------------------------
        from src.vps_sync import buscar_proximo_arquivo, baixar_arquivo, deletar_arquivo
        from src.uploader_tiktok import executar_ciclo_tiktok

        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                print(f"[*] Modo VPS — conectando em {VPS_USER}@{VPS_HOST}... (tentativa {tentativa}/{MAX_TENTATIVAS})")
                remote_path = buscar_proximo_arquivo(VPS_HOST, VPS_USER, VPS_KEY_PATH, VPS_REMOTE_DIR)

                if not remote_path:
                    print("[*] Fila da VPS vazia. Nada a fazer.")
                    sys.exit(0)

                nome_arquivo = os.path.basename(remote_path)
                local_path = os.path.join(BASE_DIR, "output_tiktok", nome_arquivo)
                os.makedirs(os.path.join(BASE_DIR, "output_tiktok"), exist_ok=True)

                print(f"[*] Baixando: {nome_arquivo}")
                if not baixar_arquivo(VPS_HOST, VPS_USER, VPS_KEY_PATH, remote_path, local_path):
                    raise RuntimeError("Falha no download via SCP.")

                print(f"[+] Download concluído. Iniciando upload TikTok...")
                executar_ciclo_tiktok()

                # Se o arquivo local foi removido pelo uploader = upload OK → apaga da VPS
                if not os.path.isfile(local_path):
                    print(f"[*] Apagando da VPS: {remote_path}")
                    deletar_arquivo(VPS_HOST, VPS_USER, VPS_KEY_PATH, remote_path)
                else:
                    print(f"[-] Upload falhou — arquivo mantido na VPS para retry.")

                break  # ciclo concluído com sucesso — encerra o loop de retry

            except Exception as e:
                print(f"[-] Erro na tentativa {tentativa}/{MAX_TENTATIVAS}: {e}")
                if tentativa < MAX_TENTATIVAS:
                    print(f"[*] Aguardando 20 minutos antes de tentar novamente...")
                    time.sleep(ESPERA_RETRY_SEGUNDOS)
                else:
                    print(f"[-] Todas as {MAX_TENTATIVAS} tentativas falharam. Abortando.")
                    sys.exit(1)

    else:
        # ----------------------------------------------------------------
        # Modo local: lê output_tiktok/ da máquina local
        # ----------------------------------------------------------------
        from src.uploader_tiktok import executar_ciclo_tiktok
        executar_ciclo_tiktok()
