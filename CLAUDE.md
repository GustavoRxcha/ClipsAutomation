# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

ClipsAutomation is a Python pipeline that converts long YouTube videos into YouTube Shorts. It downloads a video, transcribes it, segments the transcript into clips, renders each clip at 9:16 with burned-in subtitles, and optionally uploads them to YouTube.

## Setup & Run

```bash
pip install -r requirements.txt
cp .env.example .env   # configure environment variables
python main.py         # prompts for a YouTube URL, then runs the full pipeline
```

**Required external dependency:** FFmpeg must be installed and available on PATH.

**Google credentials:** Place `client_secrets.json` (OAuth2 from Google Cloud Console) in the project root before using the YouTube upload step.

**TikTok credentials:** Export your TikTok session cookies and save them as `tiktok_cookies.json` in the project root. Use a browser extension such as "Get cookies.txt LOCALLY" on the TikTok website, then rename the exported file. Phase 6 is skipped silently if `tiktok-uploader` is not installed or if the cookies file is missing.

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | faster-whisper model size (tiny/base/small/medium/large) |
| `DURACAO_ALVO_SEGUNDOS` | `90` | Target clip duration in seconds |
| `DURACAO_MINIMA_SEGUNDOS` | `45` | Minimum clip duration — shorter clips are discarded |
| `YOUTUBE_PRIVACY` | `private` | Upload visibility (public/unlisted/private) |
| `TIKTOK_INTERVALO_HORAS` | `3` | Hours between each TikTok clip upload (staggered schedule) |

## Pipeline Architecture

Each module in `src/` handles one stage and passes outputs to the next:

```
YouTube URL
  → downloader.py      → video file (assets/)
  → transcriber.py     → transcript .txt + .srt (assets/)
  → editor.py          → list of (start_sec, end_sec) tuples
  → render.py          → individual MP4 clips (output/)
  → uploader.py        → YouTube Shorts URLs        [Phase 5 — optional]
  → uploader_tiktok.py → TikTok video identifiers   [Phase 6 — optional]
```

**Segmentation logic (`editor.py`):** Parses `[start -> end] text` lines with regex, groups segments sequentially until reaching `DURACAO_ALVO_SEGUNDOS`, drops final group if under `DURACAO_MINIMA_SEGUNDOS`.

**Rendering (`render.py`):** Builds FFmpeg filter graphs manually. Crop formula: `crop=ih*9/16:ih,scale=1080:1920`. Subtitles styled as Arial Bold, yellow, black outline. Includes Windows 8.3 short-path conversion for FFmpeg filter escaping. Output encoded with `-crf 18` for high quality.

**Upload YouTube (`uploader.py`):** First clip is published immediately as public; subsequent clips are scheduled as private with 3-hour intervals. OAuth2 token cached in `token.json`.

**Upload TikTok (`uploader_tiktok.py`):** Same staggered schedule (3-hour gaps). Authentication via session cookies stored in `tiktok_cookies.json`. Import is conditional — Phase 6 only appears in `main.py` if `tiktok-uploader` is installed.

## Key Design Decisions

- **pytubefix with `client='ANDROID_VR'`** — required to bypass YouTube web API restrictions.
- **faster-whisper on CPU with int8 quantization** — balances speed and accuracy without GPU dependency.
- **Staggered upload schedule** — 3-hour gaps between clips to optimize YouTube algorithm distribution.
- The codebase and all user-facing strings are in Brazilian Portuguese.
