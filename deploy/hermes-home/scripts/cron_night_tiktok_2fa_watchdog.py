#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Night Chain: Reg Gmail ban đêm -> Add 2FA TikTok, mỗi phase báo cáo Telegram riêng."""
from __future__ import annotations

import argparse
import base64
import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
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
if str(AUTOMATION_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_CORE_SRC))
WORKBOOK_PATH = Path(os.getenv("TAADAA_KIBE_WORKBOOK", r"D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx"))
ADB_PATH = Path(os.getenv("TAADAA_ADB_PATH", r"C:\Program Files (x86)\xiaowei\tools\adb.exe"))
HOST_CONFIG = Path(os.getenv("TAADAA_HOST_CONFIG_PATH", r"D:\Taadaa\machine-config\kibe.yaml"))
ADMIN_SSH_HOST = os.getenv("TAADAA_ADMIN_SSH", "admin-farm")
ADMIN_REPO_DIR = os.getenv("TAADAA_ADMIN_REPO", "D:/Taadaa/tiktok-add-bao-mat-f2a")
ADMIN_WORKBOOK = os.getenv("TAADAA_ADMIN_WORKBOOK", r"D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx")
ADMIN_PYTHON = os.getenv("TAADAA_ADMIN_PYTHON", r"D:\Taadaa\python-envs\automation\Scripts\python.exe")
GMAIL_REPO_DIR = Path(os.getenv("TAADAA_GMAIL_REPO", "D:/Taadaa/register gmail"))
GMAIL_LOG_DIR = Path("D:/CodexRuntime/codex_gmail_debug-register-gmail")
GMAIL_EXCEL_FILE = r"D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx"
PROXY_DIENTHOAI_PATH = r"D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"
POWERSHELL_EXE = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
GMAIL_REPORT_CHAT_ID = "-5139245637"
TIKTOK_REPORT_CHAT_ID = "-5468653590"

STATE_DIR = Path(os.getenv("TAADAA_CRON_STATE_DIR", "D:/Taadaa/runtime/kibe/cron-state"))
STATE_FILE = STATE_DIR / "night_tiktok_2fa_state.json"
REPORTED_FILE = Path(os.getenv("TAADAA_REPORTED_FILE", "D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json"))
LOCK_DIR = Path(r"C:\Users\Kibe\AppData\Local\automation-core\device-locks")
CODEX_LOCK_DIR = Path(r"C:\Users\Kibe\.codex\device-locks")
LANE_CLAIM_TTL_SECONDS = 5400


ROLLING_BLOCK_WINDOWS = (
    ("dọn cache", (4, 0), (4, 30)),
    ("ca nuôi sáng", (5, 5), (9, 30)),
    ("đệm ca trưa", (11, 5), (11, 35)),
    ("ca nuôi trưa", (11, 45), (15, 30)),
    ("đệm ca chiều", (17, 5), (17, 35)),
    ("ca nuôi chiều", (17, 45), (21, 30)),
)


def rolling_block_reason(now_dt: datetime) -> str | None:
    hm = (now_dt.hour, now_dt.minute)
    for label, start, end in ROLLING_BLOCK_WINDOWS:
        if start <= hm < end:
            return label
    return None


def is_safe_rolling_window(now_dt: datetime) -> bool:
    return rolling_block_reason(now_dt) is None


def is_clear_cache_active() -> bool:
    """Kiểm tra có tiến trình dọn dẹp cache TikTok đang chạy không."""
    try:
        import psutil
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or []).lower()
                if "clear-tiktok-cache" in cmd or "cron_clear_tiktok_cache" in cmd:
                    logger.info("Phát hiện tiến trình dọn cache đang chạy: %s", cmd[:80])
                    return True
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Lỗi kiểm tra cache cleaner: %s", exc)
    return False


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


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Lỗi đọc state file: %s", exc)
        return {}


@contextlib.contextmanager
def _state_lock(timeout: float = 30.0):
    """Khóa liên-tiến-trình quanh read-modify-write state để các lane không ghi đè nhau."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    win = sys.platform == "win32"
    if win:
        import msvcrt as lk
    else:
        import fcntl as lk
    deadline = time.monotonic() + timeout
    with open(STATE_DIR / ".night_tiktok_2fa_state.lock", "a+b") as fh:
        while True:
            try:
                fh.seek(0)
                lk.locking(fh.fileno(), lk.LK_NBLCK, 1) if win else lk.flock(fh.fileno(), lk.LOCK_EX | lk.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Không lấy được khóa state sau {timeout}s")
                time.sleep(0.1)
        try:
            yield
        finally:
            fh.seek(0)
            with contextlib.suppress(OSError):
                lk.locking(fh.fileno(), lk.LK_UNLCK, 1) if win else lk.flock(fh.fileno(), lk.LOCK_UN)


def already_ran_gmail_tonight(today_str: str) -> bool:
    state = load_state()
    return state.get("last_gmail_date") == today_str


def already_ran_today(today_str: str) -> bool:
    state = load_state()
    return bool(state.get("last_2fa_date") == today_str or state.get("last_success_date") == today_str)

already_ran_tiktok_today = already_ran_today


def _write_state(payload: dict) -> None:
    tmp = STATE_DIR / f".night_tiktok_2fa_state.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        for i in range(10):
            try:
                os.replace(tmp, STATE_FILE)
                break
            except PermissionError:
                if i == 9:
                    raise
                time.sleep(0.05)
    finally:
        tmp.unlink(missing_ok=True)


def _record_lane_state(lane: str, today_str: str, details: dict) -> None:
    with _state_lock():
        payload = load_state()
        is_succ = details.get("status") == "success"
        prev_details = payload.get("details", {}) if isinstance(payload.get("details"), dict) else {}
        payload.update({
            f"last_{lane}_date": today_str,
            f"last_{lane}_success": is_succ,
            f"last_{lane}_run_at": datetime.now(HCMC).isoformat(),
            "correlation_id": details.get("correlation_id", CORRELATION_ID),
            "details": {**prev_details, lane: details, **(details if lane == "2fa" else {})},
        })
        if lane == "2fa":
            payload["last_success_date"] = today_str if is_succ else None
        payload.pop(f"{lane}_running_since", None)
        if lane == "2fa":
            payload.pop("tiktok_running_since", None)
        elif lane == "tiktok":
            payload.pop("2fa_running_since", None)
        _write_state(payload)
    logger.info("Đã lưu state %s: status=%s, code=%s", lane, details.get("status"), details.get("code"))


def claim_lane(lane: str, today_str: str, force: bool = False) -> bool:
    with _state_lock():
        done = already_ran_gmail_tonight(today_str) if lane == "gmail" else already_ran_today(today_str)
        if done and not force:
            return False
        payload = load_state()
        started = payload.get(f"{lane}_running_since")
        if started is None:
            if lane == "2fa":
                started = payload.get("tiktok_running_since")
            elif lane == "tiktok":
                started = payload.get("2fa_running_since")
        now = time.time()
        if isinstance(started, (int, float)) and (now - started) < LANE_CLAIM_TTL_SECONDS:
            return False
        payload[f"{lane}_running_since"] = now
        _write_state(payload)
    return True


def release_lane(lane: str) -> None:
    try:
        with _state_lock():
            payload = load_state()
            payload.pop(f"{lane}_running_since", None)
            if lane == "2fa":
                payload.pop("tiktok_running_since", None)
            elif lane == "tiktok":
                payload.pop("2fa_running_since", None)
            _write_state(payload)
    except Exception as exc:
        logger.error("Không xóa được claim lane %s: %s", lane, exc)


def save_gmail_state(today_str: str, details: dict) -> None:
    _record_lane_state("gmail", today_str, details)


def save_state(today_str: str, details: dict) -> None:
    _record_lane_state("2fa", today_str, details)


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
        skip_m = re.search(r"SKIP_SAFE=(\d+)", output)
        skips = int(skip_m.group(1)) if skip_m else 0
        return {"total": int(m.group(1)), "success": int(m.group(2)), "failed": int(m.group(3)), "skip_safe": skips}

    succs = len(re.findall(r"Machine\s+\d+.*(?:SUCCESS|OK)", output, re.I))
    fails = len(re.findall(r"Machine\s+\d+.*(?:FAIL|FAILED|ERROR)", output, re.I))
    return {"total": succs + fails, "success": succs, "failed": fails, "skip_safe": 0}


def _ps_quote(value: object) -> str:
    return str(value).replace("'", "''")


def hydrate_workbook(path: Path) -> bool:
    """Hydrate và pin workbook nếu đang bị OneDrive Files On-Demand giữ offline."""
    try:
        if not path.is_file():
            logger.warning('Workbook không phải file thường: %s', path)
            return False
        if sys.platform == 'win32':
            result = subprocess.run(['attrib', '-u', '+p', str(path)], capture_output=True, timeout=10)
            if result.returncode != 0:
                logger.warning('Attrib hydrate thất bại (code=%d): %s', result.returncode, path)
                return False
        with open(path, 'rb') as f:
            f.read(10)
        return True
    except Exception as exc:
        logger.warning('Lỗi hydrate workbook %s: %s', path, exc)
    return False


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

    # Hydrate và pin Kibe workbook nếu đang bị OneDrive Files On-Demand giữ offline
    if not WORKBOOK_PATH.exists() or not hydrate_workbook(WORKBOOK_PATH):
        logger.error('Workbook %s không tồn tại hoặc không thể hydrate, dừng Cluster Kibe', WORKBOOK_PATH)
        kibe_code = 5
        outputs.append('=== CLUSTER KIBE (MÁY 1-80) ===\nBLOCKED: WORKBOOK_HYDRATION_FAILED')
    else:
        # 1. Cluster Kibe (Máy 1 - 80)
        cmd_kibe = [
            PYTHON_EXE,
            str(runner_script),
            "--workbook-path", str(WORKBOOK_PATH),
            "--workbook-sheet", "Tài Khoản",
            "--adb-path", str(ADB_PATH),
            "--live",
            "--max-workers", "15",
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
        "attrib -u +p $wb\n"
        "try { [System.IO.File]::ReadAllBytes($wb) | Out-Null } catch {}\n"
        f"& '{_ps_quote(ADMIN_PYTHON)}' python_runner/run_batch_live_2fa.py "
        "--workbook-path $wb --workbook-sheet 'Tài Khoản' --max-workers 15 --live\n"
        "exit $LASTEXITCODE\n"
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


def _admin_ssh_command(script_body: str) -> list[str]:
    encoded = base64.b64encode(script_body.encode("utf-16le")).decode("ascii")
    return ["ssh", "-o", "ConnectTimeout=10", ADMIN_SSH_HOST, f"powershell -NoProfile -EncodedCommand {encoded}"]


def _split_cluster_output(out: str) -> tuple[str, str]:
    parts = re.split(r"===\s*CLUSTER\s+ADMIN\b", out, maxsplit=1, flags=re.I)
    if len(parts) == 1:
        return out, ""
    return parts[0], "=== CLUSTER ADMIN" + parts[1]


def _run_cmd(label: str, cmd: list[str], **kw) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400, **kw)
        return p.returncode, f"=== {label} ===\n{p.stdout}\n{p.stderr}"
    except Exception as exc:
        return 2, f"=== {label} ===\nRUNNER_ERROR: {exc}"


def run_gmail_batch(dry_run: bool = False) -> tuple[int, str]:
    if dry_run:
        return run_night_batch(dry_run=True)
    ps_script = GMAIL_REPO_DIR / "run_all.ps1"
    if not ps_script.exists():
        return 1, f"Không tìm thấy {ps_script}"
    env = {**os.environ, "PYTHONPATH": f"{GMAIL_REPO_DIR}{os.pathsep}{AUTOMATION_CORE_SRC}", "GMAIL_REG_PYTHON_EXE": PYTHON_EXE}
    cmd = [POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ps_script)]
    kibe_code, kibe_out = _run_cmd("CLUSTER KIBE (MÁY 1-80)", cmd, cwd=str(GMAIL_REPO_DIR), env=env)
    admin_gmail_repo = r"D:\Taadaa\register gmail"
    admin_core_src = r"D:\Taadaa\automation-core\src"
    admin_manifest = r"C:\Users\Admin\AppData\Local\automation-core\assignments\register-gmail.json"
    ps_admin_script = (
        "$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'\n"
        f"Set-Location '{admin_gmail_repo}'\n"
        f"$env:PROXY_DIENTHOAI_PATH='{_ps_quote(PROXY_DIENTHOAI_PATH)}'\n"
        f"$env:GMAIL_EXCEL_FILE='{_ps_quote(GMAIL_EXCEL_FILE)}'\n"
        f"$env:PYTHONPATH='{admin_gmail_repo};{admin_core_src}'\n"
        f"$env:GMAIL_REG_PYTHON_EXE='{_ps_quote(ADMIN_PYTHON)}'\n"
        f"$env:GMAIL_ASSIGNMENT_MANIFEST='{admin_manifest}'\n"
        "$env:GMAIL_WORKER_ID='taadaa-writer-admin-farm'\n"
        f"& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File '{admin_gmail_repo}\\run_all.ps1'\n"
        "exit $LASTEXITCODE\n"
    )
    admin_code, admin_out = _run_cmd("CLUSTER ADMIN (MÁY 201-280)", _admin_ssh_command(ps_admin_script))
    return max(kibe_code, admin_code), f"{kibe_out}\n{admin_out}"


def _load_telegram_token() -> str | None:
    token = None
    try:
        from automation_core.alerts import _load_bot_token
        token = _load_bot_token()
    except Exception as exc:
        logger.warning("Không đọc được Telegram bot token từ automation_core: %s", exc)
    return token or os.getenv("TELEGRAM_BOT_TOKEN")


def send_telegram_report(chat_id: str, text: str) -> bool:
    token = _load_telegram_token()
    if not token:
        logger.warning("Không có Telegram bot token, bỏ qua báo cáo tới chat %s", chat_id)
        return False
    try:
        from automation_core.alerts import _send_telegram_text
        if _send_telegram_text(token, chat_id, text):
            return True
        logger.warning("automation_core _send_telegram_text thất bại, fallback urllib (chat %s)", chat_id)
    except Exception as exc:
        logger.warning("automation_core _send_telegram_text lỗi, fallback urllib: %s", exc)
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload)
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            status = resp.status
    except Exception as exc:
        logger.error("Gửi báo cáo Telegram tới chat %s thất bại: %s", chat_id, exc)
        return False
    if status != 200:
        logger.error("Telegram sendMessage tới chat %s trả HTTP %s", chat_id, status)
    return status == 200


def dispatch_report(chat_id: str, text: str, dry_run: bool) -> bool:
    if dry_run:
        print(text)
        return True
    if send_telegram_report(chat_id, text):
        return True
    logger.error("Gửi báo cáo tới chat %s thất bại, phase không được xác nhận đã báo cáo", chat_id)
    return False


def read_gmail_summary_json(min_mtime: float) -> dict | None:
    candidates = [p for p in GMAIL_LOG_DIR.glob("logs_parallel_*/summary.json") if p.stat().st_mtime >= min_mtime]
    if not candidates:
        return None
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    try:
        return json.loads(newest.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("Lỗi đọc summary Reg Gmail %s: %s", newest, exc)
        return None


def parse_gmail_breakdown_from_text(text: str) -> dict:
    pv = sum(int(x) for x in re.findall(r"PHONE_VERIFY=(\d+)", text))
    ace = sum(int(x) for x in re.findall(r"ACCOUNT_CREATION_ERROR=(\d+)", text))
    fc = sum(int(x) for x in re.findall(r"FAILED_CLEANUP=(\d+)", text))
    fo = sum(int(x) for x in re.findall(r"FAILED_OTHER=(\d+)", text))
    return {
        "platform_errors": {"phone_verify": pv, "account_creation_error": ace},
        "script_errors": {"failed_cleanup": fc, "failed_other": fo},
    }


def summarize_gmail(out: str, min_mtime: float) -> dict:
    kibe_text, admin_text = _split_cluster_output(out)
    data = read_gmail_summary_json(min_mtime) if GMAIL_LOG_DIR.is_dir() else None
    if data is not None:
        kibe = {k: int(data.get(k, 0) or 0) for k in ("total", "success", "failed", "skip_safe")}
        kibe_breakdown = data.get("failure_breakdown") or {}
    else:
        kibe = parse_summary_counts(kibe_text)
        kibe_breakdown = parse_gmail_breakdown_from_text(kibe_text)
    admin = parse_summary_counts(admin_text)
    admin_breakdown = parse_gmail_breakdown_from_text(admin_text)

    total_breakdown = {
        "platform_errors": {
            "phone_verify": (kibe_breakdown.get("platform_errors", {}).get("phone_verify", 0) +
                             admin_breakdown.get("platform_errors", {}).get("phone_verify", 0)),
            "account_creation_error": (kibe_breakdown.get("platform_errors", {}).get("account_creation_error", 0) +
                                       admin_breakdown.get("platform_errors", {}).get("account_creation_error", 0)),
        },
        "script_errors": {
            "failed_cleanup": (kibe_breakdown.get("script_errors", {}).get("failed_cleanup", 0) +
                               admin_breakdown.get("script_errors", {}).get("failed_cleanup", 0)),
            "failed_other": (kibe_breakdown.get("script_errors", {}).get("failed_other", 0) +
                             admin_breakdown.get("script_errors", {}).get("failed_other", 0)),
        },
    }
    total = {k: kibe.get(k, 0) + admin.get(k, 0) for k in ("total", "success", "failed", "skip_safe")}
    return {**total, "failure_breakdown": total_breakdown}


def _error_groups(breakdown: dict) -> tuple[dict, dict]:
    p = breakdown.get("platform_errors") or {k: breakdown.get(k, 0) for k in ("phone_verify", "account_creation_error")}
    s = breakdown.get("script_errors") or {k: breakdown.get(k, 0) for k in ("failed_cleanup", "failed_other")}
    return ({k: v for k, v in p.items() if v > 0}, {k: v for k, v in s.items() if v > 0})


def _format_error_group(group: dict) -> str:
    return f"{sum(group.values())} ({', '.join(f'{k}: {v}' for k, v in group.items())})" if group else "0"


def _get_shift_label(now_dt: datetime | None = None) -> str:
    if now_dt is None:
        now_dt = datetime.now(HCMC)
    h, m = now_dt.hour, now_dt.minute
    if 5 <= h < 11 or (h == 11 and m < 30):
        return "CA SÁNG"
    elif (h == 11 and m >= 30) or (12 <= h < 14):
        return "CA TRƯA"
    elif 14 <= h < 18:
        return "CA CHIỀU"
    elif 18 <= h < 22:
        return "CA TỐI"
    return "BAN ĐÊM"


def build_gmail_report(summary: dict, code: int) -> str:
    p, s = _error_groups(summary.get("failure_breakdown") or {})
    shift = _get_shift_label()
    lines = [
        f"⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO REG GMAIL {shift}:",
        f"• Đã hoàn tất: {summary['success']} máy", f"• Bỏ qua an toàn: {summary['skip_safe']} máy",
        f"• Lỗi nền tảng: {_format_error_group(p)}", f"• Lỗi script: {_format_error_group(s)}",
    ]
    if code != 0 and summary["total"] == 0: lines.append(f"• Lỗi runner: mã thoát {code}")
    return "\n".join(lines)


def build_2fa_report(kibe: dict, admin: dict, code: int) -> str:
    shift = _get_shift_label()
    lines = [
        f"⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO 2FA TIKTOK {shift}:",
        f"• Farm Kibe (Máy 1-80): Hoàn tất {kibe['success']} | Bỏ qua {kibe.get('skip_safe', 0)} | Lỗi {kibe['failed']}",
        f"• Farm Admin (Máy 201-280): Hoàn tất {admin['success']} | Bỏ qua {admin.get('skip_safe', 0)} | Lỗi {admin['failed']}",
    ]
    if code not in ACCEPTABLE_RETURN_CODES: lines.append(f"• Lỗi runner: mã thoát {code}")
    return "\n".join(lines)


def run_gmail_phase(today_str: str, dry_run: bool, force: bool) -> int:
    if not dry_run and not force and already_ran_gmail_tonight(today_str):
        logger.info("Reg Gmail đã hoàn tất hôm nay, bỏ qua")
        return 0
    start_epoch = datetime.now(HCMC).timestamp()
    code, out = run_gmail_batch(dry_run=dry_run)
    summary = summarize_gmail(out, min_mtime=start_epoch)
    if code != 0 or summary["failed"] > 0:
        status = "partial_failure" if (code in ACCEPTABLE_RETURN_CODES and summary["success"] > 0) else "failed"
    elif summary["success"] > 0 or summary["skip_safe"] > 0:
        status = "success"
    else:
        status = "failed"
    dispatch_report(GMAIL_REPORT_CHAT_ID, build_gmail_report(summary, code), dry_run)
    if not dry_run:
        save_gmail_state(today_str, {
            "correlation_id": CORRELATION_ID,
            "code": code,
            "status": status,
            "success_count": summary["success"],
            "failed_count": summary["failed"],
            "skip_count": summary["skip_safe"],
            "failure_breakdown": summary["failure_breakdown"],
        })
    return 0 if status == "success" else (code or 1)


def run_tiktok_phase(today_str: str, dry_run: bool, force: bool = False) -> int:
    if not dry_run and not force and already_ran_tiktok_today(today_str):
        logger.info("2FA TikTok đã chạy hôm nay (%s), bỏ qua; dùng --force để chạy lại", today_str)
        return 0
    code, out = run_night_batch(dry_run=dry_run)
    kibe_text, admin_text = _split_cluster_output(out)
    kibe, admin = parse_summary_counts(kibe_text), parse_summary_counts(admin_text)
    failed = kibe["failed"] + admin["failed"]
    acceptable = code in ACCEPTABLE_RETURN_CODES
    status = "failed" if not acceptable else ("partial_failure" if failed > 0 else "success")
    reason = None if status == "success" else (
        f"Runner exited with non-acceptable return code {code}" if not acceptable
        else f"{failed} target machines failed during 2FA execution"
    )
    dispatch_report(TIKTOK_REPORT_CHAT_ID, build_2fa_report(kibe, admin, code), dry_run)
    if not dry_run:
        save_state(today_str, {
            "correlation_id": CORRELATION_ID,
            "code": code,
            "status": status,
            "success_count": kibe["success"] + admin["success"],
            "failed_count": failed,
            "skip_count": kibe.get("skip_safe", 0) + admin.get("skip_safe", 0),
            "failure_reason": reason,
            "clusters": {"kibe": kibe, "admin": admin},
        })
    if not acceptable:
        logger.error("Ca 2FA ban đêm thất bại với code=%s", code)
        return code or 1
    if failed > 0:
        logger.warning("Ca 2FA ban đêm hoàn tất nhưng có %d máy lỗi", failed)
    return 0


def _handle_phase_crash(save, chat_id: str, title: str, today_str: str, dry_run: bool, exc: Exception) -> None:
    reason = f"Unhandled exception: {type(exc).__name__}: {exc}"
    shift = _get_shift_label()
    try:
        if not dry_run:
            save(today_str, {"correlation_id": CORRELATION_ID, "code": 1, "status": "failed", "failure_reason": reason})
        dispatch_report(chat_id, f"⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO {title} {shift}:\n• Lỗi runner: {reason}", dry_run)
    except Exception as inner:
        logger.error("Không xử lý được lỗi phase %s: %s", title, inner)


def main() -> int:
    parser = argparse.ArgumentParser(description="Night Chain Watchdog (Reg Gmail -> Add 2FA TikTok)")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--force", action="store_true", help="Bypass time window, idempotency and session checks")
    parser.add_argument("--lane", choices=("gmail", "tiktok", "all"), default="all", help="Run only the selected phase (default: all)")
    args = parser.parse_args()

    global CORRELATION_ID
    CORRELATION_ID = new_correlation_id()

    now = datetime.now(HCMC)
    today_str = now.strftime("%Y-%m-%d")

    if not is_safe_rolling_window(now) and not args.force and not args.dry_run:
        logger.info("Ngoài khung giờ an toàn (%s): %s", rolling_block_reason(now), now.strftime("%H:%M"))
        return 0

    if is_feed_runner_active() and not args.dry_run:
        logger.warning("Bỏ qua vì feed session đang hoạt động")
        return 0

    if is_clear_cache_active() and not args.dry_run:
        return 0

    logger.info("=== KÍCH HOẠT NIGHT CHAIN LÚC %s (lane=%s) ===", now.strftime("%H:%M:%S %d/%m/%Y"), args.lane)

    phases = (
        ("gmail", run_gmail_phase, save_gmail_state, GMAIL_REPORT_CHAT_ID, "REG GMAIL"),
        ("tiktok", run_tiktok_phase, save_state, TIKTOK_REPORT_CHAT_ID, "2FA TIKTOK"),
    )
    rcs = [0]
    for lane, run, save, chat_id, title in phases:
        if args.lane not in (lane, "all"):
            continue
        if not args.dry_run:
            try:
                claimed = claim_lane(lane, today_str, args.force)
            except Exception as exc:
                logger.error("Không claim được phase %s: %s", title, exc)
                rcs.append(1)
                continue
            if not claimed:
                logger.info("Phase %s đã hoàn tất hoặc đang chạy ở tiến trình khác, bỏ qua", title)
                continue
        try:
            rcs.append(run(today_str, dry_run=args.dry_run, force=args.force))
        except Exception as exc:
            logger.exception("Phase %s lỗi ngoài dự kiến: %s", title, exc)
            _handle_phase_crash(save, chat_id, title, today_str, args.dry_run, exc)
            rcs.append(1)
        finally:
            if not args.dry_run:
                release_lane(lane)
    return max(rcs)


if __name__ == "__main__":
    sys.exit(main())