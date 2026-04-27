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
OUTPUT_TIKTOK_DIR = os.path.join(BASE_DIR, "output_tiktok")

# No Windows usa o ffmpeg bundled em bin/; no macOS/Linux usa o do PATH do sistema.
if os.path.isdir(BIN_DIR):
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
from src.uploader_youtube import fazer_upload_shorts
from src.finder import buscar_video_canal, registrar_video_processado, extrair_video_id

# ---------------------------------------------------------------------------
# Configurações via .env (com valores padrão)
# ---------------------------------------------------------------------------

WHISPER_MODEL     = os.getenv("WHISPER_MODEL", "small")
DURACAO_ALVO      = float(os.getenv("DURACAO_ALVO_SEGUNDOS", "90"))
DURACAO_MINIMA    = float(os.getenv("DURACAO_MINIMA_SEGUNDOS", "45"))
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
CANAL_MAX_VIDEOS  = int(os.getenv("YOUTUBE_CANAL_MAX_VIDEOS", "20"))


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _configurar_pastas():
    """Cria as pastas necessárias se não existirem."""
    for pasta in [ASSETS_DIR, TEMP_DIR, OUTPUT_DIR, OUTPUT_TIKTOK_DIR]:
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
# Fluxo principal — totalmente autônomo
# ---------------------------------------------------------------------------

def main():
    print("=" * 50)
    print("   GERADOR DE CORTES AUTOMATIZADO")
    print("=" * 50)

    _configurar_pastas()

    # Valida canal configurado
    if not YOUTUBE_CHANNEL_ID:
        print("[-] YOUTUBE_CHANNEL_ID não configurado no .env. Encerrando.")
        return

    # SELEÇÃO AUTOMÁTICA — vídeo mais viral do canal
    print(f"\n[*] Canal: {YOUTUBE_CHANNEL_ID}  |  Analisando últimos {CANAL_MAX_VIDEOS} vídeo(s) ...")
    video_canal = buscar_video_canal(YOUTUBE_CHANNEL_ID, max_videos=CANAL_MAX_VIDEOS)
    if not video_canal:
        print("[-] Nenhum vídeo disponível no canal. Encerrando.")
        return

    url_video = video_canal["url"]
    video_id  = extrair_video_id(url_video)

    # FASE 1 — Download
    print("\n--- FASE 1: DOWNLOAD ---")
    caminho_video = baixar_video(url_video, pasta_destino=ASSETS_DIR)
    if not caminho_video:
        return

    # Registra no histórico somente após download bem-sucedido
    if video_id:
        registrar_video_processado(video_id)

    # FASE 2 — Transcrição
    print("\n--- FASE 2: TRANSCRIÇÃO ---")
    caminho_txt = transcrever_video(caminho_video, pasta_destino=TEMP_DIR, modelo=WHISPER_MODEL)
    if not caminho_txt:
        _limpar_pastas([ASSETS_DIR, TEMP_DIR])
        return

    # FASE 3 — Análise de Corte
    print("\n--- FASE 3: ANÁLISE DE CORTE ---")
    cortes = analisar_corte(caminho_txt, duracao_alvo=DURACAO_ALVO, duracao_minima=DURACAO_MINIMA)
    if not cortes:
        print("[-] Nenhum corte gerado. Encerrando.")
        _limpar_pastas([ASSETS_DIR, TEMP_DIR])
        return

    # FASE 4 — Renderização
    print("\n--- FASE 4: RENDERIZAÇÃO (FFmpeg) ---")
    arquivos_finais = renderizar_cortes(
        caminho_video,
        cortes,
        pasta_temp=TEMP_DIR,
        pasta_output=OUTPUT_DIR,
    )

    if not arquivos_finais:
        print("[-] Nenhum arquivo foi gerado. Verifique os erros acima.")
        _limpar_pastas([ASSETS_DIR, TEMP_DIR])
        return

    print(f"\n{'=' * 50}")
    print(f"  RENDERIZAÇÃO CONCLUÍDA! {len(arquivos_finais)} corte(s) gerado(s).")
    print(f"{'=' * 50}")

    titulo_base = os.path.basename(caminho_video).rsplit(".", 1)[0]

    # FASE 5 — Upload para YouTube Shorts (automático)
    print("\n--- FASE 5: UPLOAD PARA YOUTUBE SHORTS ---")
    urls = fazer_upload_shorts(arquivos_finais, titulo_base)
    if urls:
        print(f"\n[+] {len(urls)} vídeo(s) enviado(s) ao YouTube:")
        for url in urls:
            print(f"    {url}")
    else:
        print("[-] Nenhum vídeo enviado ao YouTube.")

    # FASE 6 — Mover clipes para output_tiktok/
    print("\n--- FASE 6: FILA TIKTOK ---")
    movidos = 0
    for arq in arquivos_finais:
        if os.path.isfile(arq):
            shutil.move(arq, OUTPUT_TIKTOK_DIR)
            movidos += 1
    if movidos:
        print(f"[+] {movidos} clipe(s) movidos para output_tiktok/")
        print("[*] Execute 'python tiktok_runner.py' para postar no TikTok.")

    # FASE 7 — Limpeza de arquivos temporários
    _limpar_pastas([ASSETS_DIR, TEMP_DIR, OUTPUT_DIR])

    print(f"\n{'=' * 50}")
    print("  PIPELINE CONCLUÍDO COM SUCESSO.")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
