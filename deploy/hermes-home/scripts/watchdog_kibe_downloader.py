import os
import sys
import subprocess
import psutil

OUTPUT_ROOT = r"D:/video goc"

def check_all_folders_completed():
    if not os.path.exists(OUTPUT_ROOT):
        return False
    try:
        completed = 0
        for f in range(1, 641):
            f_path = os.path.join(OUTPUT_ROOT, str(f))
            if os.path.isdir(f_path):
                cnt = sum(1 for x in os.scandir(f_path) if x.name.endswith(".mp4"))
                if cnt >= 45:
                    completed += 1
            else:
                return False
        return completed >= 640
    except Exception:
        return False

def is_running():
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or [])
            if "download_by_niche.py" in cmd or "run_kibe_downloader_service.py" in cmd:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def main():
    if check_all_folders_completed():
        return 0

    if is_running():
        return 0

    python_exe = r"C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
    script_p = r"C:/Users/Kibe/run_kibe_downloader_service.py"
    log_p = r"D:/CodexRuntime/tiktok-video/download_kibe_p10.log"

    os.makedirs(r"D:/CodexRuntime/tiktok-video", exist_ok=True)
    with open(log_p, "a", encoding="utf-8") as f:
        f.write("\n[WATCHDOG] Spawning run_kibe_downloader_service.py...\n")
        subprocess.Popen(
            [python_exe, "-u", script_p],
            stdout=f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    return 0

if __name__ == "__main__":
    sys.exit(main())
