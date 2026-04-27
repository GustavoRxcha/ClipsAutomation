# ClipsAutomation

Pipeline autônomo que transforma vídeos longos do YouTube em Shorts e posts no TikTok — sem interação manual.

---

## Como funciona

```
VPS (diário, 07:00)
  YouTube → download → transcrição → cortes → renderização → YouTube Shorts → output_tiktok/

Mac (a cada 3 horas, launchd)
  output_tiktok/ na VPS → SCP download → upload TikTok → deleta da VPS
```

---

## Pré-requisitos

| O que | Onde obter |
|---|---|
| Conta Google Cloud com YouTube Data API v3 ativada | console.cloud.google.com |
| `client_secrets.json` (OAuth2 Desktop) | Google Cloud Console → APIs & Services → Credentials |
| Conta TikTok com cookie `sessionid` | tiktok.com → F12 → Application → Cookies |
| VPS Ubuntu 22.04 com acesso SSH root | Qualquer provedor |
| FFmpeg instalado no Mac | `brew install ffmpeg` |
| Chave SSH configurada para a VPS | `~/.ssh/id_rsa` ou similar |

---

## Parte 1 — Mac (configuração local)

### 1.1 Clonar e configurar o projeto

```bash
git clone <url-do-repositorio> ~/Projetos/ClipsAutomation
cd ~/Projetos/ClipsAutomation

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 1.2 Criar o arquivo `.env`

```bash
cp .env.example .env
```

Edite `.env` e preencha:

```env
# YouTube
YOUTUBE_API_KEY=AIza...
YOUTUBE_CHANNEL_ID=@handle_ou_UCxxxxx
YOUTUBE_PRIVACY=public

# TikTok
TIKTOK_SESSION_ID=<valor do cookie sessionid>

# VPS
VPS_HOST=<IP da VPS>
VPS_USER=root
VPS_KEY_PATH=/Users/seu_usuario/.ssh/id_rsa
VPS_REMOTE_DIR=/root/ClipsAutomation/output_tiktok
```

### 1.3 Gerar o token do YouTube (OAuth2)

Coloque o `client_secrets.json` na raiz do projeto e execute:

```bash
python gerar_token_youtube.py
```

O browser vai abrir para autorização. Após confirmar, o arquivo `token.json` é salvo automaticamente e o terminal exibe o comando `scp` para copiar para a VPS — guarde esse comando para o Passo 2.4.

### 1.4 Ativar o agendador TikTok no Mac (launchd)

Edite o arquivo `com.clipsautomation.tiktok.plist` e confirme que os caminhos estão corretos para o seu usuário:

```xml
<string>/Users/SEU_USUARIO/Projetos/ClipsAutomation/venv/bin/python</string>
<string>/Users/SEU_USUARIO/Projetos/ClipsAutomation/tiktok_runner.py</string>
...
<string>/Users/SEU_USUARIO/Projetos/ClipsAutomation</string>
```

Depois carregue o agente:

```bash
launchctl bootstrap gui/$(id -u) ~/Projetos/ClipsAutomation/com.clipsautomation.tiktok.plist
```

Verifique se foi carregado:

```bash
launchctl print gui/$(id -u)/com.clipsautomation.tiktok
```

Procure por `state = waiting` ou `state = not running` — ambos indicam que está agendado.

---

## Parte 2 — VPS (Ubuntu 22.04)

### 2.1 Clonar o repositório

```bash
ssh root@<IP_DA_VPS>
git clone <url-do-repositorio> /root/ClipsAutomation
cd /root/ClipsAutomation
```

### 2.2 Rodar o setup

```bash
bash setup_vps.sh
```

Isso instala: Python, FFmpeg, venv, dependências Python e cria as pastas necessárias.

### 2.3 Criar o arquivo `.env` na VPS

```bash
cp .env.example .env
nano .env
```

Preencha as mesmas variáveis do Mac, **exceto** as variáveis VPS (não são necessárias na VPS):

```env
WHISPER_MODEL=tiny        # obrigatório em VPS com 512 MB RAM
YOUTUBE_API_KEY=AIza...
YOUTUBE_CHANNEL_ID=@handle_ou_UCxxxxx
YOUTUBE_PRIVACY=public
TIKTOK_SESSION_ID=<mesmo valor do Mac>
```

### 2.4 Copiar as credenciais do Google

No **Mac**, execute o comando que o `gerar_token_youtube.py` imprimiu:

```bash
scp ~/Projetos/ClipsAutomation/client_secrets.json root@<IP_DA_VPS>:/root/ClipsAutomation/
scp ~/Projetos/ClipsAutomation/token.json root@<IP_DA_VPS>:/root/ClipsAutomation/
```

### 2.5 Corrigir o fuso horário (se necessário)

```bash
timedatectl set-timezone America/Sao_Paulo
```

### 2.6 Instalar o cron

```bash
bash setup_cron.sh
```

Confirma:

```bash
crontab -l
# deve exibir: 0 7 * * * .../python3 .../main.py >> .../logs/main.log 2>&1
```

### 2.7 (Opcional) Configurar rotação de logs

```bash
sudo bash setup_logrotate.sh
```

---

## Verificação final

### Testar o pipeline da VPS manualmente

```bash
cd /root/ClipsAutomation
venv/bin/python main.py
```

Acompanhe em tempo real:

```bash
tail -f /root/ClipsAutomation/logs/main.log
```

### Testar o uploader TikTok no Mac manualmente

```bash
cd ~/Projetos/ClipsAutomation
source venv/bin/activate
python tiktok_runner.py
```

### Verificar logs do launchd no Mac

```bash
tail -f ~/Projetos/ClipsAutomation/logs/tiktok.log
```

---

## Manutenção

### Renovar o sessionid do TikTok (~a cada 60-90 dias)

1. Acesse tiktok.com no browser e faça login
2. F12 → Application → Cookies → `tiktok.com` → copie o valor de `sessionid`
3. Atualize no `.env` do Mac e da VPS:
   ```env
   TIKTOK_SESSION_ID=novo_valor
   ```

### Renovar o token do YouTube (expira raramente, mas pode ocorrer)

No Mac:

```bash
cd ~/Projetos/ClipsAutomation
python gerar_token_youtube.py
scp token.json root@<IP_DA_VPS>:/root/ClipsAutomation/token.json
```

### Atualizar o código

```bash
# Mac
cd ~/Projetos/ClipsAutomation && git pull

# VPS
cd /root/ClipsAutomation && git pull
```

---

## Trocar de VPS ou Mac

### Trocar a VPS

1. Na nova VPS: repita os Passos 2.1 a 2.7
2. No Mac: atualize `VPS_HOST` no `.env`
3. Na VPS antiga: transfira os arquivos de `output_tiktok/` que ainda não foram postados:
   ```bash
   scp root@<VPS_ANTIGA>:/root/ClipsAutomation/output_tiktok/*.mp4 \
       root@<VPS_NOVA>:/root/ClipsAutomation/output_tiktok/
   ```

### Trocar o Mac

1. No novo Mac: repita o Passo 1 inteiro
2. O `token.json` já está na VPS — não precisa regerar
3. Transfira o `.env` do Mac antigo (tem as credenciais TikTok e VPS)
4. Recarregue o launchd no novo Mac (Passo 1.4)

---

## Estrutura do projeto

```
ClipsAutomation/
├── main.py                             # Pipeline principal (roda na VPS)
├── tiktok_runner.py                    # Uploader TikTok (roda no Mac)
├── gerar_token_youtube.py              # Geração de token OAuth (Mac, uso único)
├── com.clipsautomation.tiktok.plist    # Agendador launchd do Mac
├── setup_vps.sh                        # Bootstrap da VPS
├── setup_cron.sh                       # Instalação do cron na VPS
├── setup_logrotate.sh                  # Rotação de logs na VPS
├── requirements.txt
├── .env.example
└── src/
    ├── finder.py           # Busca o vídeo mais viral do canal
    ├── downloader.py       # Download via yt-dlp
    ├── transcriber.py      # Transcrição via faster-whisper
    ├── editor.py           # Segmentação em cortes
    ├── render.py           # Renderização 9:16 com FFmpeg
    ├── uploader_youtube.py # Upload para YouTube Shorts
    ├── uploader_tiktok.py  # Upload para TikTok
    ├── vps_sync.py         # SSH/SCP helpers para sync Mac ↔ VPS
    └── tiktok_auth.py      # Validação do sessionid TikTok
```
