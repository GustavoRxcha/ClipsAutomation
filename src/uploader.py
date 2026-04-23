import os
from datetime import datetime, timezone, timedelta

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_CHUNK_SIZE = 1024 * 1024  # 1 MB
_INTERVALO_HORAS = 3


def _get_credentials(token_path: str, secrets_path: str) -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as fh:
            fh.write(creds.to_json())

    return creds


def fazer_upload_shorts(arquivos: list, titulo_base: str) -> list:
    """
    Faz upload de cada MP4 como YouTube Short com publicação agendada progressiva.

    Clipe 1 → publicado imediatamente (público).
    Clipe N → agendado para (N-1) * 3 horas a partir do momento do upload.

    Args:
        arquivos:    Lista de caminhos absolutos dos clipes gerados.
        titulo_base: Título base derivado do vídeo original.

    Returns:
        Lista de URLs dos vídeos enviados com sucesso.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    secrets_path = os.path.join(base_dir, "client_secrets.json")
    token_path = os.path.join(base_dir, "token.json")

    if not os.path.exists(secrets_path):
        print(f"[-] client_secrets.json não encontrado em: {secrets_path}")
        print("[-] Faça o download em console.cloud.google.com e salve na raiz do projeto.")
        return []

    print("\n[*] Autenticando com o YouTube...")
    try:
        creds = _get_credentials(token_path, secrets_path)
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"[-] Falha na autenticação: {e}")
        return []

    agora = datetime.now(timezone.utc)
    urls = []

    for i, caminho in enumerate(arquivos, 1):
        sufixo = f" #{i} #shorts"
        max_base = 100 - len(sufixo)
        titulo = titulo_base[:max_base].rstrip() + sufixo
        delay_horas = (i - 1) * _INTERVALO_HORAS

        if delay_horas == 0:
            status = {"privacyStatus": "public"}
            horario_info = "publicação imediata"
        else:
            publish_at = agora + timedelta(hours=delay_horas)
            status = {
                "privacyStatus": "private",
                "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            }
            horario_info = f"agendado para {publish_at.strftime('%d/%m/%Y %H:%M')} UTC (+{delay_horas}h)"

        body = {
            "snippet": {
                "title": titulo,
                "description": "#shorts",
                "categoryId": "22",
            },
            "status": {**status, "selfDeclaredMadeForKids": False},
        }

        print(f"[*] Enviando {i}/{len(arquivos)}: {os.path.basename(caminho)} — {horario_info} ...")
        try:
            media = MediaFileUpload(caminho, mimetype="video/mp4", resumable=True, chunksize=_CHUNK_SIZE)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response.get("id", "")
            url = f"https://www.youtube.com/shorts/{video_id}"
            print(f"[+] Corte {i} enviado: {url} ({horario_info})")
            urls.append(url)

        except HttpError as e:
            if e.resp.status == 403:
                print(f"[-] Cota do YouTube atingida. Uploads restantes ignorados.")
                break
            print(f"[-] Erro HTTP ao enviar corte {i}: {e}")
        except Exception as e:
            print(f"[-] Erro inesperado ao enviar corte {i}: {e}")

    return urls
