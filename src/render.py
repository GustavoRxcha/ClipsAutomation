import os
import ctypes
import textwrap
import subprocess


# ---------------------------------------------------------------------------
# Helper Windows: caminho curto (8.3) sem espaços para o filtro subtitles
# ---------------------------------------------------------------------------

def _short_path(path: str) -> str:
    """
    Converte um caminho Windows para o formato curto 8.3 (ex: PROJET~1),
    eliminando espaços que quebrariam o filtro 'subtitles' do FFmpeg.
    Retorna o caminho original se a conversão falhar.
    """
    buf = ctypes.create_unicode_buffer(32768)
    ctypes.windll.kernel32.GetShortPathNameW(path, buf, 32768)
    return buf.value if buf.value else path


# ---------------------------------------------------------------------------
# Helpers de tempo SRT
# ---------------------------------------------------------------------------

def _parse_srt_time(time_str: str) -> float:
    """Converte tempo SRT (HH:MM:SS,mmm) para segundos."""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def _format_srt_time(seconds: float) -> str:
    """Converte segundos para o formato de texto SRT (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ---------------------------------------------------------------------------
# Otimização de texto de legenda
# ---------------------------------------------------------------------------

def _otimizar_texto_legenda(texto: str, caracteres_por_linha: int = 30) -> list:
    """
    Quebra um texto longo em blocos de no máximo 2 linhas curtas.
    Retorna uma lista de strings, cada uma pronta para ser uma entrada SRT.
    """
    texto_limpo = " ".join(texto.split())
    linhas = textwrap.wrap(texto_limpo, width=caracteres_por_linha)

    blocos = []
    for i in range(0, len(linhas), 2):
        blocos.append("\n".join(linhas[i:i + 2]))
    return blocos


# ---------------------------------------------------------------------------
# Geração do SRT individual por corte
# ---------------------------------------------------------------------------

def _gerar_srt_do_corte(srt_original: str, srt_destino: str, inicio_corte: float, fim_corte: float) -> None:
    """
    Lê o SRT global, filtra apenas as legendas dentro do intervalo [inicio_corte, fim_corte],
    zera o relógio e divide textos longos em blocos curtos.

    Args:
        srt_original: Caminho absoluto do SRT global gerado na transcrição.
        srt_destino:  Caminho absoluto onde o novo SRT do corte será salvo.
        inicio_corte: Tempo de início do corte em segundos.
        fim_corte:    Tempo de fim do corte em segundos.
    """
    with open(srt_original, 'r', encoding='utf-8') as f:
        conteudo = f.read().strip()
    if not conteudo:
        return

    blocos = conteudo.split('\n\n')
    novos_blocos_srt = []
    contador = 1

    for bloco in blocos:
        linhas = bloco.split('\n')
        if len(linhas) < 3:
            continue

        tempos = linhas[1].split(' --> ')
        try:
            inicio_leg = _parse_srt_time(tempos[0])
            fim_leg = _parse_srt_time(tempos[1])
            texto_original = " ".join(linhas[2:])

            # Apenas legendas que acontecem dentro do intervalo deste corte
            if fim_leg <= inicio_corte or inicio_leg >= fim_corte:
                continue

            textos_otimizados = _otimizar_texto_legenda(texto_original)
            num_blocos = len(textos_otimizados)
            duracao_por_bloco = (fim_leg - inicio_leg) / num_blocos

            for i, texto_curto in enumerate(textos_otimizados):
                t_inicio = max(0.0, inicio_leg - inicio_corte) + (i * duracao_por_bloco)
                t_fim = t_inicio + duracao_por_bloco

                novos_blocos_srt.append(
                    f"{contador}\n"
                    f"{_format_srt_time(t_inicio)} --> {_format_srt_time(t_fim)}\n"
                    f"{texto_curto}\n"
                )
                contador += 1

        except Exception as e:
            print(f"[-] Erro ao processar bloco de legenda: {e}")
            continue

    with open(srt_destino, 'w', encoding='utf-8') as f:
        f.write('\n'.join(novos_blocos_srt) + '\n')


# ---------------------------------------------------------------------------
# Função principal de renderização
# ---------------------------------------------------------------------------

def renderizar_cortes(
    caminho_video: str,
    cortes: list,
    pasta_temp: str,
    pasta_output: str,
) -> list:
    """
    Renderiza cada corte: recorta o vídeo, converte para formato vertical (9:16)
    e queima as legendas sincronizadas.

    Args:
        caminho_video: Caminho absoluto do vídeo original.
        cortes:        Lista de tuplas (inicio, fim) em segundos.
        pasta_temp:    Caminho absoluto da pasta temporária (onde estão os SRTs).
        pasta_output:  Caminho absoluto da pasta de saída dos clipes finais.

    Returns:
        Lista de caminhos absolutos dos arquivos gerados.
    """
    print("\n[*] Preparando FFmpeg para edição com legendas sincronizadas...")

    if not cortes:
        print("[-] Nenhum corte para renderizar.")
        return []

    nome_base = os.path.basename(caminho_video).rsplit('.', 1)[0]
    caminho_srt_original = os.path.join(pasta_temp, f"{nome_base}.srt")

    if not os.path.exists(caminho_srt_original):
        print(f"[-] Erro crítico: SRT original não encontrado em: {caminho_srt_original}")
        return []

    arquivos_gerados = []

    for i, (inicio, fim) in enumerate(cortes, 1):
        arquivo_saida = os.path.join(pasta_output, f"{nome_base}_corte_{i:02d}.mp4")

        # Nome simples sem espaços para o SRT temporário — espaços no caminho
        # quebram o filtro 'subtitles' do FFmpeg no Windows.
        caminho_srt_corte = os.path.join(pasta_temp, f"srt_{i:02d}.srt")

        # Gera o SRT individual e sincronizado para este corte
        _gerar_srt_do_corte(caminho_srt_original, caminho_srt_corte, inicio, fim)

        # Converte para caminho curto 8.3 do Windows (sem espaços) e depois
        # escapa apenas o ':' da letra do drive — o FFmpeg exige esse formato.
        srt_short = _short_path(os.path.abspath(caminho_srt_corte))
        srt_ffmpeg = srt_short.replace('\\', '/').replace(':', '\\:')

        print(f"[*] Renderizando corte {i}/{len(cortes)} (de {inicio:.2f}s até {fim:.2f}s)...")

        try:
            estilo_legenda = (
                "FontName=Arial,Bold=1,FontSize=10,"
                "PrimaryColour=&H00FFFF,OutlineColour=&H40000000,"
                "BorderStyle=1,Outline=1,Shadow=1,"
                "Alignment=2,MarginV=50"
            )

            # Constrói o -vf manualmente para ter controle total do escape.
            # ffmpeg-python re-escaparia nosso \: para \\\: ao usar .filter().
            vf = f"crop=ih*9/16:ih,subtitles='{srt_ffmpeg}':force_style='{estilo_legenda}'"

            cmd = [
                'ffmpeg',
                '-ss', str(inicio), '-to', str(fim),
                '-i', caminho_video,
                '-vf', vf,
                '-vcodec', 'libx264', '-acodec', 'aac',
                '-loglevel', 'error',
                '-y', arquivo_saida,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode != 0:
                print(f"[-] Erro FFmpeg no corte {i}: {result.stderr or 'sem detalhes'}")
            else:
                print(f"[+] Corte {i} finalizado: {arquivo_saida}")
                arquivos_gerados.append(arquivo_saida)

        except Exception as e:
            print(f"[-] Erro inesperado no corte {i}: {e}")

    return arquivos_gerados
