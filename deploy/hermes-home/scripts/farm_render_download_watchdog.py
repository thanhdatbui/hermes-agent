#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watchdog giám sát tiến độ Download Video gốc và Render Tik1..Tik8 dùng chung cho toàn Farm (Kibe & Admin)."""

import os
import sys
import sqlite3
import datetime
import json
import subprocess

try:
    import psutil
except ImportError:
    psutil = None

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def detect_host():
    user = os.environ.get("USERNAME", "").lower()
    # Kiểm tra Admin host dựa trên Username hoặc TAADAA_HOST
    if user == "admin" or os.environ.get("TAADAA_HOST", "").lower() == "admin":
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
    try:
        out = subprocess.check_output('wmic process where "name=\'python.exe\'" get commandline', shell=True, text=True, errors="replace", timeout=5)
        out_lower = out.lower()
        if "download_by_niche.py" in out_lower or "download_all_sources.py" in out_lower or "auto_rescan_loop.py" in out_lower or "smart_gaixinh" in out_lower or "distribute_exclusive" in out_lower or "clean_vn" in out_lower or "run_admin_clean_vn" in out_lower or "run_admin_downloader" in out_lower:
            return True
    except Exception:
        pass
    return False


def is_render_running():
    try:
        out = subprocess.check_output('wmic process where "name=\'python.exe\' or name=\'ffmpeg.exe\'" get commandline', shell=True, text=True, errors="replace", timeout=5)
        out_lower = out.lower()
        if "random_batch_render.py" in out_lower or "run_render" in out_lower or "ffmpeg" in out_lower or "admin_render_chain" in out_lower:
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
        ge45_folders = 0
        total_clips = 0
        for m in range(base_machine, base_machine + 80):
            folder_num = (m - base_machine) * 8 + slot
            folder_path = os.path.join(render_root, str(folder_num))
            c = count_clips_in_folder(folder_path)
            total_clips += c
            if c >= 45:
                ge45_folders += 1
        
        tik_stats[slot] = {
            "ge45": ge45_folders,
            "total_clips": total_clips,
            "pct": (ge45_folders / 80.0) * 100.0
        }
        total_rendered += total_clips

    return tik_stats, total_rendered


def format_cluster_section(label, render_root, video_goc, is_running, sf, s30, s45, smp4, is_rd, tik_stats, total_rendered, prev_tik=None, prev_total=None):
    rd_icon = "🟢" if is_rd else "⚪"
    rd_text = "Đang chạy" if is_rd else "Đang dừng"
    dl_icon = "🟢" if is_running else "⚪"
    dl_text = "Đang chạy" if is_running else "Đang dừng"

    tik_lines = []
    for slot in range(1, 9):
        st = tik_stats.get(str(slot), tik_stats.get(slot, {}))
        ge45 = st.get("ge45", st.get("ge30", 0))
        pct = st.get("pct", 0.0)
        clips = st.get("total_clips", 0)
        prev_clips = prev_tik.get(str(slot)) if prev_tik else None
        if ge45 >= 80:
            icon = "✅"
        elif ge45 > 0:
            icon = "🟡"
        else:
            icon = "⚪"
        tik_lines.append(f"{icon} Tik{slot}: <b>{ge45}/80</b> folder (≥45 clip) [{pct:.1f}%] | <b>{clips:,}</b> clip{_fmt_delta(clips, prev_clips)}")
    tik_output = "\n".join(tik_lines)

    starving_slots = []
    for slot in range(1, 9):
        st = tik_stats.get(str(slot), tik_stats.get(slot, {}))
        ge45 = st.get("ge45", st.get("ge30", 0))
        if ge45 < 80:
            starving_slots.append(f"Tik{slot} (thiếu {80 - ge45})")
    starving_part = ""
    if starving_slots:
        starving_part = f"\n⚠️ <b>Chưa đủ trần (80/80):</b> {', '.join(starving_slots)}"

    show_download = is_running or s45 < 640
    dl_part = ""
    if show_download:
        lack_str = f" <i>(thiếu {640 - s45} folder để phủ 8 Tik)</i>" if s45 < 640 else ""
        dl_part = f"""📥 <b>Video gốc (<code>{video_goc}</code>):</b>
• Trạng thái download: {dl_icon} <b>{dl_text}</b>
• Đạt ≥ 45 video: <b>{s45:,}/{sf:,}</b> folder | <b>{smp4:,}</b> clip{lack_str}
"""

    return f"""🏢 <b>{label} (<code>{render_root}</code>):</b>
{dl_part}• Trạng thái render: {rd_icon} <b>{rd_text}</b>
{tik_output}{starving_part}
👉 Đã render cụm: <b>{total_rendered:,}</b> clip{_fmt_delta(total_rendered, prev_total)}"""


ADMIN_CACHE_PATH = r"D:\OneDrive\TaadaaData\admin\last_render_stats.json"
PREV_SNAPSHOT_PATH = r"D:\Taadaa\runtime\kibe\cron-state\farm_render_download_last_snapshot.json"


def fetch_admin_stats_remote():
    try:
        cmd = ['ssh', '-o', 'ConnectTimeout=3', 'admin-farm', 'python -c "import sys; sys.path.append(r\'%LOCALAPPDATA%\\hermes\\scripts\'); import farm_render_download_watchdog as f, json; h = f.detect_host(); is_dl = f.is_download_running(); sf, s30, s45, smp4 = f.get_source_video_stats(h); is_rd = f.is_render_running(); tst, trd = f.get_render_stats(h); print(json.dumps({\'name\': h[\'name\'], \'video_goc\': h[\'video_goc\'], \'render_root\': h[\'render_root\'], \'is_dl\': is_dl, \'src_folders\': sf, \'src_ge30\': s30, \'src_ge45\': s45, \'src_mp4\': smp4, \'is_rd\': is_rd, \'tik_stats\': tst, \'total_rendered\': trd}))"']
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    try:
                        os.makedirs(os.path.dirname(ADMIN_CACHE_PATH), exist_ok=True)
                        with open(ADMIN_CACHE_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    return data, "LIVE"
    except Exception:
        pass

    if os.path.exists(ADMIN_CACHE_PATH):
        try:
            with open(ADMIN_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f), "CACHE"
        except Exception:
            pass

    return None, "OFFLINE"


def _fmt_delta(curr: int, prev: int | None) -> str:
    if prev is not None and curr >= prev:
        return f' [+{curr - prev:,}]'
    return f' [{curr - prev:,}]' if prev is not None else ''


def load_prev_snapshot():
    if not os.path.exists(PREV_SNAPSHOT_PATH):
        return None
    try:
        with open(PREV_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_snapshot(snapshot):
    try:
        os.makedirs(os.path.dirname(PREV_SNAPSHOT_PATH), exist_ok=True)
        tmp_path = PREV_SNAPSHOT_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, PREV_SNAPSHOT_PATH)
    except Exception:
        pass


def main():
    host_info = detect_host()
    now_str = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")

    # Local stats
    is_running = is_download_running()
    src_folders, src_ge30, src_ge45, src_mp4 = get_source_video_stats(host_info)
    is_render = is_render_running()
    tik_stats, total_rendered = get_render_stats(host_info)

    # If called with --json or on Admin machine directly: output local cluster only
    if "--json" in sys.argv or host_info["name"] == "FARM ADMIN":
        payload = {
            "name": host_info["name"],
            "video_goc": host_info["video_goc"],
            "render_root": host_info["render_root"],
            "is_dl": is_running,
            "src_folders": src_folders,
            "src_ge30": src_ge30,
            "src_ge45": src_ge45,
            "src_mp4": src_mp4,
            "is_rd": is_render,
            "tik_stats": tik_stats,
            "total_rendered": total_rendered,
        }
        if "--json" in sys.argv:
            print(json.dumps(payload))
            return
        # If on Admin directly without --json
        sec = format_cluster_section(
            "FARM ADMIN (MÁY 201-280)",
            host_info["render_root"],
            host_info["video_goc"],
            is_running,
            src_folders,
            src_ge30,
            src_ge45,
            src_mp4,
            is_render,
            tik_stats,
            total_rendered,
        )
        print(f"📊 <b>BÁO CÁO TIẾN ĐỘ FARM ADMIN</b> - {now_str}\n\n{sec}\n\n🔥 <b>Tổng clip render:</b> <b>{total_rendered:,}</b> video")
        return

    # Running on KIBE: generate unified report for BOTH KIBE and ADMIN
    prev = load_prev_snapshot() or {}
    prev_ts = prev.get("timestamp")
    prev_kibe_total = prev.get("kibe_total")
    prev_kibe_tik = prev.get("kibe_tik_clips") or {}
    prev_admin_total = prev.get("admin_total")
    prev_admin_tik = prev.get("admin_tik_clips") or {}
    prev_grand = prev.get("grand_total")

    kibe_sec = format_cluster_section(
        "FARM KIBE (MÁY 1-80)",
        host_info["render_root"],
        host_info["video_goc"],
        is_running,
        src_folders,
        src_ge30,
        src_ge45,
        src_mp4,
        is_render,
        tik_stats,
        total_rendered,
        prev_tik=prev_kibe_tik,
        prev_total=prev_kibe_total,
    )
    kibe_tik_clips = {str(slot): st["total_clips"] for slot, st in tik_stats.items()}

    admin_data, admin_mode = fetch_admin_stats_remote()
    if admin_data:
        admin_total = admin_data.get("total_rendered", 0)
        admin_tik_clips = {str(slot): st.get("total_clips", 0) for slot, st in admin_data.get("tik_stats", {}).items()}
        admin_sec = format_cluster_section(
            "FARM ADMIN (MÁY 201-280)",
            admin_data["render_root"],
            admin_data["video_goc"],
            admin_data.get("is_dl", False),
            admin_data.get("src_folders", 0),
            admin_data.get("src_ge30", 0),
            admin_data.get("src_ge45", 0),
            admin_data.get("src_mp4", 0),
            admin_data.get("is_rd", False),
            admin_data.get("tik_stats", {}),
            admin_total,
            prev_tik=prev_admin_tik,
            prev_total=prev_admin_total,
        )
        grand_total = total_rendered + admin_total
        compare_line = ""
        if prev_grand is not None:
            compare_line = f"\n\n🕒 So với lần trước ({prev_ts}): <b>{prev_grand:,}</b> → <b>{grand_total:,}</b> video"
        msg = f"""📊 <b>BÁO CÁO TIẾN ĐỘ RENDER TOÀN FARM</b> - {now_str}

{kibe_sec}

{admin_sec}

🔥 <b>TỔNG CLIP RENDER TOÀN BỘ 2 FARM:</b> <b>{grand_total:,}</b> video{_fmt_delta(grand_total, prev_grand)}{compare_line}"""
    else:
        admin_total = prev_admin_total
        admin_tik_clips = prev_admin_tik
        grand_total = (total_rendered + admin_total) if admin_total is not None else None
        msg = f"""📊 <b>BÁO CÁO TIẾN ĐỘ RENDER TOÀN FARM</b> - {now_str}

{kibe_sec}

⚠️ <i>Farm Admin (M201-280): Không kết nối được qua mạng LAN</i>

🔥 <b>Tổng clip render Farm Kibe:</b> <b>{total_rendered:,}</b> video{_fmt_delta(total_rendered, prev_kibe_total)}"""

    save_snapshot({
        "timestamp": now_str,
        "kibe_total": total_rendered,
        "admin_total": admin_total,
        "grand_total": grand_total,
        "kibe_tik_clips": kibe_tik_clips,
        "admin_tik_clips": admin_tik_clips,
    })
    print(msg)


if __name__ == "__main__":
    main()
