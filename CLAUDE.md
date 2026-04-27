# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

ClipsAutomation is a fully autonomous Python pipeline that converts long YouTube videos into YouTube Shorts. It picks the most viral unwatched video from a configured channel, downloads it, transcribes it, segments the transcript into clips, renders each clip at 9:16 with burned-in subtitles, uploads them to YouTube (with staggered scheduling), queues them for TikTok, and cleans up — all without any user interaction.

## Setup & Run

```bash
pip install -r requirements.txt
cp .env.example .env   # configure YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, TIKTOK_SESSION_ID, etc.
python main.py         # runs the full autonomous pipeline — no prompts
```

**Required external dependency:** FFmpeg must be installed and available on PATH.

**Google credentials:** Place `client_secrets.json` (OAuth2 from Google Cloud Console) in the project root before using the YouTube upload step.

**TikTok credentials:** Set `TIKTOK_SESSION_ID` in `.env` with the value of the `sessionid` cookie from tiktok.com (F12 → Application → Cookies). The sessionid lasts 60-90 days; renew it by repeating the same step.

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | faster-whisper model size (tiny/base/small/medium/large) |
| `DURACAO_ALVO_SEGUNDOS` | `90` | Target clip duration in seconds |
| `DURACAO_MINIMA_SEGUNDOS` | `45` | Minimum clip duration — shorter clips are discarded |
| `YOUTUBE_API_KEY` | *(empty)* | Public API key for YouTube Data API v3 — **required** for channel lookup |
| `YOUTUBE_CHANNEL_ID` | *(empty)* | Channel ID (`UC…`), `@handle`, or full URL — **required**; pipeline aborts if blank |
| `YOUTUBE_CANAL_MAX_VIDEOS` | `20` | How many recent channel videos to evaluate when picking the most viral |
| `YOUTUBE_PRIVACY` | `private` | Upload visibility (public/unlisted/private) |
| `YOUTUBE_COOKIES_FILE` | *(empty)* | Absolute path to a Netscape-format YouTube cookies file — required when VPS IP is flagged as bot |
| `TIKTOK_SESSION_ID` | *(empty)* | TikTok sessionid cookie — required for TikTok uploads; lasts ~60-90 days |
| `TIKTOK_INTERVALO_HORAS` | `3` | Hours between each TikTok clip upload (staggered schedule) |

## Pipeline Architecture

Each module in `src/` handles one stage and passes outputs to the next:

```
YOUTUBE_CHANNEL_ID (.env)
  → finder.py          → most viral unwatched video URL  [Phase 0 — auto]
  → downloader.py      → video file (assets/)            [Phase 1]
  → transcriber.py     → transcript .txt + .srt (temp/)  [Phase 2]
  → editor.py          → list of (start_sec, end_sec)    [Phase 3]
  → render.py          → MP4 clips (output/)             [Phase 4]
  → uploader_youtube.py → YouTube Shorts URLs            [Phase 5 — skips clips > 60s]
  → output_tiktok/     → queued for TikTok upload        [Phase 6]
  → cleanup assets/ temp/ output/                        [Phase 7]

  → tiktok_runner.py   → TikTok post (1 per cron run, from output_tiktok/ queue)
```

**Segmentation logic (`editor.py`):** Parses `[start -> end] text` lines with regex, groups segments sequentially until reaching `DURACAO_ALVO_SEGUNDOS`, drops final group if under `DURACAO_MINIMA_SEGUNDOS`.

**Rendering (`render.py`):** Builds FFmpeg filter graphs manually. Crop formula: `crop=ih*9/16:ih,scale=1080:1920`. Subtitles styled as Arial Bold, yellow, black outline. Includes Windows 8.3 short-path conversion for FFmpeg filter escaping. Output encoded with `-crf 18` for high quality.

**Upload YouTube (`uploader.py`):** First clip is published immediately as public; subsequent clips are scheduled as private with 3-hour intervals. OAuth2 token cached in `token.json`.

**Upload TikTok (`uploader_tiktok.py`):** One clip per run via FIFO queue in `output_tiktok/`. Authentication via `TIKTOK_SESSION_ID` in `.env`, passed directly as `cookies_list` to the uploader. Run via `tiktok_runner.py`, designed for cron/launchd scheduling.

## Key Design Decisions

- **yt-dlp with `player_client: [ios, web]`** — replaces pytubefix; actively maintained against YouTube bot detection; VPS IPs may still be blocked without a cookies file (`YOUTUBE_COOKIES_FILE`).
- **faster-whisper on CPU with int8 quantization** — balances speed and accuracy without GPU dependency.
- **Staggered upload schedule** — 3-hour gaps between clips to optimize YouTube algorithm distribution.
- The codebase and all user-facing strings are in Brazilian Portuguese.
