# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

ClipsAutomation downloads a YouTube video, transcribes its audio, splits it into timed clips, and renders each clip as a cropped 9:16 vertical MP4 with burned-in subtitles — fully automated from a single URL input.

## Running the project

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

FFmpeg must be placed inside `bin/` at the project root (not installed globally). `main.py` adds `bin/` to `PATH` automatically at startup.

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Meaning |
|---|---|---|
| `WHISPER_MODEL` | `small` | Whisper model size (`tiny` → `large-v3`) |
| `DURACAO_ALVO_SEGUNDOS` | `90` | Target clip length in seconds |
| `DURACAO_MINIMA_SEGUNDOS` | `45` | Minimum clip length; shorter clips are discarded |

## Pipeline architecture

`main.py` orchestrates four sequential phases, each backed by a module in `src/`:

1. **Download** (`src/downloader.py`) — `pytubefix` with `client='ANDROID_VR'` to bypass YouTube API restrictions. Saves the highest-resolution stream to `assets/`.

2. **Transcribe** (`src/transcriber.py`) — `faster-whisper` on CPU with `int8` compute. Produces two files in `temp/`:
   - `<name>.txt` — one line per segment in `[start -> end] text` format, consumed by the editor.
   - `<name>.srt` — standard subtitle file, consumed by FFmpeg.

3. **Analyze cuts** (`src/editor.py`) — Reads the `.txt` file, groups speech segments until `DURACAO_ALVO` is reached, and returns a list of `(start_sec, end_sec)` tuples. The last fragment is dropped if shorter than `DURACAO_MINIMA`.

4. **Render** (`src/render.py`) — For each cut:
   - Slices the `.srt` to the cut's time window, resets timestamps to zero, and wraps long lines to ≤2 lines of ≤30 chars each → `temp/srt_NN.srt`.
   - FFmpeg pipeline: `crop` to `ih*9/16` (center crop) → `subtitles` filter → `libx264` + `aac` → `output/<name>_corte_NN.mp4`.

After a successful run, `assets/` and `temp/` are cleaned automatically.

## Windows-specific: path handling in FFmpeg

The `subtitles` filter in FFmpeg breaks on paths containing spaces. `render.py:_short_path()` calls `GetShortPathNameW` (Win32 API) to convert paths to 8.3 format, then escapes the drive-letter colon (`C:` → `C\:`). Any changes to how SRT paths are passed to FFmpeg must preserve this logic.
