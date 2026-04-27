import os
import subprocess


def _ssh_args(host: str, user: str, key_path: str) -> list:
    args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
    if key_path:
        args += ["-i", key_path]
    args.append(f"{user}@{host}")
    return args


def buscar_proximo_arquivo(host: str, user: str, key_path: str, remote_dir: str) -> str | None:
    """Retorna o caminho remoto do arquivo .mp4 mais antigo na VPS, ou None se vazia."""
    cmd = _ssh_args(host, user, key_path) + [
        f"ls -rt {remote_dir}/*.mp4 2>/dev/null | head -1"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    caminho = result.stdout.strip()
    return caminho if caminho else None


def baixar_arquivo(host: str, user: str, key_path: str, remote_path: str, local_path: str) -> bool:
    """Baixa arquivo da VPS para o Mac via SCP. Retorna True em sucesso."""
    scp_args = ["scp", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes"]
    if key_path:
        scp_args += ["-i", key_path]
    scp_args += [f"{user}@{host}:{remote_path}", local_path]

    result = subprocess.run(scp_args, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"[-] Erro no SCP: {result.stderr.strip()}")
        return False
    return True


def deletar_arquivo(host: str, user: str, key_path: str, remote_path: str) -> bool:
    """Deleta arquivo na VPS via SSH. Retorna True em sucesso."""
    cmd = _ssh_args(host, user, key_path) + [f"rm -f '{remote_path}'"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"[-] Erro ao deletar na VPS: {result.stderr.strip()}")
        return False
    return True
