import os
import sys
import subprocess

PYTHON_EXE = r"D:/Taadaa/python-envs/automation/Scripts/python.exe"
TARGET_SCRIPT = r"D:/Taadaa/tools/tiktok_account_tracker.py"


def main():
    # Pass along any additional arguments passed to this wrapper (e.g. --limit 2)
    # Default workers is 10 unless overridden in sys.argv
    cmd = [PYTHON_EXE, TARGET_SCRIPT]
    if "--workers" not in sys.argv:
        cmd.extend(["--workers", "10"])
    cmd.extend(sys.argv[1:])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
    except Exception as e:
        print(f"❌ ERROR executing tracker script: {e}")
        sys.exit(1)

    if proc.returncode == 0:
        stdout_text = proc.stdout or ""
        marker = "========================================"
        if marker in stdout_text:
            summary = stdout_text[stdout_text.index(marker):].strip()
            print(summary)
        else:
            print(stdout_text.strip())
        sys.exit(0)
    else:
        print(f"❌ ERROR: tiktok_account_tracker failed with exit code {proc.returncode}")
        if proc.stderr:
            print(f"STDERR:\n{proc.stderr.strip()}")
        if proc.stdout:
            print(f"STDOUT:\n{proc.stdout.strip()}")
        sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
