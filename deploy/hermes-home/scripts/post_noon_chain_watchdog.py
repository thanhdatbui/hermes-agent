#!/usr/bin/env python3
"""
Event-driven Watchdog chạy chuỗi sau Ca trưa: Reg Gmail -> Add 2FA TikTok.
Bỏ hoàn toàn Phase Reg TikTok.
Khung giờ: 14:30 - 17:30 (HCM).
Điều kiện:
1. Đã hoàn thành Ca 2 (feed_session_reported.json có <today>_ca2 hoặc <today>_ca2_phien2).
2. Idle: Không có feed runner active, không có active device locks.
3. Idempotency: Chưa chạy hôm nay (state file).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

GMAIL_REPO_DIR = Path(os.environ.get("GMAIL_REPO_DIR", "D:/Taadaa/register gmail"))
TIKTOK_2FA_REPO_DIR = Path(os.environ.get("TIKTOK_2FA_REPO_DIR", "D:/Taadaa/tiktok-add-bao-mat-f2a"))
AUTOMATION_CORE_SRC = Path(os.environ.get("AUTOMATION_CORE_SRC", "D:/Taadaa/automation-core/src"))
STATE_DIR = Path("D:/Taadaa/runtime/kibe/cron-state")
STATE_FILE = STATE_DIR / "post_noon_chain_state.json"
REPORTED_FILE = STATE_DIR / "feed_session_reported.json"
LOCK_DIR = Path(r"C:\Users\Kibe\AppData\Local\automation-core\device-locks")
CODEX_LOCK_DIR = Path(r"C:\Users\Kibe\.codex\device-locks")

PYTHON_EXE = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
if not Path(PYTHON_EXE).exists():
    PYTHON_EXE = sys.executable

POWERSHELL_EXE = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def is_feed_runner_active() -> bool:
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            try:
                name = (p.info.get("name") or "").lower()
                if not name.startswith(("python", "powershell", "pwsh")):
                    continue
                cmd = " ".join(p.cmdline() or [])
                if "multi_machine_feed_session" in cmd or "run-feed-session.ps1" in cmd or "run_follow" in cmd:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def has_active_device_locks() -> bool:
    for ldir in (LOCK_DIR, CODEX_LOCK_DIR):
        if ldir.is_dir():
            for f in ldir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    # Coi la active neu status dang chay va owner van con song
                    if data.get("status") in ("active", "running", "queued"):
                        return True
                    # Status blocked nhung owner_active false (dead/finished) thi khong coi la active block
                    if data.get("status") == "blocked" and data.get("owner_active", True) is not False:
                        return True
                except Exception:
                    pass
            for f in ldir.glob("*.lock"):
                if f.is_file():
                    return True
    return False


def is_ca2_finished(today_str: str) -> bool:
    if not REPORTED_FILE.is_file():
        return False
    try:
        data = json.loads(REPORTED_FILE.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca2_phien2" in sessions or f"{today_str}_ca2" in sessions or f"{today_str}_ca2_phien3" in sessions
    except Exception:
        return False


def is_in_cooldown(threshold_minutes: int = 45) -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        last_run_str = data.get("last_run_at")
        if not last_run_str:
            return False
        last_run_dt = datetime.fromisoformat(last_run_str)
        now_dt = datetime.now(HCMC)
        elapsed_seconds = (now_dt - last_run_dt).total_seconds()
        return 0 <= elapsed_seconds < (threshold_minutes * 60)
    except Exception:
        return False


def already_ran_today(today_str: str) -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # Chỉ coi là đã hoàn tất trọn vẹn hôm nay nếu toàn bộ lane được yêu cầu thành công
        return data.get("last_success_date") == today_str and data.get("details", {}).get("lane_status") == "success"
    except Exception:
        return False


def save_state(today_str: str, details: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    existing_success = None
    if STATE_FILE.is_file():
        try:
            old_data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            existing_success = old_data.get("last_success_date")
        except Exception:
            pass
    # Chỉ ghi nhận last_success_date khi toàn bộ lane được yêu cầu thành công triệt để
    is_success = details.get("lane_status") == "success"
    new_success = today_str if is_success else existing_success
    payload = {
        "last_success_date": new_success,
        "last_run_at": datetime.now(HCMC).isoformat(),
        "details": details,
    }
    tmp = STATE_FILE.parent / f".post_noon_chain_state.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))


def run_gmail_batch(dry_run: bool = False) -> tuple[int, str]:
    if dry_run:
        return 0, "TOTAL=40 SUCCESS=40 FAILED=0 (dry-run)"
    ps_script = GMAIL_REPO_DIR / "run_all.ps1"
    if not ps_script.exists():
        return 1, f"Khong tim thay {ps_script}"
    cmd = [
        POWERSHELL_EXE,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", str(ps_script),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{GMAIL_REPO_DIR}{os.pathsep}{AUTOMATION_CORE_SRC}"
    env["GMAIL_REG_PYTHON_EXE"] = PYTHON_EXE
    try:
        proc = subprocess.run(cmd, cwd=str(GMAIL_REPO_DIR), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400)
        return proc.returncode, proc.stdout + "\n" + proc.stderr
    except Exception as exc:
        return 1, f"Loi chay Reg Gmail: {exc}"


def run_tiktok_2fa_batch(dry_run: bool = False) -> tuple[int, str]:
    if dry_run:
        return 0, "TOTAL=40 SUCCESS=40 FAILED=0 (dry-run Kibe + Admin)"
    runner_script = TIKTOK_2FA_REPO_DIR / "python_runner" / "run_batch_live_2fa.py"
    if not runner_script.exists():
        return 1, f"Khong tim thay {runner_script}"

    outputs = []
    kibe_code = 0
    admin_code = 0

    # 1. Cluster Kibe (Máy 1 - 80)
    cmd_kibe = [
        PYTHON_EXE,
        str(runner_script),
        "--workbook-path", r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx",
        "--workbook-sheet", "Tài Khoản",
        "--adb-path", r"C:\Program Files (x86)\xiaowei\tools\adb.exe",
        "--live",
        "--max-workers", "40",
    ]
    env_kibe = dict(os.environ)
    env_kibe["PYTHONPATH"] = f"{TIKTOK_2FA_REPO_DIR / 'python_runner'}{os.pathsep}{AUTOMATION_CORE_SRC}"
    env_kibe["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
    try:
        proc_kibe = subprocess.run(
            cmd_kibe,
            cwd=str(TIKTOK_2FA_REPO_DIR),
            env=env_kibe,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5400,
        )
        outputs.append(f"=== CLUSTER KIBE (MÁY 1-80) ===\n{proc_kibe.stdout}\n{proc_kibe.stderr}")
        kibe_code = proc_kibe.returncode
    except Exception as exc:
        outputs.append(f"Lỗi chạy Kibe 2FA: {exc}")
        kibe_code = 1

    # 2. Cluster Admin (Máy 201 - 280) via SSH admin-farm with EncodedCommand
    import base64
    ps_admin_script = (
        "$env:PYTHONIOENCODING = 'utf-8'\n"
        "$env:PYTHONUTF8 = '1'\n"
        "Set-Location 'D:/Taadaa/tiktok-add-bao-mat-f2a'\n"
        "$wb = 'D:\\OneDrive\\TaadaaData\\admin\\taikhoan_dat_v2_updated .xlsx'\n"
        "& 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' python_runner/run_batch_live_2fa.py "
        "--workbook-path $wb --max-workers 40 --live\n"
    )
    b64_ps = base64.b64encode(ps_admin_script.encode("utf-16le")).decode("ascii")
    cmd_admin = [
        "ssh", "-o", "ConnectTimeout=10", "admin-farm",
        f"powershell -NoProfile -EncodedCommand {b64_ps}"
    ]
    try:
        proc_admin = subprocess.run(
            cmd_admin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5400,
        )
        outputs.append(f"=== CLUSTER ADMIN (MÁY 201-280) ===\n{proc_admin.stdout}\n{proc_admin.stderr}")
        admin_code = proc_admin.returncode
    except Exception as exc:
        outputs.append(f"Lỗi chạy Admin 2FA: {exc}")
        admin_code = 1

    combined_code = 0 if (kibe_code in (0, 4) and admin_code in (0, 4)) else max(kibe_code, admin_code)
    return combined_code, "\n".join(outputs)


class SummaryResult(dict):
    def __iter__(self):
        return iter((self.get("total", 0), self.get("success", 0), self.get("failed", 0)))


def parse_chatgpt_warmup_counts(log_dir_hint: Path | None = None, min_mtime: float | None = None) -> tuple[int, int]:
    """Deprecated: ChatGPT registration on S7 has been disabled."""
    return 0, 0


def parse_summary_counts(output: str, log_dir_hint: Path | None = None, min_mtime: float | None = None) -> SummaryResult:
    # 1. Fallback đọc summary.json từ runtime logs (cho Reg Gmail - hỗ trợ UTF-8 BOM từ PowerShell)
    if log_dir_hint and log_dir_hint.is_dir():
        try:
            candidates = list(log_dir_hint.glob("logs_parallel_*/summary.json"))
            if min_mtime is not None:
                candidates = [p for p in candidates if p.stat().st_mtime >= min_mtime]
            if candidates:
                candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                data = json.loads(candidates[0].read_text(encoding="utf-8-sig"))
                return SummaryResult({
                    "total": int(data.get("total", 0)),
                    "success": int(data.get("success", 0)),
                    "failed": int(data.get("failed", 0)),
                    "skip_safe": int(data.get("skip_safe", 0) or 0),
                    "failure_breakdown": data.get("failure_breakdown") or {},
                })
        except Exception:
            pass

    # 2. Trích xuất chuẩn TOTAL=... SUCCESS=... FAILED=...
    m = re.search(r"TOTAL=(\d+)\s+SUCCESS=(\d+)\s+FAILED=(\d+)", output)
    if m:
        return SummaryResult({"total": int(m.group(1)), "success": int(m.group(2)), "failed": int(m.group(3)), "skip_safe": 0, "failure_breakdown": {}})

    # 3. Bóc tách bảng kết quả TikTok 2FA (machine | source_row | username | status | reason)
    # Loại trừ bảng 'Skip do device lock' in lặp ở cuối để tránh đếm trùng x2 các mục skipped
    table_section = output
    if "Skip do device lock" in output:
        table_section = output.split("Skip do device lock")[0]
    table_rows = re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", table_section, re.M)
    if table_rows:
        succs = sum(1 for r in table_rows if r[2].lower() == "success")
        fails = sum(1 for r in table_rows if r[2].lower() in ("failed", "fail", "error"))
        skips = sum(1 for r in table_rows if r[2].lower() in ("skipped", "skip"))
        tot = succs + fails + skips
        if tot > 0:
            return SummaryResult({"total": tot, "success": succs, "failed": fails, "skip_safe": skips, "failure_breakdown": {}})

    succs = len(re.findall(r"Machine\s+\d+.*(?:SUCCESS|OK)", output, re.I))
    fails = len(re.findall(r"Machine\s+\d+.*(?:FAIL|FAILED|ERROR)", output, re.I))
    return SummaryResult({"total": succs + fails, "success": succs, "failed": fails, "skip_safe": 0, "failure_breakdown": {}})


def main() -> int:
    parser = argparse.ArgumentParser(description="Post Noon Chain Watchdog (Reg Gmail -> Add 2FA TikTok)")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--force", action="store_true", help="Bypass time window and session checks")
    parser.add_argument("--lane", choices=("gmail", "tiktok", "all"), default="all", help="Run only the selected lane (default: all)")
    args = parser.parse_args()

    now = datetime.now(HCMC)
    today_str = now.strftime("%Y-%m-%d")

    # 1. Kiểm tra khung giờ: 14:30 - 18:30 (khoảng nghỉ trước Ca 3)
    in_window = (now.hour == 14 and now.minute >= 30) or (15 <= now.hour <= 18 and (now.hour < 18 or now.minute <= 30))
    if not in_window and not args.force and not args.dry_run:
        return 0

    # 2. Kiểm tra idempotency
    if already_ran_today(today_str) and not args.force:
        return 0

    # 2b. Kiểm tra cooldown 45 phút chống cron kích hoạt liên tiếp khi run vừa xong
    if is_in_cooldown(threshold_minutes=45) and not args.force and not args.dry_run:
        return 0

    # 3. Kiểm tra Ca 2 đã kết thúc
    if not is_ca2_finished(today_str) and not args.force and not args.dry_run:
        return 0

    # 4. Kiểm tra Idle
    if is_feed_runner_active() and not args.dry_run:
        return 0
    if has_active_device_locks() and not args.dry_run:
        return 0

    # BẮT ĐẦU CHUỖI
    start_dt = datetime.now(HCMC)
    start_epoch = start_dt.timestamp()
    sys.stderr.write(f"=== KÍCH HOẠT CHUỖI SAU CA TRƯA LÚC {start_dt.strftime('%H:%M:%S %d/%m/%Y')} ===\n")

    g_code, g_out = 0, ""
    g_tot = 0
    t2fa_code, t2fa_out = 0, ""

    # THIẾT KẾ ĐỘC LẬP (DECOUPLED):
    # Dù lane là all hay gmail/tiktok, Phase 2 (TikTok 2FA) KHÔNG BAO GIỜ bị chặn nếu Phase 1 (Reg Gmail) thất bại.
    g_duration_min = 0
    t2fa_duration_min = 0

    if args.lane in ("gmail", "all"):
        g_start = time.time()
        g_code, g_out = run_gmail_batch(dry_run=args.dry_run)
        g_duration_min = max(1, int((time.time() - g_start) // 60))

    if args.lane in ("tiktok", "all"):
        t_start = time.time()
        t2fa_code, t2fa_out = run_tiktok_2fa_batch(dry_run=args.dry_run)
        t2fa_duration_min = max(1, int((time.time() - t_start) // 60))

    end_dt = datetime.now(HCMC)
    duration_min = max(1, int((end_dt - start_dt).total_seconds() // 60))

    if args.lane == "all":
        lane_label = "ALL (GMAIL + TIKTOK 2FA)"
    elif args.lane == "gmail":
        lane_label = "GMAIL"
    else:
        lane_label = "TIKTOK 2FA"

    report_lines = [
        f"[BÁO CÁO CHUỖI SAU CA TRƯA] [LANE {lane_label}]",
        f"- Thời gian: {start_dt.strftime('%H:%M')} -> {end_dt.strftime('%H:%M')} ({duration_min} phút)",
        "",
    ]

    if args.lane in ("gmail", "all"):
        g_res = parse_summary_counts(
            g_out,
            log_dir_hint=Path("D:/CodexRuntime/codex_gmail_debug-register-gmail"),
            min_mtime=start_epoch
        )
        g_tot, g_suc = g_res["total"], g_res["success"]
        g_skip = g_res.get("skip_safe", 0)
        bk = g_res.get("failure_breakdown") or {}
        if "platform_errors" in bk or "script_errors" in bk:
            p_err = {k: v for k, v in bk.get("platform_errors", {}).items() if v > 0}
            s_err = {k: v for k, v in bk.get("script_errors", {}).items() if v > 0}
        else:
            p_err = {k: bk.get(k, 0) for k in ("phone_verify", "account_creation_error") if bk.get(k, 0) > 0}
            s_err = {k: bk.get(k, 0) for k in ("failed_cleanup", "failed_other") if bk.get(k, 0) > 0}
        p_cnt = sum(p_err.values())
        s_cnt = sum(s_err.values())
        p_str = f" ({p_cnt}): " + ", ".join(f"{k}: {v}" for k, v in p_err.items()) if p_cnt > 0 else ": 0"
        s_str = f" ({s_cnt}): " + ", ".join(f"{k}: {v}" for k, v in s_err.items()) if s_cnt > 0 else ": 0"

        if g_tot == 0 and g_code != 0:
            phase1_header = f"- Phase 1 (Reg Gmail - Code {g_code}): LỖI KHỞI ĐỘNG RUNNER"
        else:
            phase1_header = f"- Phase 1 (Reg Gmail - Code {g_code}):"
        report_lines.extend([
            phase1_header,
            f"  • Đã hoàn tất: {g_suc} máy",
        ])
        if g_skip > 0:
            report_lines.append(f"  • Bỏ qua an toàn: {g_skip} máy (đầy slot / nhường cron khác)")
        report_lines.append(f"  • Lỗi nền tảng{p_str}")
        report_lines.append(f"  • Lỗi script{s_str}")

    if args.lane in ("tiktok", "all"):
        if args.lane == "all":
            report_lines.append("")
        
        # Phân tách báo cáo chi tiết theo từng cụm Farm (Kibe vs Admin)
        if "=== CLUSTER ADMIN" in t2fa_out:
            parts = t2fa_out.split("=== CLUSTER ADMIN")
            kibe_text = parts[0]
            admin_text = "=== CLUSTER ADMIN" + parts[1]
            k_res = parse_summary_counts(kibe_text)
            a_res = parse_summary_counts(admin_text)

            phase2_header = f"- Phase 2 (Add 2FA TikTok - Code {t2fa_code}):"
            report_lines.extend([
                phase2_header,
                f"  • Farm Kibe (Máy 1-80): Hoàn tất {k_res['success']} máy | Bỏ qua {k_res.get('skip_safe', 0)} | Lỗi {k_res['failed']}",
                f"  • Farm Admin (Máy 201-280): Hoàn tất {a_res['success']} máy | Bỏ qua {a_res.get('skip_safe', 0)} | Lỗi {a_res['failed']}",
            ])
        else:
            t_res = parse_summary_counts(t2fa_out)
            t_tot, t_suc, t_fail = t_res["total"], t_res["success"], t_res["failed"]
            t_skip = t_res.get("skip_safe", 0)
            if t_tot == 0 and t2fa_code not in (0, 4):
                phase2_header = f"- Phase 2 (Add 2FA TikTok - Code {t2fa_code}): LỖI KHỞI ĐỘNG RUNNER"
            else:
                phase2_header = f"- Phase 2 (Add 2FA TikTok - Code {t2fa_code}):"
            report_lines.extend([
                phase2_header,
                f"  • Đã hoàn tất: {t_suc} máy",
            ])
            if t_skip > 0:
                report_lines.append(f"  • Bỏ qua an toàn: {t_skip} máy (nhường cron khác / đã có 2FA)")
            report_lines.append(f"  • Lỗi ({t_fail})" if t_fail > 0 else "  • Lỗi: 0")

    print("\n".join(report_lines))

    if not args.dry_run:
        gmail_ok = (g_code == 0) or (g_code == 1 and g_tot > 0)
        t2fa_ok = t2fa_code in (0, 4)
        save_state(today_str, {
            "gmail_code": g_code,
            "gmail_duration_min": g_duration_min,
            "2fa_code": t2fa_code,
            "2fa_duration_min": t2fa_duration_min,
            "lane": args.lane,
            "total_duration_min": duration_min,
            "gmail_status": "success" if gmail_ok else "failed",
            "2fa_status": "success" if t2fa_ok else "failed",
            "lane_status": "success" if (
                (gmail_ok if args.lane in ("gmail", "all") else True) and
                (t2fa_ok if args.lane in ("tiktok", "all") else True)
            ) else "failed",
        })

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
