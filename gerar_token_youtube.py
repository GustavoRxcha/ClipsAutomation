"""
Gera token.json do YouTube OAuth2 localmente (requer browser).
Execute UMA VEZ no seu computador pessoal, depois copie token.json para a VPS.

Uso:
    python gerar_token_youtube.py
"""
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
secrets_path = os.path.join(BASE_DIR, "client_secrets.json")
token_path = os.path.join(BASE_DIR, "token.json")

if not os.path.exists(secrets_path):
    print(f"[-] client_secrets.json não encontrado em: {secrets_path}")
    print("    Baixe em: console.cloud.google.com → APIs & Services → Credentials")
    exit(1)

print("[*] Abrindo browser para autorização do YouTube...")
flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
creds = flow.run_local_server(port=0)

with open(token_path, "w") as fh:
    fh.write(creds.to_json())

print(f"\n[+] token.json salvo em: {token_path}")
print("\nAgora copie para a VPS com:")
print(f"    scp {token_path} root@<IP_DA_VPS>:/root/ClipsAutomation/token.json")
