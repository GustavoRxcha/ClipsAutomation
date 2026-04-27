"""
src/finder.py — Busca automática de vídeos no YouTube via Data API v3.

Usa apenas API Key pública (sem OAuth). Configure YOUTUBE_API_KEY no .env.
Reutiliza google-api-python-client já instalada no projeto.
"""

import json
import os
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Caminho do histórico de vídeos já processados (raiz do projeto)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HISTORICO_PATH = os.path.join(_BASE_DIR, "historico_videos.json")


# ---------------------------------------------------------------------------
# Utilitários internos
# ---------------------------------------------------------------------------

def _iso8601_para_segundos(duracao: str) -> int:
    """Converte duração ISO 8601 (PT1H2M3S) retornada pela API em segundos."""
    horas   = int(re.search(r"(\d+)H", duracao).group(1)) if "H" in duracao else 0
    minutos = int(re.search(r"(\d+)M", duracao).group(1)) if "M" in duracao else 0
    segundos = int(re.search(r"(\d+)S", duracao).group(1)) if "S" in duracao else 0
    return horas * 3600 + minutos * 60 + segundos


def _build_client():
    """Cria cliente autenticado via API Key. Retorna None se a chave não estiver configurada."""
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[-] YOUTUBE_API_KEY não configurada no .env.")
        print("[-] Adicione a chave em .env para usar a busca automática.")
        return None
    try:
        return build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        print(f"[-] Falha ao inicializar cliente YouTube: {e}")
        return None


def extrair_video_id(url: str) -> str | None:
    """Extrai o ID de 11 caracteres de uma URL do YouTube."""
    m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Histórico de vídeos processados
# ---------------------------------------------------------------------------

def _carregar_historico() -> set[str]:
    """Lê historico_videos.json e retorna um set de IDs já processados."""
    if not os.path.exists(_HISTORICO_PATH):
        return set()
    try:
        with open(_HISTORICO_PATH, encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def _salvar_historico(historico: set[str]) -> None:
    """Persiste o set de IDs em historico_videos.json."""
    with open(_HISTORICO_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(historico), f, indent=2, ensure_ascii=False)


def registrar_video_processado(video_id: str) -> None:
    """
    Adiciona um ID ao histórico para que nunca seja selecionado novamente
    pela busca automática de canal.
    """
    historico = _carregar_historico()
    historico.add(video_id)
    _salvar_historico(historico)
    print(f"[+] Vídeo {video_id} registrado no histórico.")


# ---------------------------------------------------------------------------
# Busca por query (opção 1)
# ---------------------------------------------------------------------------

def buscar_videos(
    query: str,
    regiao: str = "BR",
    idioma: str = "pt",
    duracao_maxima_segundos: int = 600,
    max_resultados: int = 10,
) -> list[dict]:
    """
    Busca vídeos no YouTube em duas etapas e retorna os mais vistos dentro do limite.

    Etapa 1 — search.list:
        order=viewCount, regionCode, relevanceLanguage, videoDuration=medium,
        maxResults=50 (pool inicial para filtro posterior).

    Etapa 2 — videos.list:
        Busca contentDetails + statistics nos IDs retornados.
        Filtra localmente por duracao_maxima_segundos.
        Retorna os max_resultados mais vistos ordenados por views (desc).

    Returns:
        Lista de dicts: [{"url", "titulo", "duracao_segundos", "visualizacoes"}]
    """
    youtube = _build_client()
    if youtube is None:
        return []

    # Etapa 1 — search.list
    print(f"[*] Buscando vídeos para: '{query}' (região={regiao}, idioma={idioma}) ...")
    try:
        search_resp = youtube.search().list(
            part="id,snippet",
            q=query,
            type="video",
            order="viewCount",
            regionCode=regiao,
            relevanceLanguage=idioma,
            videoDuration="medium",
            maxResults=50,
        ).execute()
    except HttpError as e:
        print(f"[-] Erro na busca (search.list): {e}")
        return []

    items = search_resp.get("items", [])
    if not items:
        print("[-] Nenhum vídeo encontrado para a busca.")
        return []

    ids = [item["id"]["videoId"] for item in items]

    # Etapa 2 — videos.list
    try:
        videos_resp = youtube.videos().list(
            part="contentDetails,statistics,snippet",
            id=",".join(ids),
            maxResults=50,
        ).execute()
    except HttpError as e:
        print(f"[-] Erro ao buscar detalhes (videos.list): {e}")
        return []

    resultados = []
    for video in videos_resp.get("items", []):
        duracao_seg = _iso8601_para_segundos(video["contentDetails"].get("duration", "PT0S"))
        if duracao_seg > duracao_maxima_segundos:
            continue
        resultados.append({
            "url": f"https://www.youtube.com/watch?v={video['id']}",
            "titulo": video["snippet"]["title"],
            "duracao_segundos": duracao_seg,
            "visualizacoes": int(video["statistics"].get("viewCount", 0)),
        })

    if not resultados:
        print(f"[-] Nenhum vídeo encontrado com duração ≤ {duracao_maxima_segundos}s.")
        return []

    resultados.sort(key=lambda v: v["visualizacoes"], reverse=True)
    print(f"[+] {len(resultados[:max_resultados])} vídeo(s) encontrado(s).")
    return resultados[:max_resultados]


# ---------------------------------------------------------------------------
# Busca por canal (opção 3)
# ---------------------------------------------------------------------------

def _resolver_uploads_playlist(youtube, canal: str) -> str | None:
    """
    Resolve qualquer formato de canal para o ID da playlist de uploads (UU...).

    Aceita:
      - ID direto:          UCxxxxxxxxxxxxxxxxxxxxxx
      - Handle com @:       @nomecanal
      - URL channel:        https://youtube.com/channel/UC...
      - URL handle:         https://youtube.com/@nomecanal
    """
    canal = canal.strip().rstrip("/")

    # URL com channel ID
    m = re.search(r"youtube\.com/channel/(UC[A-Za-z0-9_-]+)", canal)
    if m:
        return "UU" + m.group(1)[2:]

    # URL com @handle → extrai o handle
    m = re.search(r"youtube\.com/@([A-Za-z0-9_.-]+)", canal)
    if m:
        canal = "@" + m.group(1)

    # Channel ID direto (UC...)
    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", canal):
        return "UU" + canal[2:]

    # Handle (@nome ou nome) → resolve via API
    handle = canal.lstrip("@")
    try:
        resp = youtube.channels().list(
            part="id",
            forHandle=handle,
        ).execute()
        items = resp.get("items", [])
        if items:
            return "UU" + items[0]["id"][2:]
    except HttpError as e:
        print(f"[-] Erro ao resolver canal '{canal}': {e}")

    return None


def buscar_video_canal(canal: str, max_videos: int = 20) -> dict | None:
    """
    Seleciona o vídeo mais viral entre os últimos `max_videos` de um canal,
    ignorando qualquer vídeo já presente em historico_videos.json.

    Args:
        canal:      Channel ID (UC...), @handle ou URL do canal.
        max_videos: Quantos vídeos recentes considerar (padrão 20).

    Returns:
        Dict {"url", "titulo", "duracao_segundos", "visualizacoes"} do mais viral,
        ou None se não houver candidatos disponíveis.
    """
    youtube = _build_client()
    if youtube is None:
        return None

    # Resolve canal → playlist de uploads
    playlist_id = _resolver_uploads_playlist(youtube, canal)
    if not playlist_id:
        print(f"[-] Canal não encontrado ou inválido: {canal}")
        return None

    historico = _carregar_historico()

    # Coleta IDs dos últimos max_videos vídeos ainda não processados
    print(f"[*] Buscando últimos {max_videos} vídeo(s) do canal ...")
    ids_candidatos: list[str] = []
    page_token = None

    while len(ids_candidatos) < max_videos:
        try:
            resp = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=min(50, max_videos),
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            print(f"[-] Erro ao buscar playlist do canal: {e}")
            return None

        for item in resp.get("items", []):
            vid_id = item["contentDetails"]["videoId"]
            if vid_id not in historico:
                ids_candidatos.append(vid_id)

        page_token = resp.get("nextPageToken")
        if not page_token or len(ids_candidatos) >= max_videos:
            break

    if not ids_candidatos:
        print("[*] Todos os vídeos recentes do canal já foram processados.")
        return None

    # Busca detalhes e estatísticas dos candidatos
    try:
        videos_resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(ids_candidatos[:50]),
        ).execute()
    except HttpError as e:
        print(f"[-] Erro ao buscar detalhes dos vídeos: {e}")
        return None

    candidatos = []
    for video in videos_resp.get("items", []):
        candidatos.append({
            "url": f"https://www.youtube.com/watch?v={video['id']}",
            "titulo": video["snippet"]["title"],
            "duracao_segundos": _iso8601_para_segundos(
                video["contentDetails"].get("duration", "PT0S")
            ),
            "visualizacoes": int(video["statistics"].get("viewCount", 0)),
        })

    if not candidatos:
        print("[-] Nenhum vídeo disponível no canal.")
        return None

    # Seleciona o mais viral
    melhor = max(candidatos, key=lambda v: v["visualizacoes"])
    views_fmt = f"{melhor['visualizacoes']:,}".replace(",", ".")
    minutos, seg = divmod(melhor["duracao_segundos"], 60)
    print(f"[+] Vídeo selecionado: {melhor['titulo']}")
    print(f"    {minutos}m{seg:02d}s  •  {views_fmt} visualizações")
    return melhor
