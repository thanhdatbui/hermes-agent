# Real media canary gate for dubbing and render pipelines

Use this checklist whenever a task claims an end-to-end video dubbing, TTS, or audio/video mixing capability. A standalone model probe (generating a few WAV files) proves only that the TTS engine runs in isolation; it is not proof that the pipeline, ASR, translation, subtitle generation, audio ducking, or FFmpeg render succeed on a real video.

## Acceptance matrix

| Step | Required check | Evidence | Blocking condition |
|---|---|---|---|
| 1. Source media | Native path existence, size > 0, streams present | `Path.exists()`, `ffprobe` stream summary | Missing file, 0 bytes, video/audio missing |
| 2. Pipeline execution | Real CLI/pipeline command, not mocked test | Terminal output, exit code, process ID | Unhandled exception, unparsed args, syntax error |
| 3. Output media | Output file exists, fresh timestamp, non-trivial size | `stat.st_size`, `mtime` | Output missing, truncated file (<100KB) |
| 4. Stream integrity | Both video (H.264/etc) and audio (AAC/etc) present | `ffprobe -show_entries stream=codec_name,codec_type` | Audio missing, silent track, video dropped |
| 5. Perceptual audit | Speech intelligible, timing aligned, ducking active | Human or focused verification of artifact | Speech overlapping, unintelligible, wrong language |

## Windows / MSYS path pitfall and fix

- **Symptom:** Command launched in Git Bash fails with `FileNotFoundError: Input video not found: /d/Taadaa/...`.
- **Cause:** Git Bash uses MSYS POSIX paths (`/d/Taadaa/...`), but native Windows Python (`python.exe`) resolves paths using Windows drive letters (`D:\...` or `D:/...`). Standard `pathlib.Path('/d/...')` treats the leading slash as the current drive root (`C:\d\...`), failing to find the file on drive `D:`.
- **Fix:**
  - Always pass native drive paths with forward or escaped backward slashes (`D:/Taadaa/...` or `D:\\Taadaa\\...`) as CLI arguments to native Python processes.
  - Shell `cd /d/Taadaa/...` is fine for changing directories, but any path argument handed to a Python script must be native Windows format.
  - Test path existence inside Python before starting long background jobs:
    ```python
    from pathlib import Path
    p = Path(r"D:/Taadaa/path/to/file.mp4")
    assert p.exists() and p.stat().st_size > 0
    ```

## Terminal guard pitfall with virtualenv binaries

- **Symptom:** `Failed to execute command: open: embedded null character in path` from `lifecycle_guard.py`.
- **Cause:** Passing a path literal like `.venv/Scripts/python.exe` directly in the command causes the lifecycle guard's shell script scanner to tokenize the executable path, treat it as a candidate shell script, open the Windows PE binary, and encounter binary NUL bytes.
- **Fix:**
  - Add the virtualenv `Scripts` directory to `PATH` first:
    `export PATH="<abs_path>/.venv/Scripts:$PATH" && python ...`
  - This lets the guard classify `python` as a standard shell executable without attempting to inspect the binary file as a shell script.
