"""Watchdog: báo tiến độ render tik3 mỗi khi xong thêm ~10 folder.

Cách hoạt động:
- Đếm số folder output tik3 (folder = (m-1)*8+3) có du 45 mp4 > 0 bytes.
- Lưu mốc last_reported trong state file.
- Nếu số folder xong >= last_reported + 10 (hoặc đã đủ 80) -> in báo cáo (được deliver).
- Ngược lại in rỗng -> silent (không spam).
"""
import json
import os

ROOT = r"D:\TIKTOK-videonuoinick"
STATE = r"D:\CodexRuntime\tiktok-video\tik3-render-progress.json"
TOTAL = 80


def folder_for_machine(m):
    return (m - 1) * 8 + 3


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
        if n >= 45:
            done.append(m)
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

    if done_count >= last + 10 or done_count >= TOTAL:
        state["last_reported"] = done_count
        try:
            with open(STATE, "w", encoding="utf-8") as fh:
                json.dump(state, fh)
        except OSError:
            pass
        if done:
            rng = f"máy {done[0]}-{done[-1]}" if len(done) > 1 else f"máy {done[0]}"
        else:
            rng = "-"
        partial_txt = f" | đang render máy {partial[0]} ({partial[1]}/45)" if partial else ""
        print(
            f"✅ Tik3 render: {done_count}/{TOTAL} folder xong ({rng}){partial_txt}"
        )


if __name__ == "__main__":
    main()
