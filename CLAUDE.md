# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

ClipsAutomation is a fully autonomous Python pipeline that converts long YouTube videos into YouTube Shorts. It picks the most viral unwatched video from a configured channel, downloads it, transcribes it, segments the transcript into clips, renders each clip at 9:16 with burned-in subtitles, uploads them to YouTube Shorts (with staggered scheduling), queues them for TikTok, and cleans up — all without any user interaction.

The pipeline runs in two separate environments:
- **VPS (Ubuntu):** runs `main.py` daily via cron — handles everything from download through YouTube upload, then saves clips to `output_tiktok/`.
- **Mac (local):** runs `tiktok_runner.py` every 3 hours via launchd — downloads clips from VPS via SCP and uploads to TikTok using a residential IP (bypasses bot detection).

## Setup & Run

```bash
pip install -r requirements.txt
cp .env.example .env   # configure env vars (see table below)
python main.py         # runs the full autonomous pipeline — no prompts
```

**Required external dependency:** FFmpeg must be installed and available on PATH.

**Google credentials:** Place `client_secrets.json` (OAuth2 from Google Cloud Console) in the project root. Generate `token.json` once on your local Mac with `python gerar_token_youtube.py`, then `scp` it to the VPS.

**TikTok credentials:** Set `TIKTOK_SESSION_ID` in `.env` with the value of the `sessionid` cookie from tiktok.com (F12 → Application → Cookies). The sessionid lasts 60-90 days; renew it by repeating the same step.

## VPS Setup

```bash
bash setup_vps.sh     # installs system deps, Python venv, creates runtime dirs
# then copy: .env, client_secrets.json, token.json
bash setup_cron.sh    # installs cron job (main.py daily at 07:00)
```

## Mac launchd Setup (TikTok uploader)

```bash
# Load the launchd agent (runs tiktok_runner.py every 3 hours)
launchctl bootstrap gui/$(id -u) /path/to/com.clipsautomation.tiktok.plist

# Check status
launchctl print gui/$(id -u)/com.clipsautomation.tiktok

# Unload
launchctl bootout gui/$(id -u)/com.clipsautomation.tiktok
```

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | faster-whisper model size (tiny/base/small/medium/large) — use `tiny` on 512 MB VPS |
| `DURACAO_ALVO_SEGUNDOS` | `90` | Target clip duration in seconds |
| `DURACAO_MINIMA_SEGUNDOS` | `45` | Minimum clip duration — shorter clips are discarded |
| `YOUTUBE_API_KEY` | *(empty)* | Public API key for YouTube Data API v3 — **required** for channel lookup |
| `YOUTUBE_CHANNEL_ID` | *(empty)* | Channel ID (`UC…`), `@handle`, or full URL — **required**; pipeline aborts if blank |
| `YOUTUBE_CANAL_MAX_VIDEOS` | `20` | How many recent channel videos to evaluate when picking the most viral |
| `YOUTUBE_PRIVACY` | `private` | Upload visibility (public/unlisted/private) |
| `YOUTUBE_COOKIES_FILE` | *(empty)* | Absolute path to a Netscape-format YouTube cookies file — required when VPS IP is flagged as bot |
| `TIKTOK_SESSION_ID` | *(empty)* | TikTok sessionid cookie — required for TikTok uploads; lasts ~60-90 days |
| `VPS_HOST` | *(empty)* | VPS IP or hostname — enables VPS sync mode in `tiktok_runner.py` |
| `VPS_USER` | `root` | SSH user for VPS connection |
| `VPS_KEY_PATH` | *(empty)* | Absolute path to SSH private key on Mac |
| `VPS_REMOTE_DIR` | `/root/ClipsAutomation/output_tiktok` | Remote directory where clips are queued on the VPS |
| `MOLDURA_PATH` | *(empty)* | Absolute path to a 1080×1920 PNG frame overlay — leave empty to disable |
| `MOLDURA_TOPO_PX` | `200` | Pixels of top frame border kept visible (e.g. channel name) |
| `MOLDURA_RODAPE_PX` | `150` | Pixels of bottom frame border kept visible (e.g. CTA) |

## Pipeline Architecture

```
YOUTUBE_CHANNEL_ID (.env)
  → src/finder.py           → most viral unwatched video URL  [Phase 0 — auto]
  → src/downloader.py       → video file (assets/)            [Phase 1]
  → src/transcriber.py      → transcript .txt + .srt (temp/)  [Phase 2]
  → src/editor.py           → list of (start_sec, end_sec)    [Phase 3]
  → src/render.py           → MP4 clips (output/)             [Phase 4]
  → src/uploader_youtube.py → YouTube Shorts URLs             [Phase 5 — skips clips > 60s]
  → output_tiktok/          → queued for TikTok upload        [Phase 6]
  → cleanup assets/ temp/ output/                             [Phase 7]

  ↓ (Mac launchd, every 3 hours)
  tiktok_runner.py + src/vps_sync.py → SCP download from VPS → TikTok upload → SSH delete
```

**Segmentation logic (`src/editor.py`):** Parses `[start -> end] text` lines with regex, groups segments sequentially until reaching `DURACAO_ALVO_SEGUNDOS`, drops final group if under `DURACAO_MINIMA_SEGUNDOS`.

**Rendering (`src/render.py`):** Builds FFmpeg filter graphs manually. Default crop formula: `crop=ih*9/16:ih,scale=1080:1920`. When `MOLDURA_PATH` is set, uses `-filter_complex` with 2 inputs: the PNG is scaled to 1080×1920 as background (`[bg]`), the video is scaled to `1080×(1920-MOLDURA_TOPO_PX-MOLDURA_RODAPE_PX)` with subtitles burned in (`[vid]`), then overlaid centered at `y=MOLDURA_TOPO_PX`. Subtitles styled as Arial Bold, yellow, black outline. Output encoded with `-crf 18` for high quality.

**Upload YouTube (`src/uploader_youtube.py`):** First clip is published immediately as public; subsequent clips are scheduled as private with 3-hour intervals. OAuth2 token cached in `token.json`. Generate `token.json` locally with `gerar_token_youtube.py`, then scp to VPS.

**Upload TikTok (`src/uploader_tiktok.py` + `tiktok_runner.py`):** One clip per run via FIFO queue in `output_tiktok/`. Authentication via `TIKTOK_SESSION_ID` in `.env`. When `VPS_HOST` is set, `tiktok_runner.py` downloads the oldest clip from the VPS via SCP before uploading, then deletes it from VPS on success.

**VPS sync (`src/vps_sync.py`):** SSH/SCP helpers — `buscar_proximo_arquivo`, `baixar_arquivo`, `deletar_arquivo`.

## Key Design Decisions

- **yt-dlp with `player_client: [ios, web]`** — replaces pytubefix; actively maintained against YouTube bot detection; VPS IPs may still be blocked without a cookies file (`YOUTUBE_COOKIES_FILE`).
- **faster-whisper on CPU with int8 quantization** — balances speed and accuracy without GPU dependency. Use `WHISPER_MODEL=tiny` on VPS with ≤ 512 MB RAM.
- **Staggered upload schedule** — 3-hour gaps between clips to optimize YouTube algorithm distribution.
- **TikTok uploads run on Mac, not VPS** — VPS datacenter IPs are blocked by TikTok bot detection; Mac residential IP passes. The VPS only queues clips in `output_tiktok/`; Mac's launchd picks them up via SCP.
- The codebase and all user-facing strings are in Brazilian Portuguese.

## Utility Scripts

| Script | Where to run | Purpose |
|---|---|---|
| `gerar_token_youtube.py` | Mac | One-time OAuth2 token generation — opens browser, saves `token.json`, prints `scp` command |
| `setup_vps.sh` | VPS (root) | Full VPS bootstrap: system deps, Python venv, runtime dirs |
| `setup_cron.sh` | VPS | Installs cron job for `main.py` (daily at 07:00) |
| `setup_logrotate.sh` | VPS (root) | Configures log rotation (daily, 7-day history, gzip) |
| `com.clipsautomation.tiktok.plist` | Mac | launchd agent — runs `tiktok_runner.py` every 3 hours |
