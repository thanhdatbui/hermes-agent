#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cron wrapper for Taadaa Farm Stale Upload Accounts Watchdog.
Runs daily at 07:15 AM to inspect upload cadence and data drift across all accounts.
Outputs clean Telegram-compatible markdown format under 3500 chars.
"""

import sys
import subprocess
import json
from pathlib import Path

PYTHON_EXE = sys.executable
SCRIPT_PATH = r"D:/Taadaa/tools/audit_stale_upload_accounts.py"
PREV_SNAPSHOT_PATH = Path(r'D:\Taadaa\runtime\kibe\cron-state\stale_upload_watchdog_last_snapshot.json')


def _fmt_delta(curr: int, prev: int | None) -> str:
    return f' [{curr - prev:+d}]' if prev is not None else ''


def load_previous_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def save_current_snapshot(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_flop_section(cluster: str = "kibe", limit: int = 8) -> tuple[list[str], int]:
    res_lines = []
    f_cnt = 0
    try:
        sys.path.insert(0, r"D:/Taadaa/tools")
        from flop_channel_scanner import scan_farm_flop_channels
        excel_dir = r"D:/OneDrive/TaadaaData/kibe" if cluster == "kibe" else r"D:/OneDrive/TaadaaData/admin"
        res = scan_farm_flop_channels(
            db_path=r"D:/Taadaa/data/tiktok_tracker.db",
            excel_dir=excel_dir,
            cluster=cluster,
            min_videos=5,
            flop_heart_threshold=20,
        )
        flop_list = res.get("flop_need_source_swap", [])
        swap_plan = res.get("swap_plan", [])
        plan_by_user = {item["username"]: item for item in swap_plan}

        summary = res.get("summary", {})
        h_cnt = summary.get("healthy", 0)
        s_cnt = summary.get("stagnant_watch", 0)
        f_cnt = summary.get("flop_need_source_swap", 0)

        res_lines.append(f"\n📉 [ĐỐI SOÁT KÊNH FLOP & ĐỀ XUẤT XOAY NGUỒN] ({f_cnt} kênh flop):")
        res_lines.append(f"• Tỷ lệ: {h_cnt} khỏe 🟢 | {s_cnt} theo dõi 🟡 | {f_cnt} flop cần xoay 🔴")
        if flop_list:
            res_lines.append("• Top kênh flop (vẫn đăng đều nhưng view/tim kẹt đáy):")
            for acc in flop_list[:limit]:
                u = acc.get("username", "")
                m = acc.get("may", 0)
                tik = acc.get("tik", 0)
                v = acc.get("video_count", 0)
                h = acc.get("heart_count", 0)
                plan = plan_by_user.get(u, {})
                niche = plan.get("suggested_niche", "niche_hot")
                seq = plan.get("start_seq", v + 1)
                res_lines.append(f"  • M{m:<3} T{tik}: @{u} ({v} clip, {h} tim) ➔ Đổi ngách '{niche}' (từ clip {seq})")
            if len(flop_list) > limit:
                res_lines.append(f"  ... và {len(flop_list) - limit} kênh flop khác.")
            res_lines.append("👉 Lệnh O(1) swap mẫu: python D:/Taadaa/tools/flop_channel_scanner.py --generate-swap-commands")
    except Exception as e:
        res_lines.append(f"\n⚠️ Không thể quét kênh flop: {e}")
    return res_lines, f_cnt


def main():
    try:
        from cron_alert_core import CronRun
    except ImportError:
        CronRun = None

    force = "--force" in sys.argv
    run = CronRun("cron_stale_upload_watchdog", force_report=force) if CronRun else None
    if run:
        run.__enter__()
    if not Path(SCRIPT_PATH).exists():
        if run:
            run.anomaly("SCRIPT_NOT_FOUND", f"Script not found: {SCRIPT_PATH}")
            run.__exit__(None, None, None)
        else:
            print(f"❌ Script not found: {SCRIPT_PATH}")
        sys.exit(1)

    cmd = [
        PYTHON_EXE,
        SCRIPT_PATH,
        "--days", "9",
        "--critical-days", "14",
        "--json"
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120
        )
    except Exception as e:
        print(f"❌ Lỗi chạy audit_stale_upload_accounts: {e}")
        sys.exit(1)

    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        # Fallback to stdout if JSON parsing fails
        print("📋 [BÁO CÁO ĐỐI SOÁT ĐĂNG VIDEO FARM]")
        print((proc.stdout or proc.stderr)[:3500])
        sys.exit(0)

    drift_issues = data.get("workbook_drift_issues", [])
    freshness = data.get("upload_freshness", {})

    ref_date = freshness.get("reference_date", "Hôm nay")
    tot = freshness.get("total_farm_accounts", 0)
    act = freshness.get("active_count", 0)
    zero = freshness.get("zero_video_count", 0)
    warn = freshness.get("warning_stale_count", 0)
    crit = freshness.get("critical_stale_count", 0)
    days_thr = freshness.get('days_threshold', 9)
    crit_thr = freshness.get('critical_threshold', 14)

    prev = load_previous_snapshot(PREV_SNAPSHOT_PATH)
    prev_vals = prev or {}

    lines = []
    lines.append(f"📊 [BÁO CÁO ĐỐI SOÁT TIẾN ĐỘ ĐĂNG VIDEO TOÀN FARM] ({ref_date})")
    lines.append("────────────────────────────────")
    lines.append(f"• Tổng số nick quản lý: {tot}{_fmt_delta(tot, prev_vals.get('tot'))}")
    lines.append(f"• Đang đăng đều (≤ {days_thr} ngày): {act} nick{_fmt_delta(act, prev_vals.get('act'))}")
    lines.append(f"• Nick mới warm-up (0 video): {zero} nick{_fmt_delta(zero, prev_vals.get('zero'))}")
    lines.append(f"• Cảnh báo trễ ({days_thr} - {crit_thr} ngày): {warn} nick{_fmt_delta(warn, prev_vals.get('warn'))}")
    lines.append(f"• 🚨 NGUY CƠ ĐÓNG BĂNG (> {crit_thr} ngày): {crit} nick{_fmt_delta(crit, prev_vals.get('crit'))}")
    if prev is not None:
        lines.append(f"↔ So sánh với lần chạy trước ({prev.get('ref_date', '?')}) — [±n] là chênh lệch")
    lines.append("────────────────────────────────")

    # Drift issues
    if drift_issues:
        lines.append(f"\n❌ [CẢNH BÁO LỆCH FILE EXCEL (DATA DRIFT)]: {len(drift_issues)} lỗi")
        for iss in drift_issues[:5]:
            lines.append(f"  • {iss.get('detail', '')}")
        if len(drift_issues) > 5:
            lines.append(f"  ... và {len(drift_issues) - 5} lỗi khác.")
    else:
        lines.append("\n✓ Tính toàn vẹn Excel: 100% khớp giữa Master DAT và Tik1..Tik8.")

    # Critical stale accounts
    crit_list = freshness.get("critical_stale", [])
    if crit_list:
        lines.append(f"\n🚨 [TOP NICK BỊ ĐÓNG BĂNG LÂU NHẤT (> 14 NGÀY)] ({len(crit_list)} nick):")
        # Gom theo cụm máy để dễ nhìn
        for acc in crit_list[:15]:
            m = acc.get("machine", 0)
            slot = acc.get("slot", 0)
            host = acc.get("host", "kibe")
            u = acc.get("username", "")
            days = acc.get("days_stale", 0)
            vids = acc.get("videos", 0)
            since = str(acc.get("stuck_since", ""))[:10]
            lines.append(f"  • M{m:<3} T{slot} ({host}): @{u} (kẹt {days}d từ {since}, dừng ở {vids} clip)")

        if len(crit_list) > 15:
            lines.append(f"  ... và {len(crit_list) - 15} nick khác kẹt > 14 ngày.")

    # Warning stale accounts
    warn_list = freshness.get("warning_stale", [])
    if warn_list and not crit_list:
        lines.append(f"\n⚠️ [NICK CẦN THEO DÕI (> 7 NGÀY CHƯA TĂNG VIDEO)] ({len(warn_list)} nick):")
        for acc in warn_list[:10]:
            m = acc.get("machine", 0)
            slot = acc.get("slot", 0)
            u = acc.get("username", "")
            days = acc.get("days_stale", 0)
            vids = acc.get("videos", 0)
            lines.append(f"  • M{m:<3} T{slot}: @{u} ({days}d chưa lên clip, hiện có {vids} clip)")

    # Flop channels & source swap recommendation
    flop_lines, f_cnt = _get_flop_section(cluster="kibe", limit=8)
    lines.extend(flop_lines)

    if run:
        run.check("total_farm_accounts", tot, lambda v: v > 0, severity="P0", msg="Không đọc được danh sách tài khoản Farm (0 nick)!")
        run.check("critical_stale_accounts", crit, lambda v: v == 0, severity="P1", msg=f"Có {crit} tài khoản bị đóng băng > 14 ngày!")
        run.check("workbook_drift", len(drift_issues), lambda v: v == 0, severity="P1", msg=f"Có {len(drift_issues)} lỗi lệch dữ liệu Excel giữa Master và Tik1..8!")
        if f_cnt > 0:
            run.check("flop_accounts", f_cnt, lambda v: v == 0, severity="P1", msg=f"Có {f_cnt} kênh flop cần xoay nguồn cào!")

    msg = "\n".join(lines)
    if len(msg) > 3800:
        msg = msg[:3800] + "\n\n... (đã cắt ngắn để vừa giới hạn Telegram)"

    save_current_snapshot(PREV_SNAPSHOT_PATH, {
        "ref_date": ref_date,
        "tot": tot,
        "act": act,
        "zero": zero,
        "warn": warn,
        "crit": crit,
    })

    if run:
        run.set_report(msg)
        run.__exit__(None, None, None)
    elif crit > 0 or drift_issues or f_cnt > 0 or force:
        print(msg)
    sys.exit(0)


if __name__ == "__main__":
    main()
