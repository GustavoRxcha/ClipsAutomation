import os
import re
import threading

from .tiktok_auth import garantir_sessao

_TITULO_MAX = 150  # TikTok aceita até 150 caracteres na descrição

# Caminho base do projeto (dois níveis acima deste arquivo: src/ → raiz)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUT_TIKTOK_DIR = os.path.join(_BASE_DIR, "output_tiktok")


def _carregar_lib():
    """Importa tiktok-uploader em tempo de execução para não quebrar sem a lib."""
    try:
        from tiktok_uploader.upload import upload_video
        return upload_video
    except ImportError:
        return None


def _titulo_do_arquivo(nome_arquivo: str) -> str:
    """
    Deriva o título TikTok a partir do nome do arquivo.

    Remove o sufixo _corte_NN (gerado por render.py), adiciona #tiktok,
    e trunca para o máximo permitido pelo TikTok.
    """
    stem = os.path.splitext(nome_arquivo)[0]
    stem_limpo = re.sub(r"_corte_\d+$", "", stem)
    sufixo = " #tiktok"
    max_base = _TITULO_MAX - len(sufixo)
    return stem_limpo[:max_base].rstrip() + sufixo


def executar_ciclo_tiktok() -> None:
    """
    Processa UMA rodada de upload TikTok.

    - Verifica autenticação via TIKTOK_SESSION_ID do .env (ou cookies.json).
    - Lê output_tiktok/ e seleciona o arquivo mais antigo (ordem FIFO).
    - Faz o upload imediato (sem agendamento).
    - Em caso de sucesso, exclui o arquivo.
    - Em caso de falha, mantém o arquivo para nova tentativa.

    Projetado para ser chamado repetidamente via cron / launchd:
        python tiktok_runner.py
    """
    upload_video = _carregar_lib()
    if upload_video is None:
        print("[-] Biblioteca tiktok-uploader não instalada.")
        print("[-] Execute: pip install tiktok-uploader")
        return

    # -----------------------------------------------------------------------
    # Autenticação — sessionid do .env tem prioridade sobre cookies.json
    # -----------------------------------------------------------------------
    session_id = os.getenv("TIKTOK_SESSION_ID", "").strip()

    if not garantir_sessao(session_id):
        print("[-] Upload abortado — sem autenticação TikTok válida.")
        return

    # -----------------------------------------------------------------------
    # Fila de upload
    # -----------------------------------------------------------------------
    if not os.path.isdir(_OUTPUT_TIKTOK_DIR):
        print("[*] output_tiktok/ vazia. Nada a fazer.")
        return

    arquivos = [
        os.path.join(_OUTPUT_TIKTOK_DIR, f)
        for f in os.listdir(_OUTPUT_TIKTOK_DIR)
        if os.path.isfile(os.path.join(_OUTPUT_TIKTOK_DIR, f))
        and f.lower().endswith(".mp4")
    ]

    if not arquivos:
        print("[*] output_tiktok/ vazia. Nada a fazer.")
        return

    # Seleciona o arquivo mais antigo (FIFO)
    arquivos.sort(key=os.path.getmtime)
    caminho = arquivos[0]
    nome = os.path.basename(caminho)

    descricao = _titulo_do_arquivo(nome)
    restantes = len(arquivos) - 1

    print(f"\n[*] Iniciando upload TikTok: {nome}")
    print(f"[*] Descrição: {descricao}")
    print(f"[*] Restantes na fila após este: {restantes}")

    kwargs = dict(
        filename=caminho,
        description=descricao,
        cookies_list=[{
            "name": "sessionid",
            "value": session_id,
            "domain": ".tiktok.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None",
        }],
        headless=True,
    )
    resultado: dict = {}

    def _executar(kw=kwargs, res=resultado):
        try:
            res["falhas"] = upload_video(**kw)
        except Exception as exc:
            res["erro"] = exc

    # Upload em thread própria para garantir contexto Playwright limpo
    t = threading.Thread(target=_executar)
    t.start()
    t.join()

    if "erro" in resultado:
        erro = resultado["erro"]
        print(f"[-] Erro inesperado ao enviar: {erro}")
        # Detecta erro de autenticação para avisar sobre sessionid expirado
        if any(kw in str(erro).lower() for kw in ("auth", "session", "login", "403", "cookie")):
            print("[!] Erro pode indicar sessionid expirado.")
            print("[!] Atualize TIKTOK_SESSION_ID no .env com o cookie 'sessionid' do tiktok.com.")
        print(f"[-] Falha — arquivo mantido para retry: {nome}")
    elif resultado.get("falhas"):
        print(f"[-] Erro ao enviar: {resultado['falhas']}")
        print(f"[-] Falha — arquivo mantido para retry: {nome}")
    else:
        try:
            os.remove(caminho)
        except OSError as exc:
            print(f"[-] Upload OK, mas falha ao remover arquivo: {exc}")
        else:
            print(f"[+] Corte enviado e removido: {nome}")
