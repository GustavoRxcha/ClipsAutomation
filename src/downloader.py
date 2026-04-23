import os
from pytubefix import YouTube
from pytubefix.cli import on_progress


def baixar_video(url: str, pasta_destino: str) -> str:
    """
    Faz o download do vídeo do YouTube na resolução máxima disponível.

    Args:
        url: URL do vídeo do YouTube.
        pasta_destino: Caminho absoluto da pasta onde o vídeo será salvo.

    Returns:
        Caminho absoluto do arquivo baixado, ou None em caso de falha.
    """
    print(f"[*] Iniciando o download do vídeo: {url}")

    try:
        # Usamos o client ANDROID_VR para contornar restrições do YouTube na API web
        yt = YouTube(url, on_progress_callback=on_progress, client='ANDROID_VR')

        print(f"[*] Título encontrado: {yt.title}")

        stream = yt.streams.get_highest_resolution()

        print("[*] Baixando... (isso pode levar alguns segundos)")

        arquivo_baixado = stream.download(output_path=pasta_destino)

        print(f"\n[+] Download concluído com sucesso: {arquivo_baixado}")
        return arquivo_baixado

    except Exception as e:
        print(f"\n[-] Erro ao baixar o vídeo: {e}")
        return None
