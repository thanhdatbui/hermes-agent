"""Watchdog: báo tiến độ render tik4 mỗi 1 tiếng (hoặc khi hoàn tất 80/80)."""
import os
import json
from datetime import datetime

ROOT = r"D:\TIKTOK-videonuoinick"
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
    partial = []
    zero = []

    for m in range(1, TOTAL + 1):
        fld = folder_for_machine(m)
        d = os.path.join(ROOT, str(fld))
        n = count_mp4(d) if os.path.isdir(d) else 0
        if n >= 30:
            done.append((m, fld, n))
        elif n > 0:
            partial.append((m, fld, n))
        else:
            zero.append((m, fld, 0))

    done_count = len(done)
    now_str = datetime.now().strftime("%H:%M %d/%m/%Y")

    if done_count >= TOTAL:
        print(f"✅ [DONE] Tik4 render - {now_str}\n• Đã hoàn tất: 80/80 folder\n• Tổng số video render: {sum(x[2] for x in done)} video")
    else:
        partial_txt = f"\n• Đang render: máy {partial[0][0]} (folder {partial[0][1]} - {partial[0][2]} video)" if partial else ""
        print(
            f"📊 [TIẾN ĐỘ RENDER TIK4 - {now_str}]\n"
            f"• Đã xong (>=30 video): {done_count}/{TOTAL} folder\n"
            f"• Chưa xong: {len(zero) + len(partial)}/{TOTAL} folder"
            f"{partial_txt}"
        )

if __name__ == "__main__":
    main()
