import os
import re
import ctypes
import textwrap
import subprocess


# ---------------------------------------------------------------------------
# Helper Windows: caminho curto (8.3) sem espaços para o filtro subtitles
# ---------------------------------------------------------------------------

def _short_path(path: str) -> str:
    """
    No Windows converte para 8.3 para evitar espaços no filtro subtitles do FFmpeg.
    No macOS/Linux retorna o caminho sem modificação (barras e colons são tratados na linha 174).
    """
    if os.name == 'nt':
        buf = ctypes.create_unicode_buffer(32768)
        ctypes.windll.kernel32.GetShortPathNameW(path, buf, 32768)
        return buf.value if buf.value else path
    return path


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

    Quando MOLDURA_PATH estiver definido e o arquivo existir, a moldura PNG é
    usada como fundo decorativo: o vídeo é redimensionado para caber na área
    central, deixando MOLDURA_TOPO_PX pixels visíveis no topo e
    MOLDURA_RODAPE_PX no rodapé.

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

    # ----------------------------------------------------------------
    # Moldura — lê configuração do .env uma única vez por execução
    # ----------------------------------------------------------------
    moldura_path      = os.getenv("MOLDURA_PATH", "").strip()
    moldura_topo_px   = int(os.getenv("MOLDURA_TOPO_PX",   "0") or "0")
    moldura_rodape_px = int(os.getenv("MOLDURA_RODAPE_PX", "0") or "0")

    # Resolve caminho relativo a partir da raiz do projeto (onde fica o .env),
    # ou seja, um nível acima de src/. Caminhos absolutos não são alterados.
    if moldura_path and not os.path.isabs(moldura_path):
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        moldura_path  = os.path.join(_project_root, moldura_path)

    usar_moldura = bool(moldura_path and os.path.isfile(moldura_path))

    if usar_moldura:
        video_h = 1920 - moldura_topo_px - moldura_rodape_px
        print(f"[*] Moldura ativa: {os.path.basename(moldura_path)} "
              f"(topo={moldura_topo_px}px · rodapé={moldura_rodape_px}px · vídeo={video_h}px)")
    elif moldura_path:
        print(f"[!] MOLDURA_PATH definido mas arquivo não encontrado: {moldura_path} — renderizando sem moldura.")

    arquivos_gerados = []

    # Sanitiza o nome base removendo vírgulas e aspas — caracteres que quebram
    # o parsing de filtros e nomes de arquivo no FFmpeg.
    nome_seguro = re.sub(r"[,'\"]", '', nome_base).strip()

    for i, (inicio, fim) in enumerate(cortes, 1):
        arquivo_saida = os.path.join(pasta_output, f"{nome_seguro}_corte_{i:02d}.mp4")

        # Nome simples sem espaços para o SRT temporário — espaços no caminho
        # quebram o filtro 'subtitles' do FFmpeg no Windows.
        caminho_srt_corte = os.path.join(pasta_temp, f"srt_{i:02d}.srt")

        # Gera o SRT individual e sincronizado para este corte
        _gerar_srt_do_corte(caminho_srt_original, caminho_srt_corte, inicio, fim)

        srt_short = _short_path(os.path.abspath(caminho_srt_corte))

        print(f"[*] Renderizando corte {i}/{len(cortes)} (de {inicio:.2f}s até {fim:.2f}s)...")

        try:
            estilo_legenda = (
                "FontName=Arial,Bold=1,FontSize=10,"
                "PrimaryColour=&H00FFFF,OutlineColour=&H40000000,"
                "BorderStyle=1,Outline=1,Shadow=1,"
                "Alignment=2,MarginV=70"
            )

            if usar_moldura:
                # ------------------------------------------------------------
                # Modo com moldura: 2 inputs — vídeo + PNG de fundo.
                # O vídeo é redimensionado para 1080×video_h, as legendas são
                # queimadas nessa área e o resultado é sobreposto à moldura.
                # Filtro: [1]scale→[bg]; [0]crop+scale+subtitles→[vid]; overlay→[out]
                # ------------------------------------------------------------
                if os.name == 'nt':
                    srt_ffmpeg = srt_short.replace('\\', '/').replace(':', '\\:')
                    sub_filter = f"subtitles='{srt_ffmpeg}':force_style='{estilo_legenda}'"
                else:
                    # macOS/Linux: escapar ',' de force_style e ':' do caminho SRT.
                    srt_ffmpeg = srt_short.replace(':', '\\:').replace(' ', '\\ ')
                    estilo_escapado = estilo_legenda.replace(',', '\\,')
                    sub_filter = f"subtitles=filename={srt_ffmpeg}:force_style={estilo_escapado}"

                filter_complex = (
                    f"[1]scale=1080:1920[bg];"
                    f"[0]crop=ih*9/16:ih,scale=1080:{video_h},{sub_filter}[vid];"
                    f"[bg][vid]overlay=(W-w)/2:{moldura_topo_px}[out]"
                )

                cmd = [
                    'ffmpeg',
                    '-ss', str(inicio), '-to', str(fim),
                    '-i', caminho_video,
                    '-i', moldura_path,
                    '-filter_complex', filter_complex,
                    '-map', '[out]',
                    '-map', '0:a',
                    '-vcodec', 'libx264', '-crf', '18', '-preset', 'medium',
                    '-acodec', 'aac', '-b:a', '192k',
                    '-loglevel', 'error',
                    '-y', arquivo_saida,
                ]

            else:
                # ------------------------------------------------------------
                # Modo padrão: 1 input — vídeo direto em 9:16 1080×1920.
                # ------------------------------------------------------------
                if os.name == 'nt':
                    # Windows: caminho 8.3 sem espaços; escapa '\' e ':' do drive.
                    srt_ffmpeg = srt_short.replace('\\', '/').replace(':', '\\:')
                    vf = f"crop=ih*9/16:ih,scale=1080:1920,subtitles='{srt_ffmpeg}':force_style='{estilo_legenda}'"
                else:
                    # macOS/Linux: o parser lavfi divide o filterchain por ',' ANTES de
                    # processar aspas — os ',' dentro de force_style quebram o parsing.
                    # Solução: escapar cada ',' como '\,' (literal para o filterchain parser)
                    # e usar 'filename=' explícito para evitar ambiguidade no positional arg.
                    srt_ffmpeg = srt_short.replace(':', '\\:').replace(' ', '\\ ')
                    estilo_escapado = estilo_legenda.replace(',', '\\,')
                    vf = f"crop=ih*9/16:ih,scale=1080:1920,subtitles=filename={srt_ffmpeg}:force_style={estilo_escapado}"

                cmd = [
                    'ffmpeg',
                    '-ss', str(inicio), '-to', str(fim),
                    '-i', caminho_video,
                    '-vf', vf,
                    '-vcodec', 'libx264', '-crf', '18', '-preset', 'medium',
                    '-acodec', 'aac', '-b:a', '192k',
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
