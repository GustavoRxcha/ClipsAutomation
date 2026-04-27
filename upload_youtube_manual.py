"""
Script avulso para upload manual de clipes ao YouTube Shorts.
Usa os arquivos já existentes em output_tiktok/ (ou output/).

Uso:
    python upload_youtube_manual.py
    python upload_youtube_manual.py --pasta output
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

bin_dir = os.path.join(BASE_DIR, "bin")
if os.path.isdir(bin_dir):
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from src.uploader_youtube import fazer_upload_shorts

pasta = "output_tiktok"
if "--pasta" in sys.argv:
    idx = sys.argv.index("--pasta")
    if idx + 1 < len(sys.argv):
        pasta = sys.argv[idx + 1]

pasta_path = os.path.join(BASE_DIR, pasta)

if not os.path.isdir(pasta_path):
    print(f"[-] Pasta não encontrada: {pasta_path}")
    sys.exit(1)

arquivos = sorted(
    [os.path.join(pasta_path, f) for f in os.listdir(pasta_path) if f.endswith(".mp4")],
)

if not arquivos:
    print(f"[-] Nenhum arquivo .mp4 encontrado em: {pasta_path}")
    sys.exit(1)

print(f"[*] {len(arquivos)} clipe(s) encontrado(s) em '{pasta}':")
for f in arquivos:
    print(f"    {os.path.basename(f)}")
print()

titulo_base = os.path.splitext(os.path.basename(arquivos[0]))[0]
titulo_base = titulo_base.rsplit("_corte_", 1)[0]

urls = fazer_upload_shorts(arquivos, titulo_base)

print()
if urls:
    print(f"[+] {len(urls)} vídeo(s) enviado(s):")
    for url in urls:
        print(f"    {url}")
else:
    print("[-] Nenhum vídeo foi enviado.")
