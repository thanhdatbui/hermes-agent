"""Xoá video YouTube dài (>MAX_DUR giây) đã tải nhầm vào D:\video goc; đồng bộ state.db.

Dùng khi pipeline chưa có duration filter (hoặc fallback /videos kéo video thường dài).
- Probe duration bằng ffprobe (chỉ file > min_size MB — file nhỏ là clip ngắn, bỏ qua nhanh)
- Xoá file > MAX_DUR → xoá record videos + perceptual_hashes trong state.db
- Giảm video_count folder + reset folder complete bị ảnh hưởng → insufficient_pool (re-download bù)

Kiểm chứng 17/08/2026: xoá 439 file / 250.1GB rác (phim hài 3.6GB, series 10.982s), reset 15 folder.
CẢNH BÁO: ffprobe KHÔNG nằm trong venv — dùng bản WinGet Gyan.FFmpeg (cập nhật path nếu đổi máy).
"""
import sqlite3
import subprocess
from pathlib import Path

FFPROBE = r"C:\Users\Kibe\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
STATE_DB = Path(r"D:\CodexRuntime\tiktok-video\state.db")
ROOT = Path(r"D:\video goc")
MAX_DUR = 300.0      # giây — khớp match_filter "duration < 300" trong download_by_niche
MIN_SIZE_MB = 100    # chỉ probe file lớn hơn mức này (clip ngắn chuẩn luôn nhỏ hơn)


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=20,
    )
    try:
        return float(r.stdout.strip())
    except (ValueError, TypeError):
        return -1.0


def main():
    conn = sqlite3.connect(STATE_DB)
    conn.row_factory = sqlite3.Row
    mp4s = [p for p in ROOT.rglob("*.mp4")]
    print(f"scan {len(mp4s)} mp4...", flush=True)
    removed_files = 0
    removed_bytes = 0
    folder_delta = {}
    for i, p in enumerate(mp4s):
        if p.stat().st_size < MIN_SIZE_MB * 1024 * 1024:
            continue
        dur = probe_duration(p)
        if not (0 < dur <= MAX_DUR):
            folder = int(p.parent.name) if p.parent.name.isdigit() else None
            print(f"XOA dur={dur:.0f}s {p.stat().st_size/1e6:.0f}MB folder={folder} {p.name[:60]}", flush=True)
            if folder is not None:
                row = conn.execute(
                    "SELECT video_id FROM videos WHERE folder=? AND output_path=?", (folder, str(p))
                ).fetchone()
                if row:
                    vid = row["video_id"]
                    conn.execute("DELETE FROM perceptual_hashes WHERE video_id=?", (vid,))
                    conn.execute("DELETE FROM videos WHERE video_id=?", (vid,))
                    folder_delta[folder] = folder_delta.get(folder, 0) + 1
            p.unlink(missing_ok=True)
            removed_files += 1
            removed_bytes += p.stat().st_size
        if (i + 1) % 100 == 0:
            print(f"...{i+1}/{len(mp4s)}", flush=True)
    for folder, n in folder_delta.items():
        conn.execute("UPDATE folders SET video_count = MAX(0, video_count - ?) WHERE folder_num=?", (n, folder))
        conn.execute("UPDATE folders SET status='insufficient_pool' WHERE folder_num=? AND status='complete'", (folder,))
    conn.commit()
    print(f"\nTONG: xoa {removed_files} file, {removed_bytes/1e9:.1f} GB | folder reset: {sorted(folder_delta)}", flush=True)


if __name__ == "__main__":
    main()