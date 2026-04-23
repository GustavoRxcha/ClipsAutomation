import os
import shutil
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuração de caminhos absolutos
# Tudo é calculado a partir da localização deste arquivo, garantindo que
# o projeto funcione independentemente de onde o terminal for aberto.
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Adiciona o diretório bin/ ao PATH do processo para que o ffmpeg seja encontrado
# automaticamente, sem necessidade de instalação global.
os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")

# Carrega variáveis do .env (se existir)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------------------
# Importações dos módulos internos (após configurar o PATH)
# ---------------------------------------------------------------------------

from src.downloader import baixar_video
from src.transcriber import transcrever_video
from src.editor import analisar_corte
from src.render import renderizar_cortes
from src.uploader import fazer_upload_shorts

# ---------------------------------------------------------------------------
# Configurações via .env (com valores padrão)
# ---------------------------------------------------------------------------

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
DURACAO_ALVO = float(os.getenv("DURACAO_ALVO_SEGUNDOS", "90"))
DURACAO_MINIMA = float(os.getenv("DURACAO_MINIMA_SEGUNDOS", "45"))
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _configurar_pastas():
    """Cria as pastas necessárias se não existirem."""
    for pasta in [ASSETS_DIR, TEMP_DIR, OUTPUT_DIR]:
        os.makedirs(pasta, exist_ok=True)


def _limpar_pastas(pastas: list):
    """Remove todo o conteúdo das pastas temporárias listadas."""
    print("\n--- LIMPANDO ARQUIVOS TEMPORÁRIOS ---")
    for pasta in pastas:
        if not os.path.exists(pasta):
            continue
        for item in os.listdir(pasta):
            caminho = os.path.join(pasta, item)
            try:
                if os.path.isfile(caminho) or os.path.islink(caminho):
                    os.unlink(caminho)
                elif os.path.isdir(caminho):
                    shutil.rmtree(caminho)
                print(f"[*] Removido: {item}")
            except Exception as e:
                print(f"[-] Erro ao remover {caminho}: {e}")
    print("[+] Limpeza concluída.")


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

def main():
    print("=" * 45)
    print("   GERADOR DE CORTES AUTOMATIZADO")
    print("=" * 45)

    _configurar_pastas()

    url_video = input("\nInsira o link do vídeo do YouTube: ").strip()
    if not url_video:
        print("[-] Nenhuma URL informada. Encerrando.")
        return

    # FASE 1 — Download
    print("\n--- FASE 1: DOWNLOAD ---")
    caminho_video = baixar_video(url_video, pasta_destino=ASSETS_DIR)
    if not caminho_video:
        return

    # FASE 2 — Transcrição
    print("\n--- FASE 2: TRANSCRIÇÃO ---")
    caminho_txt = transcrever_video(caminho_video, pasta_destino=TEMP_DIR, modelo=WHISPER_MODEL)
    if not caminho_txt:
        return

    # FASE 3 — Análise de Corte
    print("\n--- FASE 3: ANÁLISE DE CORTE ---")
    cortes = analisar_corte(caminho_txt, duracao_alvo=DURACAO_ALVO, duracao_minima=DURACAO_MINIMA)
    if not cortes:
        print("\n[-] Nenhum corte gerado. Encerrando.")
        return

    # FASE 4 — Renderização
    print("\n--- FASE 4: RENDERIZAÇÃO (FFmpeg) ---")
    arquivos_finais = renderizar_cortes(
        caminho_video,
        cortes,
        pasta_temp=TEMP_DIR,
        pasta_output=OUTPUT_DIR,
    )

    if arquivos_finais:
        print(f"\n{'=' * 45}")
        print(f"  CONCLUÍDO! {len(arquivos_finais)} corte(s) gerado(s).")
        print(f"  Pasta de saída: {OUTPUT_DIR}")
        print(f"{'=' * 45}")

        # FASE 5 — Upload (opcional)
        resposta = input("\nFazer upload para YouTube Shorts? (s/n): ").strip().lower()
        if resposta == "s":
            print("\n--- FASE 5: UPLOAD PARA YOUTUBE SHORTS ---")
            titulo_base = os.path.basename(caminho_video).rsplit('.', 1)[0]
            urls = fazer_upload_shorts(arquivos_finais, titulo_base)
            if urls:
                print(f"\n[+] {len(urls)} vídeo(s) enviado(s):")
                for url in urls:
                    print(f"    {url}")

        _limpar_pastas([ASSETS_DIR, TEMP_DIR, OUTPUT_DIR])
    else:
        print("\n[-] Nenhum arquivo foi gerado. Verifique os erros acima.")


if __name__ == "__main__":
    main()