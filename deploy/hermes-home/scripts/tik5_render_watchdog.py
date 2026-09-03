"""Watchdog: báo tiến độ render Tik5 theo giờ."""
import os
from datetime import datetime

ROOT = r"D:\TIKTOK-videonuoinick"
TOTAL = 80


def count_mp4(path: str) -> int:
    try:
        return sum(
            1
            for name in os.listdir(path)
            if name.lower().endswith(".mp4")
            and os.path.getsize(os.path.join(path, name)) > 0
        )
    except OSError:
        return 0


def main() -> None:
    done = []
    partial = []
    zero = []
    for machine in range(1, TOTAL + 1):
        folder = (machine - 1) * 8 + 5
        count = count_mp4(os.path.join(ROOT, str(folder)))
        if count >= 30:
            done.append((machine, folder, count))
        elif count > 0:
            partial.append((machine, folder, count))
        else:
            zero.append((machine, folder, count))

    stamp = datetime.now().strftime("%H:%M %d/%m/%Y")
    if len(done) == TOTAL:
        print(
            f"✅ [DONE] Tik5 render - {stamp}\n"
            f"• Đã hoàn tất: {TOTAL}/{TOTAL} folder\n"
            f"• Tổng số video render: {sum(x[2] for x in done)} video"
        )
        return

    partial_text = ""
    if partial:
        machine, folder, count = partial[0]
        partial_text = f"\n• Đang render: máy {machine} (folder {folder} - {count} video)"
    print(
        f"📊 [TIẾN ĐỘ RENDER TIK5 - {stamp}]\n"
        f"• Đã xong (>=30 video): {len(done)}/{TOTAL} folder\n"
        f"• Chưa xong: {len(partial) + len(zero)}/{TOTAL} folder"
        f"{partial_text}"
    )


if __name__ == "__main__":
    main()
