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

**Google credentials:** Place `client_secrets.json` (OAuth2 from Google Cloud Console) in the project root before using the upload step.

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `small` | faster-whisper model size (tiny/base/small/medium/large) |
| `DURACAO_ALVO_SEGUNDOS` | `90` | Target clip duration in seconds |
| `DURACAO_MINIMA_SEGUNDOS` | `45` | Minimum clip duration — shorter clips are discarded |
| `YOUTUBE_PRIVACY` | `private` | Upload visibility (public/unlisted/private) |

## Pipeline Architecture

Each module in `src/` handles one stage and passes outputs to the next:

```
YouTube URL
  → downloader.py   → video file (assets/)
  → transcriber.py  → transcript .txt + .srt (assets/)
  → editor.py       → list of (start_sec, end_sec) tuples
  → render.py       → individual MP4 clips (output/)
  → uploader.py     → YouTube Shorts URLs
```

**Segmentation logic (`editor.py`):** Parses `[start -> end] text` lines with regex, groups segments sequentially until reaching `DURACAO_ALVO_SEGUNDOS`, drops final group if under `DURACAO_MINIMA_SEGUNDOS`.

**Rendering (`render.py`):** Builds FFmpeg filter graphs manually. Crop formula: `crop=ih*9/16:ih`. Subtitles styled as Arial Bold, yellow, black outline. Includes Windows 8.3 short-path conversion for FFmpeg filter escaping.

**Upload (`uploader.py`):** First clip is published immediately as public; subsequent clips are scheduled as private with 3-hour intervals. OAuth2 token cached in `token.json`.

## Key Design Decisions

- **pytubefix with `client='ANDROID_VR'`** — required to bypass YouTube web API restrictions.
- **faster-whisper on CPU with int8 quantization** — balances speed and accuracy without GPU dependency.
- **Staggered upload schedule** — 3-hour gaps between clips to optimize YouTube algorithm distribution.
- The codebase and all user-facing strings are in Brazilian Portuguese.
