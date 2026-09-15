#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watchdog giám sát tiến độ Download Video gốc và Render Tik1..Tik8 dùng chung cho toàn Farm (Kibe & Admin)."""

import os
import sys
import sqlite3
import datetime

try:
    import psutil
except ImportError:
    psutil = None


def detect_host():
    # Kiểm tra Admin host
    if os.path.exists(r"D:\video goc may 2") or os.environ.get("TAADAA_HOST", "").lower() == "admin":
        return {
            "name": "FARM ADMIN",
            "video_goc": r"D:\video goc may 2",
            "render_root": r"D:\TIKTOK-videonuoinick-admin",
            "state_db": r"D:\CodexRuntime\tiktok-video-machine2\state.db",
            "machine_range": range(201, 281),
            "base_machine": 201,
        }
    # Kibe host
    # Fast SSD NVMe (C:) is primary for fast I/O; fallback to HDD (D:)
    kibe_state_db = r"C:\CodexRuntime\tiktok-video\state.db"
    if not os.path.exists(kibe_state_db) and os.path.exists(r"D:\CodexRuntime\tiktok-video\state.db"):
        kibe_state_db = r"D:\CodexRuntime\tiktok-video\state.db"

    return {
        "name": "FARM KIBE",
        "video_goc": r"D:\video goc",
        "render_root": r"D:\TIKTOK-videonuoinick",
        "state_db": kibe_state_db,
        "machine_range": range(1, 81),
        "base_machine": 1,
    }


def is_download_running():
    if not psutil:
        return False
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or []).lower()
            if "download_by_niche.py" in cmd or "download_all_sources.py" in cmd:
                return True
        except Exception:
            pass
    return False


def is_render_running():
    if not psutil:
        return False
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            cmd = " ".join(p.info["cmdline"] or []).lower()
            if "random_batch_render.py" in cmd or "ffmpeg" in cmd:
                return True
        except Exception:
            pass
    return False


def get_source_video_stats(host_info):
    video_goc = host_info["video_goc"]
    state_db = host_info["state_db"]
    
    total_folders = 0
    ge30 = 0
    ge45 = 0
    total_mp4 = 0

    # Ưu tiên đọc siêu nhanh từ state.db (< 10ms)
    if os.path.exists(state_db):
        try:
            conn = sqlite3.connect(f"file:{state_db}?mode=ro", uri=True, timeout=5)
            cur = conn.cursor()
            cur.execute("SELECT video_count FROM folders WHERE video_count IS NOT NULL")
            rows = cur.fetchall()
            conn.close()
            if rows:
                total_folders = len(rows)
                for (cnt,) in rows:
                    total_mp4 += cnt
                    if cnt >= 30:
                        ge30 += 1
                    if cnt >= 45:
                        ge45 += 1
                return total_folders, ge30, ge45, total_mp4
        except Exception:
            pass

    # Fallback scan thư mục nếu không có DB
    if os.path.isdir(video_goc):
        try:
            with os.scandir(video_goc) as it:
                for entry in it:
                    if entry.is_dir() and entry.name.isdigit():
                        total_folders += 1
                        try:
                            # Chỉ lấy tối đa 50 file để tránh đơ HDD
                            cnt = 0
                            with os.scandir(entry.path) as sub_it:
                                for f in sub_it:
                                    if f.name.lower().endswith(".mp4") and not f.name.endswith(".part.mp4"):
                                        cnt += 1
                            total_mp4 += cnt
                            if cnt >= 30:
                                ge30 += 1
                            if cnt >= 45:
                                ge45 += 1
                        except Exception:
                            pass
        except Exception:
            pass

    return total_folders, ge30, ge45, total_mp4


def count_clips_in_folder(path):
    if not os.path.isdir(path):
        return 0
    cnt = 0
    try:
        with os.scandir(path) as it:
            for f in it:
                if f.name.lower().endswith(".mp4") and not f.name.endswith(".part.mp4"):
                    cnt += 1
    except Exception:
        pass
    return cnt


def get_render_stats(host_info):
    render_root = host_info["render_root"]
    base_machine = host_info["base_machine"]
    
    tik_stats = {}
    total_rendered = 0

    for slot in range(1, 9):
        ge30_folders = 0
        total_clips = 0
        for m in range(base_machine, base_machine + 80):
            folder_num = (m - base_machine) * 8 + slot
            folder_path = os.path.join(render_root, str(folder_num))
            c = count_clips_in_folder(folder_path)
            total_clips += c
            if c >= 30:
                ge30_folders += 1
        
        tik_stats[slot] = {
            "ge30": ge30_folders,
            "total_clips": total_clips,
            "pct": (ge30_folders / 80.0) * 100.0
        }
        total_rendered += total_clips

    return tik_stats, total_rendered


def main():
    host_info = detect_host()
    now_str = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
    
    # 1. Video gốc
    is_running = is_download_running()
    status_icon = "🟢" if is_running else "⚪"
    status_text = "Đang chạy" if is_running else "Đang dừng"
    
    src_folders, src_ge30, src_ge45, src_mp4 = get_source_video_stats(host_info)

    # 2. Render Tik1..Tik8
    is_render = is_render_running()
    render_icon = "🟢" if is_render else "⚪"
    render_text = "Đang chạy" if is_render else "Đang dừng"
    tik_stats, total_rendered = get_render_stats(host_info)

    tik_lines = []
    for slot in range(1, 9):
        st = tik_stats[slot]
        ge30 = st["ge30"]
        pct = st["pct"]
        clips = st["total_clips"]
        if ge30 >= 80:
            icon = "✅"
        elif ge30 > 0:
            icon = "🟡"
        else:
            icon = "⚪"
        tik_lines.append(f"{icon} Tik{slot}: <b>{ge30}/80</b> folder (≥30 clip) [{pct:.1f}%] | <b>{clips:,}</b> clip")

    tik_output = "\n".join(tik_lines)

    msg = f"""📊 <b>BÁO CÁO TIẾN ĐỘ {host_info['name']} (DOWNLOAD & RENDER)</b> - {now_str}

📥 <b>1. Video gốc (<code>{host_info['video_goc']}</code>):</b>
• Trạng thái download: {status_icon} <b>{status_text}</b>
• Tổng folder nguồn: <b>{src_folders:,}</b> folder
• Đạt ≥ 30 video: <b>{src_ge30:,}</b> folder
• Đạt ≥ 45 video: <b>{src_ge45:,}</b> folder
• Tổng video mp4 gốc: <b>{src_mp4:,}</b> video

🎬 <b>2. Tiến độ Render Tik1..Tik8 (<code>{host_info['render_root']}</code>):</b>
• Trạng thái render: {render_icon} <b>{render_text}</b>
{tik_output}

🔥 <b>Tổng clip render toàn farm:</b> <b>{total_rendered:,}</b> video"""

    print(msg)


if __name__ == "__main__":
    main()
