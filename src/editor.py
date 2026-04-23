import re


def analisar_corte(caminho_txt: str, duracao_alvo: float = 90.0, duracao_minima: float = 45.0) -> list:
    """
    Lê o arquivo de transcrição (.txt) e define os timestamps dos cortes.

    A lógica agrupa frases sequencialmente até atingir a `duracao_alvo`.
    Cortes menores que `duracao_minima` são descartados (evita sobras curtinhas no final).

    Args:
        caminho_txt: Caminho absoluto do arquivo de transcrição .txt.
        duracao_alvo: Duração-alvo de cada corte em segundos (padrão: 90s).
        duracao_minima: Duração mínima para um corte ser aceito em segundos (padrão: 45s).

    Returns:
        Lista de tuplas (inicio, fim) em segundos, ou lista vazia se falhar.
    """
    print(f"\n[*] Iniciando análise de corte do arquivo: {caminho_txt}")

    # Captura linhas no formato: [20.08s -> 28.24s] Texto...
    padrao = r'\[([\d\.]+)s\s*->\s*([\d\.]+)s\]'

    linhas_tempo = []
    try:
        with open(caminho_txt, 'r', encoding='utf-8') as f:
            for linha in f:
                match = re.search(padrao, linha)
                if match:
                    inicio = float(match.group(1))
                    fim = float(match.group(2))
                    linhas_tempo.append((inicio, fim))
    except Exception as e:
        print(f"[-] Erro ao ler o arquivo de transcrição: {e}")
        return []

    if not linhas_tempo:
        print("[-] Falha: Não foi possível extrair timestamps do arquivo de transcrição.")
        return []

    # Agrupamento sequencial por duração-alvo
    cortes = []
    inicio_corte = linhas_tempo[0][0]

    for i, (_, fim_atual) in enumerate(linhas_tempo):
        duracao_atual = fim_atual - inicio_corte

        if duracao_atual >= duracao_alvo or i == len(linhas_tempo) - 1:
            cortes.append((inicio_corte, fim_atual))
            if i + 1 < len(linhas_tempo):
                inicio_corte = linhas_tempo[i + 1][0]

    # Filtro de sanidade: descarta cortes muito curtos (geralmente o último fragmento)
    cortes_filtrados = [c for c in cortes if (c[1] - c[0]) >= duracao_minima]

    if cortes_filtrados:
        print(f"\n[+] Sucesso! O vídeo foi fatiado em {len(cortes_filtrados)} cortes:")
        for i, (ini, fim) in enumerate(cortes_filtrados, 1):
            duracao = fim - ini
            print(f"    Corte {i}: de {ini:.2f}s até {fim:.2f}s (Duração: {duracao:.2f}s)")
        return cortes_filtrados
    else:
        print(f"[-] Falha: Nenhum corte passou do filtro de duração mínima ({duracao_minima}s).")
        return []
