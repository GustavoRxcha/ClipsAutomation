import os
import math
from faster_whisper import WhisperModel


def _formatar_tempo_srt(segundos: float) -> str:
    """Converte segundos para o formato SRT (HH:MM:SS,mmm)."""
    horas = math.floor(segundos / 3600)
    minutos = math.floor((segundos % 3600) / 60)
    segs = math.floor(segundos % 60)
    milisegundos = math.floor((segundos % 1) * 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milisegundos:03d}"


def transcrever_video(caminho_video: str, pasta_destino: str, modelo: str = "small") -> str:
    """
    Transcreve o áudio do vídeo e gera dois arquivos em `pasta_destino`:
      - <nome>.txt  → usado pelo editor para calcular timestamps dos cortes
      - <nome>.srt  → usado pelo FFmpeg para queimar legendas no vídeo

    Args:
        caminho_video: Caminho absoluto do arquivo de vídeo.
        pasta_destino: Caminho absoluto da pasta onde os arquivos serão salvos.
        modelo: Tamanho do modelo Whisper (tiny, base, small, medium, large).

    Returns:
        Caminho absoluto do arquivo .txt gerado, ou None em caso de falha.
    """
    print(f"\n[*] Iniciando transcrição do arquivo: {caminho_video}")
    print(f"[*] Carregando o modelo Whisper '{modelo}'...")

    try:
        whisper_model = WhisperModel(modelo, device="cpu", compute_type="int8")
        segmentos, info = whisper_model.transcribe(caminho_video, beam_size=5, word_timestamps=True)

        nome_arquivo = os.path.basename(caminho_video).rsplit('.', 1)[0]
        caminho_txt = os.path.join(pasta_destino, nome_arquivo + ".txt")
        caminho_srt = os.path.join(pasta_destino, nome_arquivo + ".srt")

        print(f"[*] Idioma detectado: {info.language}")
        print("[*] Extraindo falas e gerando legendas...")

        # Gera o .txt (para o editor) e o .srt (para o ffmpeg) simultaneamente
        with open(caminho_txt, "w", encoding="utf-8") as f_txt, \
             open(caminho_srt, "w", encoding="utf-8") as f_srt:

            for i, segmento in enumerate(segmentos, start=1):
                # Formato TXT: [0.00s -> 5.34s] Texto da frase
                linha_txt = f"[{segmento.start:.2f}s -> {segmento.end:.2f}s] {segmento.text}"
                print(linha_txt)
                f_txt.write(linha_txt + "\n")

                # Formato SRT padrão
                inicio_srt = _formatar_tempo_srt(segmento.start)
                fim_srt = _formatar_tempo_srt(segmento.end)
                f_srt.write(f"{i}\n")
                f_srt.write(f"{inicio_srt} --> {fim_srt}\n")
                f_srt.write(f"{segmento.text.strip()}\n\n")

        print(f"\n[+] Transcrição concluída! Arquivos salvos em: {pasta_destino}")
        return caminho_txt

    except Exception as e:
        print(f"\n[-] Erro durante a transcrição: {e}")
        return None
