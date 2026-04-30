import os
import yt_dlp


def baixar_video(url: str, pasta_destino: str) -> str | None:
    """
    Faz o download do vídeo do YouTube na resolução máxima disponível.

    Args:
        url: URL do vídeo do YouTube.
        pasta_destino: Caminho absoluto da pasta onde o vídeo será salvo.

    Returns:
        Caminho absoluto do arquivo baixado, ou None em caso de falha.
    """
    print(f"[*] Iniciando o download do vídeo: {url}")

    # Arquivo de cookies do YouTube (opcional) — exportar do browser em formato Netscape
    # e configurar YOUTUBE_COOKIES_FILE no .env com o caminho absoluto do arquivo.
    cookies_file = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()

    ydl_opts = {
        # Prefere mp4+m4a (sem transcodificação); fallback para melhor disponível
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(pasta_destino, "%(title)s.%(ext)s"),
        "noprogress": False,
        # necessário para resolver o desafio JS do YouTube em servidores sem browser
        "remote_components": ["ejs:github"],
        # CLI default é deno, mas instalamos nodejs no setup_vps.sh
        "js_runtimes": {"node": {}},
    }

    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
        print(f"[*] Usando cookies de: {cookies_file}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("[*] Baixando... (isso pode levar alguns segundos)")
            info = ydl.extract_info(url, download=True)
            titulo = info.get("title", "video")
            print(f"[*] Título: {titulo}")

            # Reconstrói o caminho do arquivo gerado
            nome_arquivo = ydl.prepare_filename(info)
            # O yt-dlp pode alterar a extensão após merge; tenta extensões comuns
            for ext in ("", ".mp4", ".mkv", ".webm"):
                candidato = nome_arquivo if not ext else os.path.splitext(nome_arquivo)[0] + ext
                if os.path.isfile(candidato):
                    print(f"\n[+] Download concluído: {candidato}")
                    return candidato

            # Fallback: procura o arquivo mais recente na pasta de destino
            arquivos = sorted(
                (f for f in os.listdir(pasta_destino) if not f.endswith(".part")),
                key=lambda f: os.path.getmtime(os.path.join(pasta_destino, f)),
                reverse=True,
            )
            if arquivos:
                caminho = os.path.join(pasta_destino, arquivos[0])
                print(f"\n[+] Download concluído: {caminho}")
                return caminho

            print("\n[-] Arquivo baixado não encontrado após o download.")
            return None

    except yt_dlp.utils.DownloadError as e:
        print(f"\n[-] Erro ao baixar o vídeo: {e}")
        return None
    except Exception as e:
        print(f"\n[-] Erro inesperado no download: {e}")
        return None
