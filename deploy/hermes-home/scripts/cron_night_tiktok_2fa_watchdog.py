#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Watchdog tự động bật 2FA TikTok ban đêm cho tài khoản thiếu 2FA sau Ca 4."""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

# Return code constants & safety policies
EXIT_SUCCESS = 0
EXIT_SAFE_SKIP = 4  # All targets skipped safely or already have 2FA
ACCEPTABLE_RETURN_CODES = (EXIT_SUCCESS, EXIT_SAFE_SKIP)

TIKTOK_2FA_REPO_DIR = Path(os.getenv("TAADAA_TIKTOK_2FA_REPO", "D:/Taadaa/tiktok-add-bao-mat-f2a"))
AUTOMATION_CORE_SRC = Path(os.getenv("TAADAA_AUTOMATION_CORE_SRC", "D:/Taadaa/automation-core/src"))
WORKBOOK_PATH = Path(os.getenv("TAADAA_KIBE_WORKBOOK", r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"))
ADB_PATH = Path(os.getenv("TAADAA_ADB_PATH", r"C:\Program Files (x86)\xiaowei\tools\adb.exe"))
HOST_CONFIG = Path(os.getenv("TAADAA_HOST_CONFIG_PATH", r"D:\Taadaa\machine-config\kibe.yaml"))
ADMIN_SSH_HOST = os.getenv("TAADAA_ADMIN_SSH", "admin-farm")
ADMIN_REPO_DIR = os.getenv("TAADAA_ADMIN_REPO", "D:/Taadaa/tiktok-add-bao-mat-f2a")
ADMIN_WORKBOOK = os.getenv("TAADAA_ADMIN_WORKBOOK", r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx")
ADMIN_PYTHON = os.getenv("TAADAA_ADMIN_PYTHON", r"D:\Taadaa\python-envs\automation\Scripts\python.exe")

STATE_DIR = Path(os.getenv("TAADAA_CRON_STATE_DIR", "D:/Taadaa/runtime/kibe/cron-state"))
STATE_FILE = STATE_DIR / "night_tiktok_2fa_state.json"
REPORTED_FILE = Path(os.getenv("TAADAA_REPORTED_FILE", "D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json"))
LOCK_DIR = Path(r"C:\Users\Kibe\AppData\Local\automation-core\device-locks")
CODEX_LOCK_DIR = Path(r"C:\Users\Kibe\.codex\device-locks")


def is_ca4_finished(today_str: str) -> bool:
    """Kiểm tra Ca 4 Phiên 2 đã hoàn tất và đã được Watchdog báo cáo hay chưa."""
    if not REPORTED_FILE.is_file():
        return False
    try:
        data = json.loads(REPORTED_FILE.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca4_phien2" in sessions or f"{today_str}_ca4" in sessions
    except Exception as exc:
        logger.warning("Lỗi kiểm tra trạng thái Ca 4: %s", exc)
        return False

PYTHON_EXE = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"
if not Path(PYTHON_EXE).exists():
    PYTHON_EXE = sys.executable

CORRELATION_ID = "-"


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = CORRELATION_ID
        return True


logger = logging.getLogger("night_tiktok_2fa_watchdog")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [cid=%(correlation_id)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    handler.addFilter(_CorrelationFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


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
                    logger.info("Phát hiện tiến trình feed đang chạy: %s", cmd[:80])
                    return True
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Lỗi kiểm tra feed runner: %s", exc)
    return False


def already_ran_today(today_str: str) -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("last_success_date") == today_str
    except Exception as exc:
        logger.warning("Lỗi đọc state file: %s", exc)
        return False


def save_state(today_str: str, details: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_success_date": today_str if details.get("status") == "success" else None,
        "last_run_at": datetime.now(HCMC).isoformat(),
        "correlation_id": details.get("correlation_id", CORRELATION_ID),
        "details": details,
    }
    tmp = STATE_FILE.parent / f".night_tiktok_2fa_state.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))
    logger.info("Đã lưu state: status=%s, code=%s, failure_reason=%s",
                details.get("status"), details.get("code"), details.get("failure_reason"))


def parse_summary_counts(output: str) -> dict:
    table_rows = re.findall(r"^\s*(\d+)\s*\|\s*(\d+)\s*\|\s*[^|]+\|\s*(\w+)", output, re.M)
    if table_rows:
        succs = sum(1 for r in table_rows if r[2].lower() == "success")
        fails = sum(1 for r in table_rows if r[2].lower() in ("failed", "fail", "error"))
        skips = sum(1 for r in table_rows if r[2].lower() in ("skipped", "skip"))
        tot = succs + fails + skips
        if tot > 0:
            return {"total": tot, "success": succs, "failed": fails, "skip_safe": skips}

    m = re.search(r"TOTAL=(\d+)\s+SUCCESS=(\d+)\s+FAILED=(\d+)", output)
    if m:
        return {"total": int(m.group(1)), "success": int(m.group(2)), "failed": int(m.group(3)), "skip_safe": 0}

    succs = len(re.findall(r"Machine\s+\d+.*(?:SUCCESS|OK)", output, re.I))
    fails = len(re.findall(r"Machine\s+\d+.*(?:FAIL|FAILED|ERROR)", output, re.I))
    return {"total": succs + fails, "success": succs, "failed": fails, "skip_safe": 0}


def _ps_quote(value: str) -> str:
    return str(value).replace("'", "''")


def run_night_batch(dry_run: bool = False) -> tuple[int, str]:
    if dry_run:
        logger.info("Chạy dry-run mode giả lập thành công")
        return EXIT_SUCCESS, "=== CLUSTER KIBE (MÁY 1-80) ===\nTOTAL=40 SUCCESS=40 FAILED=0\n=== CLUSTER ADMIN (MÁY 201-280) ===\nTOTAL=40 SUCCESS=40 FAILED=0"
    runner_script = TIKTOK_2FA_REPO_DIR / "python_runner" / "run_batch_live_2fa.py"
    if not runner_script.exists():
        err_msg = f"Không tìm thấy runner script tại {runner_script}"
        logger.error(err_msg)
        return 1, err_msg

    outputs = []
    kibe_code = EXIT_SUCCESS
    admin_code = EXIT_SUCCESS

    # 1. Cluster Kibe (Máy 1 - 80)
    cmd_kibe = [
        PYTHON_EXE,
        str(runner_script),
        "--workbook-path", str(WORKBOOK_PATH),
        "--workbook-sheet", "Tài Khoản",
        "--adb-path", str(ADB_PATH),
        "--live",
        "--max-workers", "40",
    ]
    env_kibe = dict(os.environ)
    env_kibe["PYTHONPATH"] = f"{TIKTOK_2FA_REPO_DIR / 'python_runner'}{os.pathsep}{AUTOMATION_CORE_SRC}"
    env_kibe["TAADAA_HOST_CONFIG"] = str(HOST_CONFIG)
    logger.info("Khởi chạy Cluster Kibe: %s", " ".join(cmd_kibe[:3]))
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
        logger.info("Cluster Kibe hoàn tất với returncode=%d", kibe_code)
    except Exception as exc:
        err_str = f"Lỗi chạy Kibe 2FA đêm: {exc}"
        logger.error(err_str)
        outputs.append(err_str)
        kibe_code = 1

    # 2. Cluster Admin (Máy 201 - 280) via SSH admin-farm
    ps_admin_script = (
        "$env:PYTHONIOENCODING = 'utf-8'\n"
        "$env:PYTHONUTF8 = '1'\n"
        f"Set-Location '{_ps_quote(ADMIN_REPO_DIR)}'\n"
        f"$wb = '{_ps_quote(ADMIN_WORKBOOK)}'\n"
        f"& '{_ps_quote(ADMIN_PYTHON)}' python_runner/run_batch_live_2fa.py "
        "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 40 --live\n"
    )
    b64_ps = base64.b64encode(ps_admin_script.encode("utf-16le")).decode("ascii")
    cmd_admin = [
        "ssh", "-o", "ConnectTimeout=10", ADMIN_SSH_HOST,
        f"powershell -NoProfile -EncodedCommand {b64_ps}"
    ]
    logger.info("Khởi chạy Cluster Admin via SSH %s powershell -EncodedCommand", ADMIN_SSH_HOST)
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
        logger.info("Cluster Admin hoàn tất với returncode=%d", admin_code)
    except Exception as exc:
        err_str = f"Lỗi chạy Admin 2FA đêm: {exc}"
        logger.error(err_str)
        outputs.append(err_str)
        admin_code = 1

    both_acceptable = (kibe_code in ACCEPTABLE_RETURN_CODES and admin_code in ACCEPTABLE_RETURN_CODES)
    if both_acceptable:
        # If any cluster returned safe skip (4) and none failed, return EXIT_SAFE_SKIP if all were 4, or EXIT_SUCCESS if at least one succeeded with 0
        combined_code = EXIT_SUCCESS if (kibe_code == EXIT_SUCCESS or admin_code == EXIT_SUCCESS) else EXIT_SAFE_SKIP
    else:
        combined_code = max(kibe_code, admin_code)

    return combined_code, "\n".join(outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Night TikTok 2FA Watchdog")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--force", action="store_true", help="Bypass time window and session checks")
    args = parser.parse_args()

    global CORRELATION_ID
    CORRELATION_ID = new_correlation_id()

    now = datetime.now(HCMC)
    today_str = now.strftime("%Y-%m-%d")

    # Khung giờ chạy đêm an toàn: 02:45 - 04:50 (sau khi Ca 4 Phiên 2 hoàn tất)
    in_window = (now.hour == 2 and now.minute >= 45) or (3 <= now.hour <= 4)
    if not in_window and not args.force and not args.dry_run:
        logger.info("Ngoài khung giờ chạy đêm an toàn (02:45 - 04:50): %s", now.strftime("%H:%M"))
        return 0

    if not is_ca4_finished(today_str) and not args.force and not args.dry_run:
        logger.info("Bỏ qua vì Ca 4 (Phiên 2) chưa hoàn tất báo cáo: %s", today_str)
        return 0

    if already_ran_today(today_str) and not args.force:
        logger.info("Đã chạy thành công trong ngày hôm nay: %s", today_str)
        return 0

    if is_feed_runner_active() and not args.dry_run:
        logger.warning("Bỏ qua ca đêm vì feed session đang hoạt động")
        return 0

    start_dt = datetime.now(HCMC)
    logger.info("=== KÍCH HOẠT 2FA TIKTOK BAN ĐÊM LÚC %s ===", start_dt.strftime("%H:%M:%S %d/%m/%Y"))

    code, out = run_night_batch(dry_run=args.dry_run)

    end_dt = datetime.now(HCMC)
    duration_min = max(1, int((end_dt - start_dt).total_seconds() // 60))

    header = f"[BÁO CÁO 2FA TIKTOK BAN ĐÊM] (Code {code}):" if code in ACCEPTABLE_RETURN_CODES else f"[BÁO CÁO 2FA TIKTOK BAN ĐÊM - LỖI RUNNER] (Code {code}):"
    report_lines = [
        header,
        f"- Correlation ID: {CORRELATION_ID}",
        f"- Thời gian: {start_dt.strftime('%H:%M')} -> {end_dt.strftime('%H:%M')} ({duration_min} phút)",
    ]

    cluster_details = {}
    if "=== CLUSTER ADMIN" in out:
        parts = out.split("=== CLUSTER ADMIN")
        kibe_text = parts[0]
        admin_text = "=== CLUSTER ADMIN" + parts[1]
        k_res = parse_summary_counts(kibe_text)
        a_res = parse_summary_counts(admin_text)
        suc = k_res["success"] + a_res["success"]
        fail = k_res["failed"] + a_res["failed"]
        skip = k_res.get("skip_safe", 0) + a_res.get("skip_safe", 0)
        cluster_details = {
            "kibe": k_res,
            "admin": a_res,
        }
        report_lines.extend([
            f"- Farm Kibe (Máy 1-80): Hoàn tất {k_res['success']} máy | Bỏ qua {k_res.get('skip_safe', 0)} | Lỗi {k_res['failed']}",
            f"- Farm Admin (Máy 201-280): Hoàn tất {a_res['success']} máy | Bỏ qua {a_res.get('skip_safe', 0)} | Lỗi {a_res['failed']}",
        ])
    else:
        res = parse_summary_counts(out)
        tot, suc, fail = res["total"], res["success"], res["failed"]
        skip = res.get("skip_safe", 0)
        cluster_details = {"single": res}
        report_lines.append(f"- Đã hoàn tất: {suc} máy")
        if skip > 0:
            report_lines.append(f"- Bỏ qua an toàn: {skip} máy (đã có 2FA / nhường cron khác)")
        report_lines.append(f"- Lỗi ({fail})" if fail > 0 else "- Lỗi: 0")

    print("\n".join(report_lines))

    failure_reason = None
    if code not in ACCEPTABLE_RETURN_CODES:
        failure_reason = f"Runner exited with non-acceptable return code {code}"
    elif fail > 0:
        failure_reason = f"{fail} target machines failed during 2FA execution"

    if not args.dry_run:
        save_state(today_str, {
            "correlation_id": CORRELATION_ID,
            "code": code,
            "status": "success" if (code in ACCEPTABLE_RETURN_CODES and fail == 0) else ("partial_failure" if code in ACCEPTABLE_RETURN_CODES else "failed"),
            "success_count": suc,
            "failed_count": fail,
            "skip_count": skip,
            "failure_reason": failure_reason,
            "clusters": cluster_details,
        })

    if code not in ACCEPTABLE_RETURN_CODES:
        logger.error("Ca 2FA ban đêm thất bại với code=%s", code)
        return code if code != 0 else 1
    if fail > 0:
        logger.warning("Ca 2FA ban đêm hoàn tất nhưng có %d máy lỗi", fail)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
