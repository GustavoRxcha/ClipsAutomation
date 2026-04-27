"""
src/tiktok_auth.py — Autenticação TikTok via sessionid.

Como obter o sessionid:
    1. Acesse tiktok.com no seu browser e faça login
    2. F12 → Application → Cookies → tiktok.com → copie o valor de "sessionid"
    3. Cole em TIKTOK_SESSION_ID no .env

    Ou execute: python tiktok_setup.py
"""


def garantir_sessao(session_id: str) -> bool:
    """
    Verifica se há um sessionid configurado.

    Args:
        session_id: valor de TIKTOK_SESSION_ID lido do .env.

    Returns:
        True  → sessionid disponível, pode prosseguir com o upload.
        False → sessionid ausente, upload deste ciclo é abortado.
    """
    if session_id:
        return True

    print("[-] TIKTOK_SESSION_ID não configurado no .env.")
    print()
    print("    Como obter:")
    print("      1. Acesse tiktok.com no seu browser e faça login")
    print("      2. F12 → Application → Cookies → tiktok.com")
    print("      3. Copie o valor do cookie 'sessionid'")
    print("      4. Cole no .env: TIKTOK_SESSION_ID=valor_aqui")
    print()
    print("    Ou execute: python tiktok_setup.py")
    return False
