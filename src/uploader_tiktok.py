import os
import threading
from datetime import datetime, timedelta

_INTERVALO_HORAS = int(os.getenv("TIKTOK_INTERVALO_HORAS", "3"))
_TITULO_MAX = 150  # TikTok aceita até 150 caracteres na descrição


def _carregar_lib():
    """Importa tiktok-uploader em tempo de execução para não quebrar sem a lib."""
    try:
        from tiktok_uploader.upload import upload_video
        return upload_video
    except ImportError:
        return None


def fazer_upload_tiktok(arquivos: list, titulo_base: str) -> list:
    """
    Faz upload de cada MP4 para o TikTok com publicação agendada progressiva.

    Clipe 1 → publicado imediatamente.
    Clipe N → agendado para (N-1) * 3 horas a partir do momento do upload.

    Requer cookies exportados do TikTok salvos em tiktok_cookies.json na raiz
    do projeto (formato Netscape/JSON compatível com tiktok-uploader).

    Args:
        arquivos:    Lista de caminhos absolutos dos clipes gerados.
        titulo_base: Título base derivado do vídeo original.

    Returns:
        Lista de identificadores (nome do arquivo) dos vídeos enviados com sucesso.
    """
    upload_video = _carregar_lib()
    if upload_video is None:
        print("[-] Biblioteca tiktok-uploader não instalada.")
        print("[-] Execute: pip install tiktok-uploader")
        return []

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cookies_path = os.path.join(base_dir, "tiktok_cookies.json")

    if not os.path.exists(cookies_path):
        print(f"[-] tiktok_cookies.json não encontrado em: {cookies_path}")
        print("[-] Exporte seus cookies do TikTok e salve na raiz do projeto.")
        print("[-] Use uma extensão como 'Get cookies.txt LOCALLY' e renomeie para tiktok_cookies.json.")
        return []

    print("\n[*] Iniciando uploads para o TikTok...")

    agora = datetime.utcnow()  # naive UTC — exigido pela tiktok-uploader
    enviados = []

    for i, caminho in enumerate(arquivos, 1):
        sufixo = " #tiktok"
        max_base = _TITULO_MAX - len(sufixo)
        descricao = titulo_base[:max_base].rstrip() + sufixo

        delay_horas = (i - 1) * _INTERVALO_HORAS

        if delay_horas == 0:
            schedule_dt = None
            horario_info = "publicação imediata"
        else:
            schedule_dt = agora + timedelta(hours=delay_horas)
            horario_info = f"agendado para {schedule_dt.strftime('%d/%m/%Y %H:%M')} UTC (+{delay_horas}h)"

        print(f"[*] Enviando {i}/{len(arquivos)}: {os.path.basename(caminho)} — {horario_info} ...")

        kwargs = dict(filename=caminho, description=descricao, cookies=cookies_path)
        if schedule_dt is not None:
            kwargs["schedule"] = schedule_dt

        resultado: dict = {}

        def _executar(kw=kwargs, res=resultado):
            try:
                res["falhas"] = upload_video(**kw)
            except Exception as exc:
                res["erro"] = exc

        # Cada upload roda em thread própria para garantir contexto Playwright limpo
        t = threading.Thread(target=_executar)
        t.start()
        t.join()

        if "erro" in resultado:
            print(f"[-] Erro inesperado ao enviar corte {i}: {resultado['erro']}")
        elif resultado.get("falhas"):
            print(f"[-] Erro ao enviar corte {i}: {resultado['falhas']}")
        else:
            print(f"[+] Corte {i} enviado com sucesso ({horario_info})")
            enviados.append(os.path.basename(caminho))

    return enviados
