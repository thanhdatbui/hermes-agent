"""Watchdog: báo tiến độ render tik4 mỗi khi xong thêm 10 folder (hoặc hoàn tất 80/80).

Cách hoạt động:
- Đếm số folder output tik4 (folder = (m-1)*8+4) có đủ >= 30 mp4 > 0 bytes (theo min_videos 30 / target 45).
- Lưu mốc last_reported trong state file.
- Nếu số folder xong >= last_reported + 10 (hoặc đã đủ 80) -> in báo cáo.
- Ngược lại in rỗng -> silent (Hermes cron no_agent im lặng).
"""
import json
import os

ROOT = r"D:\TIKTOK-videonuoinick"
STATE = r"D:\CodexRuntime\tiktok-video\tik4-render-progress.json"
TOTAL = 80


def folder_for_machine(m):
    return (m - 1) * 8 + 4


def count_mp4(path):
    try:
        return sum(
            1
            for f in os.listdir(path)
            if f.lower().endswith(".mp4")
            and os.path.getsize(os.path.join(path, f)) > 0
        )
    except OSError:
        return 0


def main():
    done = []
    partial = None
    for m in range(1, TOTAL + 1):
        d = os.path.join(ROOT, str(folder_for_machine(m)))
        n = count_mp4(d) if os.path.isdir(d) else 0
        if n >= 30: # 30..45 videos
            done.append((m, n))
        elif n > 0 and partial is None:
            partial = (m, n)
    done_count = len(done)

    state = {}
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            state = {}
    last = int(state.get("last_reported", 0))

    if (done_count >= last + 10 and done_count > 0) or (done_count >= TOTAL and last < TOTAL):
        state["last_reported"] = done_count
        try:
            os.makedirs(os.path.dirname(STATE), exist_ok=True)
            with open(STATE, "w", encoding="utf-8") as fh:
                json.dump(state, fh)
        except OSError:
            pass
        
        first_m = done[0][0]
        last_m = done[-1][0]
        rng = f"máy {first_m}-{last_m}" if len(done) > 1 else f"máy {first_m}"
        partial_txt = f" | đang render máy {partial[0]} ({partial[1]} video)" if partial else ""
        
        prefix = "✅ [DONE] Tik4 render" if done_count >= TOTAL else "📊 [TIẾN ĐỘ] Tik4 render"
        print(f"{prefix}: {done_count}/{TOTAL} folder xong ({rng}){partial_txt}")


if __name__ == "__main__":
    main()
