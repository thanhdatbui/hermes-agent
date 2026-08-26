# Cron wrapper: tự động sync 2 skill điều phối lên git repo Hermes (commit + push).
# Silent khi không có thay đổi; in ra khi đã push (để cron deliver biết).
import subprocess

PS1 = r"D:\Taadaa\Hermes\deploy\sync-orchestration-skills.ps1"

try:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", PS1],
        capture_output=True, text=True, timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    out = (r.stdout or "") + (r.stderr or "")
    if "SYNCED" in out:
        # Chỉ in khi có push thật sự
        print(out.strip())
    elif "SKILLS_UNCHANGED" in out:
        pass  # silent - không có gì để báo
    else:
        print("SYNC_ERROR:", out.strip()[:300])
except Exception as exc:
    print("SYNC_ERROR:", type(exc).__name__, str(exc)[:300])
