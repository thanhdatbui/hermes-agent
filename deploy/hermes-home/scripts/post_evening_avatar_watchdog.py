"""
Watchdog cuốn chiếu: Tự động chạy upload Avatar cho các acc CHƯA BAO GIỜ ĐƯỢC UP
ngay sau ca tối (khung giờ 21:00 -> 23:45) và CHỈ BÁO CÁO KHI CHẠY XONG vào Farm Alert.

Kênh Farm Alert: Telegram chat_id = -5373649734

Nguyên tắc:
- Quét các workbook theo host_id (admin vs kibe).
- Lọc chính xác các máy mà cột Avatar != 'OK' (chưa bao giờ được up).
- Sau khi kích hoạt batch -> Chạy ngầm im lặng, không spam lúc bắt đầu.
- IM LẶNG hoàn toàn sau mỗi batch lẻ.
- CHỈ BÁO CÁO 1 LẦN DUY NHẤT khi tất cả các Tik hoàn tất 100% HOẶC hết khung giờ ca tối (sau 23:30).
"""
from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request
import urllib.parse
try:
    import psutil
except ImportError:  # pragma: no cover - optional on stripped-down test hosts
    psutil = None
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger("post_evening_avatar_watchdog")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("[%(asctime)s][%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

FARM_ALERT_CHAT_ID = "-5435853713"  # Nhóm Telegram: Tiktok video
LAUNCHER = Path(r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1")
TIKTOK_VIDEO_DIR = Path(r"D:\Taadaa\Tiktok-video")
BATCH_RUNS_DIR = Path(r"D:\CodexRuntime\tiktok-video\batch-runs")
LOCK_DIR = Path(os.path.expanduser("~/.codex/device-locks"))
ADMIN_ADB_SOCKET = os.environ.get("TAADAA_ADMIN_ADB_SOCKET", "tcp:192.168.110.119:5037")
ADMIN_HOST_CONFIG = Path(os.environ.get("TAADAA_ADMIN_HOST_CONFIG", r"D:\Taadaa\machine-config\admin.yaml"))


def get_host_context(config_path_override: str | Path | None = None) -> dict:
    """Xác định host context (host_id, target_tiks, workbook_dir, state_file) từ config hoặc fallback kibe."""
    if config_path_override:
        cfg_path = Path(config_path_override)
    else:
        env_cfg = os.environ.get("TAADAA_HOST_CONFIG")
        if env_cfg:
            cfg_path = Path(env_cfg)
        else:
            cfg_path = Path(r"D:\Taadaa\machine-config\kibe.yaml")

    host_id = "kibe"
    if cfg_path.exists():
        try:
            try:
                import yaml
                data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("host_id"):
                    host_id = str(data["host_id"]).strip().lower()
            except Exception:
                for line in cfg_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("host_id:"):
                        host_id = line.split(":", 1)[1].strip().strip('"').strip("'").lower()
                        break
        except Exception:
            pass

    if host_id == "admin":
        target_tiks = [1, 2, 3, 4, 5, 6, 7, 8]
        workbook_dir = Path(r"D:\OneDrive\TaadaaData\admin")
        state_file = Path(r"D:\Taadaa\runtime\admin\cron-state\post_evening_avatar_state.json")
    else:
        host_id = "kibe"
        target_tiks = [5, 6, 7, 8, 3, 4]
        if cfg_path.exists():
            try:
                import yaml
                data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                if "target_tiks" in data:
                    target_tiks = list(data["target_tiks"])
            except Exception:
                pass
        workbook_dir = Path(r"D:\OneDrive\TaadaaData\kibe")
        state_file = Path("D:/Taadaa/runtime/kibe/cron-state/post_evening_avatar_state.json")

    return {
        "host_id": host_id,
        "host_config_path": cfg_path,
        "target_tiks": target_tiks,
        "workbook_dir": workbook_dir,
        "state_file": state_file,
    }


# Khởi tạo mặc định theo môi trường hiện tại
HOST_CONTEXT = get_host_context()
HOST_ID = HOST_CONTEXT["host_id"]
TARGET_TIKS = HOST_CONTEXT["target_tiks"]
WORKBOOK_DIR = HOST_CONTEXT["workbook_dir"]
STATE_FILE = HOST_CONTEXT["state_file"]
HOST_CONFIG = HOST_CONTEXT["host_config_path"]


def now_hcmc() -> datetime:
    return datetime.now(HCMC)


def get_session_key(now_dt: datetime) -> str:
    """Xác định session date (nếu chạy qua đêm 00:00 -> 05:00 vẫn tính là ca tối ngày hôm trước)."""
    prefix = "morning" if 6 <= now_dt.hour < 14 else "evening"
    date_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d") if now_dt.hour < 6 else now_dt.strftime("%Y-%m-%d")
    return f"{date_str}_{prefix}"


def get_telegram_bot_token() -> str | None:
    """Lấy Telegram Bot Token từ env hoặc file .env của Hermes."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token
    env_file = Path.home() / "AppData/Local/hermes/.env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None


def send_farm_alert(text: str) -> bool:
    """Gửi tin nhắn thông báo vào nhóm Farm Alert."""
    token = get_telegram_bot_token()
    if not token:
        print("[ALERT] Không tìm thấy TELEGRAM_BOT_TOKEN, in console:")
        print(text)
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": FARM_ALERT_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        data = urllib.parse.urlencode(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        sys.stderr.write(f"send_farm_alert error: {e}\n")
        return False


def is_post_evening_window(now_dt: datetime) -> bool:
    """Mở cuốn chiếu liên tục né giờ nuôi (05:15-09:30, 11:45-15:30, 17:45-21:30) và dọn cache (04:00-04:30)."""
    h, m = now_dt.hour, now_dt.minute
    if (h == 5 and m >= 15) or h in (6, 7, 8) or (h == 9 and m < 30): return False
    if (h == 11 and m >= 45) or h in (12, 13, 14) or (h == 15 and m < 30): return False
    if (h == 17 and m >= 45) or h in (18, 19, 20) or (h == 21 and m < 30): return False
    return not (h == 4 and m < 30)


def is_after_evening_window(now_dt: datetime) -> bool:
    """Mốc báo cáo định kỳ mỗi 6H (00:00, 06:00, 12:00, 18:00)."""
    return now_dt.hour in (0, 6, 12, 18) and now_dt.minute < 30


def count_active_locks() -> int:
    """Đếm số device locks còn fresh (< 45 phút / 2700s) và active/running/queued/queued_v2."""
    lock_dirs = [
        LOCK_DIR,
        Path(os.path.expanduser(r"~\AppData\Local\automation-core\device-locks")),
    ]
    cur_time = time.time()
    count = 0
    seen_files: set[str] = set()
    for ldir in lock_dirs:
        if not ldir.exists():
            continue
        try:
            for f in ldir.iterdir():
                if f.name in seen_files:
                    continue
                if f.is_file() and f.suffix == ".json" and (
                    f.name.startswith("machine_") or f.name.startswith("serial_")
                ):
                    try:
                        if (cur_time - f.stat().st_mtime) < 2700:
                            data = json.loads(f.read_text(encoding="utf-8"))
                            st = data.get("status")
                            if st in ("active", "running", "queued", "queued_v2") or (st == "blocked" and data.get("owner_active", True) is not False):
                                seen_files.add(f.name)
                                count += 1
                    except Exception:
                        pass
        except Exception:
            pass
    return count
def is_feed_session_finished_for_window(now_dt: datetime) -> bool:
    today_str = now_dt.strftime("%Y-%m-%d")
    yesterday_str = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    reported_file = Path("D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json")
    if not reported_file.is_file():
        return False
    try:
        data = json.loads(reported_file.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        if 0 <= now_dt.hour < 6:
            return f"{yesterday_str}_ca3_phien2" in sessions or f"{yesterday_str}_ca3" in sessions
        if 6 <= now_dt.hour < 14:
            return f"{today_str}_ca1_phien2" in sessions or f"{today_str}_ca1" in sessions
        return f"{today_str}_ca3_phien2" in sessions or f"{today_str}_ca3" in sessions
    except Exception:
        return False


def is_feed_active() -> bool:
    """Kiểm tra có feed runner nào đang chạy không."""
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process '
            '-Filter "Name like \'python%\' or Name like \'powershell%\'" '
            '| Select-Object -ExpandProperty CommandLine'
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        cmdlines = p.stdout.lower()
        signatures = [
            "run-feed-session.ps1",
            "multi_machine_feed_session",
            "run_tiktok.py",
            "night_chain_reg_pipeline"
        ]
        for sig in signatures:
            if sig in cmdlines:
                return True
    except Exception:
        pass
    return False


def is_clear_cache_active() -> bool:
    """Kiểm tra có tiến trình dọn dẹp cache TikTok đang chạy không."""
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process '
            '-Filter "Name like \'python%\'" '
            '| Select-Object -ExpandProperty CommandLine'
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        cmdlines = p.stdout.lower()
        return "clear-tiktok-cache" in cmdlines or "cron_clear_tiktok_cache" in cmdlines
    except Exception:
        return False


def rescan_completed_machines(machines: list[int] | None = None, timeout_seconds: int = 180) -> bool:
    """Gọi tiktok_account_tracker.py cập nhật snapshot DB cho các máy vừa chạy xong."""
    tracker_script = Path(r"D:\Taadaa\tools\tiktok_account_tracker.py")
    if not tracker_script.exists():
        sys.stderr.write(f"Tracker script not found: {tracker_script}\n")
        return False

    py_exe = Path(r"D:\Taadaa\python-envs\automation\Scripts\python.exe")
    python_bin = str(py_exe) if py_exe.exists() else sys.executable

    cmd = [python_bin, str(tracker_script)]
    machine_count = 0
    if machines:
        unique_machines = sorted(list(set(machines)))
        cmd.extend(["--machines", ",".join(str(m) for m in unique_machines), "--workers", "10"])
        machine_count = len(unique_machines)

    start_time = time.time()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        elapsed = time.time() - start_time
        stdout_clean = (res.stdout or "").strip()
        stderr_clean = (res.stderr or "").strip()

        if res.returncode == 0:
            target_desc = f"{machine_count} máy" if machine_count > 0 else "toàn bộ"
            logger.info(f"[TRACKER RESCAN] Hoàn tất cập nhật DB cho {target_desc} (exit: 0, duration: {elapsed:.2f}s).")
            # Rescan thành công: IM LẶNG hoàn toàn trên stdout theo đúng nguyên tắc watchdog (tránh cron spam Telegram)
            return True
        else:
            err_msg = (
                f"[TRACKER RESCAN] Error (exit {res.returncode}, duration: {elapsed:.2f}s)\n"
                f"[TRACKER RESCAN stderr]:\n{stderr_clean or '<empty>'}"
            )
            logger.error(err_msg)
            return False
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TRACKER RESCAN] Failed to run rescan after {elapsed:.2f}s: {e}")
        return False


def ensure_avatar_replace_queue_schema(conn: sqlite3.Connection) -> None:
    """Đảm bảo bảng avatar_replace_queue tồn tại và tự động migrate cột thiếu nếu cần."""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS avatar_replace_queue (
        username TEXT,
        may INTEGER,
        tik INTEGER,
        host_id TEXT,
        folder_video TEXT,
        video_goc TEXT,
        status TEXT DEFAULT 'PENDING',
        last_error TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')),
        PRIMARY KEY (username, tik, host_id)
    )
    """)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(avatar_replace_queue)")
    existing_cols = {row[1].lower() for row in cur.fetchall()}
    col_defs = {
        "may": "INTEGER",
        "tik": "INTEGER",
        "host_id": "TEXT",
        "folder_video": "TEXT",
        "video_goc": "TEXT",
        "status": "TEXT DEFAULT 'PENDING'",
        "last_error": "TEXT",
        "created_at": "TEXT DEFAULT (datetime('now', 'localtime'))",
        "updated_at": "TEXT DEFAULT (datetime('now', 'localtime'))",
    }
    for col, col_def in col_defs.items():
        if col not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE avatar_replace_queue ADD COLUMN {col} {col_def}")
            except Exception as e:
                logger.warning(f"[SCHEMA_MIGRATION_WARN] Failed adding column {col}: {e}")


def get_tik_avatar_stats(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> dict:
    """Lấy danh sách máy chưa có avatar từ SQLite database tiktok_tracker.db có lọc theo host_id.
    Fallback đọc Excel workbook nếu SQLite database lỗi hoặc không mở được.
    """
    ctx = host_context or get_host_context()
    host_id = ctx.get("host_id", "kibe").lower()
    db_path = Path(ctx.get("db_path", r"D:\Taadaa\data\tiktok_tracker.db"))

    if db_path.exists():
        try:
            if host_id == "admin":
                query = """
                WITH Ranked AS (
                    SELECT s.username, s.status, s.has_avatar,
                           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
                    FROM snapshots s
                )
                SELECT m.may, r.has_avatar, r.status, q.status AS queue_status
                FROM farm_account_info m
                LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
                LEFT JOIN avatar_replace_queue q ON m.username = q.username AND m.may = q.may AND m.tik = q.tik
                WHERE m.tik = ? AND (m.host_id = ? OR m.may >= ?)
                ORDER BY m.may
                """
                params = (tik, "admin", 200)
            else:
                query = """
                WITH Ranked AS (
                    SELECT s.username, s.status, s.has_avatar,
                           ROW_NUMBER() OVER (PARTITION BY s.username ORDER BY s.id DESC) as rn
                    FROM snapshots s
                )
                SELECT m.may, r.has_avatar, r.status, q.status AS queue_status
                FROM farm_account_info m
                LEFT JOIN Ranked r ON m.username = r.username AND r.rn = 1
                LEFT JOIN avatar_replace_queue q ON m.username = q.username AND m.may = q.may AND m.tik = q.tik
                WHERE m.tik = ? AND (m.host_id = ? OR m.host_id IS NULL OR m.host_id = ?) AND m.may < ?
                ORDER BY m.may
                """
                params = (tik, "kibe", "", 200)

            with sqlite3.connect(str(db_path), timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='avatar_replace_queue'")
                if not cursor.fetchone():
                    ensure_avatar_replace_queue_schema(conn)
                cursor.execute(query, params)
                rows = cursor.fetchall()

            if rows:
                unuploaded = []
                uploaded_count = 0
                for may, has_avatar, _st, queue_status in rows:
                    if queue_status == "PENDING":
                        unuploaded.append(may)
                    elif queue_status == "DONE":
                        uploaded_count += 1
                    elif has_avatar == 1:
                        uploaded_count += 1
                    else:
                        unuploaded.append(may)
                return {
                    "unuploaded": sorted(list(set(unuploaded))),
                    "uploaded_count": uploaded_count,
                    "total_accounts": len(rows),
                }
        except Exception as e:
            sys.stderr.write(f"Error querying tiktok_tracker.db for Tik {tik}: {e}\n")

    wb_base = workbook_dir or ctx.get("workbook_dir") or WORKBOOK_DIR
    fn = f"Tik{tik}.xlsx" if tik != 3 else "tik3.xlsx"
    wb_path = wb_base / fn
    if not wb_path.exists():
        return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}

    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(wb_path), data_only=True, read_only=True)
        ws = wb["TaiKhoan"] if "TaiKhoan" in wb.sheetnames else wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}

        header = [str(c or "").strip().lower() for c in rows[0]]
        id_col = -1
        ava_col = -1
        for idx, h in enumerate(header):
            if h in ("id", "id tiktok", "tiktok id"):
                id_col = idx
            if "avatar" in h:
                ava_col = idx

        if id_col == -1:
            id_col = 2

        unuploaded = []
        uploaded_count = 0
        total_accounts = 0
        for r in rows[1:]:
            m_val = r[0]
            if m_val is None:
                continue
            try:
                m_int = int(m_val)
            except (ValueError, TypeError):
                continue

            nick = r[id_col] if id_col < len(r) else None
            if not nick or str(nick).strip().lower() in ("none", "null", "", "0", "missing_id"):
                continue

            total_accounts += 1
            ava = r[ava_col] if (ava_col != -1 and ava_col < len(r)) else None
            if ava and str(ava).strip().lower() in ("ok", "present", "true", "done", "yes"):
                uploaded_count += 1
            else:
                unuploaded.append(m_int)

        wb.close()
        return {
            "unuploaded": sorted(list(set(unuploaded))),
            "uploaded_count": uploaded_count,
            "total_accounts": total_accounts
        }
    except Exception as e:
        sys.stderr.write(f"Error reading {fn}: {e}\n")
        return {"unuploaded": [], "uploaded_count": 0, "total_accounts": 0}


def get_unuploaded_machines(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> list[int]:
    return get_tik_avatar_stats(tik, workbook_dir=workbook_dir, host_context=host_context)["unuploaded"]


def get_tik_avatar_status(
    tik: int,
    workbook_dir: Path | None = None,
    host_context: dict | None = None,
) -> tuple[int, list[int]]:
    st = get_tik_avatar_stats(tik, workbook_dir=workbook_dir, host_context=host_context)
    return st["total_accounts"], st["unuploaded"]


def is_cluster_batch_alive(cluster_id: str, pid: int | None = None) -> bool:
    """Kiểm tra batch upload avatar đang chạy cho riêng một cluster."""
    if pid and psutil is not None:
        try:
            if psutil.pid_exists(int(pid)):
                return True
        except (TypeError, ValueError, OSError):
            pass
    try:
        ps_cmd = (
            'Get-CimInstance Win32_Process '
            '-Filter "Name like \'powershell%\'" '
            '| Select-Object -ExpandProperty CommandLine'
        )
        p = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=15,
        )
        cluster_id = str(cluster_id).lower()
        for line in (p.stdout or "").splitlines():
            cmdline = line.lower()
            if "run_tiktok_upload_avatar.ps1" not in cmdline and "run_tiktok_upload_batch.ps1" not in cmdline:
                continue
            if cluster_id == "admin" and "admin.yaml" in cmdline:
                return True
            if cluster_id == "kibe" and "admin.yaml" not in cmdline:
                return True
    except Exception:
        return False
    return False


def is_powershell_batch_alive(cluster_id: str | None = None) -> bool:
    """Backward-compatible wrapper for one cluster or any avatar batch."""
    if cluster_id:
        return is_cluster_batch_alive(cluster_id)
    return any(is_cluster_batch_alive(cid) for cid in ("kibe", "admin"))


def get_state(state_file: Path | None = None) -> dict:
    target_file = state_file or STATE_FILE
    if target_file.exists():
        try:
            return json.loads(target_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"running_batch": None, "running_batches": {}}


def save_state(st: dict, state_file: Path | None = None):
    target_file = state_file or STATE_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target_file)


def collect_recent_batch_results(
    tik: int,
    machines: list[int] | None = None,
    batch_runs_dir: Path | None = None,
) -> tuple[list[int], dict[str, list[int]]]:
    base_dir = batch_runs_dir or Path(r"D:\CodexRuntime\tiktok-video\batch-runs")
    if not base_dir.exists():
        return [], {}
    pattern = f"batch_tik{tik}_*"
    try:
        matching_dirs = sorted(base_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    except Exception:
        return [], {}
    if not matching_dirs:
        return [], {}
    target_set = set(machines) if machines else None
    summary_file = None
    for candidate_dir in matching_dirs:
        candidate = candidate_dir / "summary.csv"
        if not candidate.exists():
            continue
        if target_set is None:
            summary_file = candidate
            break
        try:
            with open(candidate, mode="r", encoding="utf-8-sig") as f:
                found = set()
                for row in csv.DictReader(f):
                    value = row.get("Machine") or row.get("machine_id") or row.get("may")
                    if value and str(value).strip().lstrip("-").isdigit():
                        found.add(int(value))
            if found & target_set:
                summary_file = candidate
                break
        except (OSError, ValueError, TypeError):
            continue
    if summary_file is None:
        return [], {}
    succeeded = []
    failed_by_reason = {}
    try:
        with open(summary_file, mode="r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                m_val = row.get("Machine") or row.get("machine_id") or row.get("may")
                if not m_val: continue
                try: m = int(m_val)
                except Exception: continue
                if target_set is not None and m not in target_set: continue
                status = (row.get("Status") or "").strip()
                verified = (row.get("Verified") or "").strip().lower() == "true"
                reason_raw = (row.get("Reason") or "").strip()
                report_path = (row.get("Report") or "").strip()
                if verified or status in ("AVATAR_SMOKE_SUCCESS", "SUCCESS") or reason_raw in ("AVATAR_SMOKE_SUCCESS", "SUCCESS"):
                    succeeded.append(m)
                    continue
                err_code = ""
                if report_path and Path(report_path).exists():
                    try:
                        with open(report_path, mode="r", encoding="utf-8") as rf:
                            rd = json.load(rf)
                            err_msg = rd.get("error") or rd.get("avatar_error") or ""
                            mm = re.search(r"\[([A-Z0-9_]+)\]", str(err_msg))
                            if mm: err_code = mm.group(1)
                    except (json.JSONDecodeError, OSError) as e:
                        logger.debug("Cannot parse report json %s: %s", report_path, e)
                if not err_code:
                    mm = re.search(r"\[([A-Z0-9_]+)\]", reason_raw)
                    if mm:
                        err_code = mm.group(1)
                    elif reason_raw:
                        err_code = reason_raw
                    elif status:
                        err_code = status
                    else:
                        err_code = "UNKNOWN_ERROR"
                failed_by_reason.setdefault(err_code, []).append(m)
    except Exception as e:
        logger.warning(f"[WATCHDOG] Error reading batch summary: {e}")
    for k in failed_by_reason:
        failed_by_reason[k] = sorted(list(set(failed_by_reason[k])))
    succeeded_sorted = sorted(list(set(succeeded)))
    logger.info(
        "[WATCHDOG] Batch Tik %s telemetry: succeeded=%d, failed=%d, reasons=%s",
        tik,
        len(succeeded_sorted),
        sum(len(m) for m in failed_by_reason.values()),
        failed_by_reason,
    )
    return succeeded_sorted, failed_by_reason

def check_batch_status(state: dict, state_file: Path | None = None, cluster_id: str | None = None) -> bool:
    """Dọn batch đã xong theo cluster; True khi mọi batch được kiểm tra vẫn bận."""
    running_batches = state.get("running_batches") or {}
    if not running_batches and state.get("running_batch"):
        legacy = state["running_batch"]
        legacy_cluster = legacy.get("host_id", "kibe")
        running_batches = {legacy_cluster: legacy}
        state["running_batches"] = running_batches
    selected = [cluster_id] if cluster_id else list(running_batches)
    if not selected:
        return False
    all_alive = True
    for cid in selected:
        running = running_batches.get(cid)
        if not running:
            all_alive = False
            continue
        start_time = running.get("start_time", 0)
        if is_cluster_batch_alive(cid, pid=running.get("pid")) and (time.time() - start_time) < 2700:
            continue
        all_alive = False
        completed_machines = running.get("machines", [])
        tik = running.get("tik")
        if completed_machines:
            try:
                rescan_completed_machines(completed_machines)
            except Exception as e:
                logger.error(f"[WATCHDOG] Rescan completed machines failed: {e}")
        if tik and completed_machines:
            try:
                succeeded, failed_by_reason = collect_recent_batch_results(tik, completed_machines)
                db_path = Path(os.environ.get("TAADAA_TRACKER_DB", r"D:\Taadaa\data\tiktok_tracker.db"))
                if succeeded and db_path.exists():
                    try:
                        with sqlite3.connect(str(db_path), timeout=10) as conn:
                            cur = conn.cursor()
                            for m in succeeded:
                                cur.execute("""
                                UPDATE avatar_replace_queue
                                SET status = 'DONE', last_error = NULL, updated_at = datetime('now', 'localtime')
                                WHERE may = ? AND tik = ? AND host_id = ?
                                """, (m, tik, cid))
                                logger.info("[WATCHDOG][METRIC] event=avatar_queue_status_transition machine=%d tik=%d host=%s status=DONE", m, tik, cid)
                            state.setdefault("queue_transitions", {})["DONE"] = state.get("queue_transitions", {}).get("DONE", 0) + len(succeeded)
                            conn.commit()
                    except Exception as e:
                        logger.warning(f"[WATCHDOG][QUEUE_SYNC_ERR] Failed to mark succeeded machines in avatar_replace_queue: {e}")
                if failed_by_reason and db_path.exists():
                    try:
                        with sqlite3.connect(str(db_path), timeout=10) as conn:
                            cur = conn.cursor()
                            failed_cnt = 0
                            for reason, m_list in failed_by_reason.items():
                                for m in m_list:
                                    cur.execute("""
                                    UPDATE avatar_replace_queue
                                    SET last_error = ?, updated_at = datetime('now', 'localtime')
                                    WHERE may = ? AND tik = ? AND host_id = ? AND status = 'PENDING'
                                    """, (reason, m, tik, cid))
                                    logger.info("[WATCHDOG][METRIC] event=avatar_queue_status_transition machine=%d tik=%d host=%s status=FAILED error=%s", m, tik, cid, reason)
                                    failed_cnt += 1
                            state.setdefault("queue_transitions", {})["FAILED"] = state.get("queue_transitions", {}).get("FAILED", 0) + failed_cnt
                            conn.commit()
                    except Exception as e:
                        logger.warning(f"[WATCHDOG][QUEUE_SYNC_ERR] Failed to record failures in avatar_replace_queue: {e}")
                sess_key = get_session_key(now_hcmc())
                if state.get("active_session_key") != sess_key:
                    state["active_session_key"] = sess_key
                    state["session_uploaded_machines"] = []
                    state["session_failed_by_reason"] = {}
                cur_up = set(state.get("session_uploaded_machines", []))
                cur_up.update(succeeded)
                state["session_uploaded_machines"] = sorted(cur_up)
                cur_failed = state.get("session_failed_by_reason", {})
                for r_code, m_list in failed_by_reason.items():
                    m_set = set(cur_failed.get(r_code, []))
                    m_set.update(m_list)
                    cur_failed[r_code] = sorted(m_set)
                for r_code in list(cur_failed.keys()):
                    cur_failed[r_code] = sorted(set(cur_failed[r_code]) - cur_up)
                    if not cur_failed[r_code]:
                        cur_failed.pop(r_code, None)
                state["session_failed_by_reason"] = cur_failed
                logger.info(
                    "[WATCHDOG] [METRIC] event=session_failures_cleared cluster=%s active_errors=%d total_uploaded=%d",
                    cid,
                    sum(len(m) for m in cur_failed.values()),
                    len(cur_up),
                )
            except Exception as e:
                logger.error(f"[WATCHDOG] Collect recent batch results failed: {e}")
        running_batches.pop(cid, None)
    state["running_batches"] = running_batches
    if not running_batches:
        state["running_batch"] = None
    elif state.get("running_batch", {}).get("host_id") not in running_batches:
        state["running_batch"] = next(iter(running_batches.values()))
    save_state(state, state_file=state_file)
    return all_alive


def format_report_html(
    host_id: str,
    all_done: bool,
    stats_by_tik: dict[int, dict],
    target_tiks: list[int] | None = None,
    now_dt: datetime | None = None,
    stats_by_cluster: dict[str, dict] | None = None,
    session_stats: dict | None = None,
) -> str:
    """Định dạng template báo cáo Farm Alert. Hỗ trợ gộp toàn farm 2 cụm Kibe & Admin gọn gàng, sạch sẽ."""
    if now_dt is None:
        now_dt = now_hcmc()

    # Backward compatibility cho callers truyền unuploaded dạng dict[int, list[int]]
    if stats_by_tik:
        first_val = next(iter(stats_by_tik.values()))
        if isinstance(first_val, list):
            stats_by_tik = {
                tik: {
                    "unuploaded": stats_by_tik.get(tik, []),
                    "uploaded_count": 80 - len(stats_by_tik.get(tik, [])),
                    "total_accounts": 80,
                }
                for tik in (target_tiks or list(stats_by_tik.keys()))
            }


    # Tính trước tổng số máy còn thiếu để phần session summary có thể quyết định
    # trạng thái hoàn tất mà không phụ thuộc vào thứ tự khối render bên dưới.
    tot_miss = 0
    if stats_by_cluster:
        tot_miss = sum(
            len(st.get("unuploaded", []))
            for cluster_stats in stats_by_cluster.values()
            for st in cluster_stats.values()
        )

    session_lines = []
    if session_stats:
        sess_up = session_stats.get("session_uploaded_machines", [])
        sess_fail = session_stats.get("session_failed_by_reason", {})
        total_fail = sum(len(m_list) for m_list in sess_fail.values())
        if sess_up or sess_fail:
            session_lines.append(f"• Kết quả gần đây: Thành công +{len(sess_up)} acc mới | Lỗi {total_fail} máy")
        elif all_done or (stats_by_cluster and tot_miss == 0):
            session_lines.append("• Kết quả: Hoàn tất 100%, không ghi nhận lỗi.")
        if tot_miss > 0 and not all_done:
            session_lines.append(f"• Còn lại: {tot_miss} tài khoản chưa up")
        if sess_fail:
            session_lines.append("📋 CHI TIẾT CỤM LỖI CA TỐI NAY:")
            for r_code, m_list in sorted(sess_fail.items()):
                m_str = ", ".join(map(str, m_list[:10]))
                if len(m_list) > 10: m_str += f"... (+{len(m_list)-10})"
                session_lines.append(f"  ❌ [{r_code}] ({len(m_list)} máy): {m_str}")
    # Nếu có stats_by_cluster -> Báo cáo gộp TOÀN FARM (định dạng sạch, không lộ tag HTML)
    if stats_by_cluster:
        tot_up = 0
        tot_acc = 0
        tot_miss = 0
        cluster_blocks = []

        # Thứ tự hiển thị: kibe trước, admin sau
        cluster_order = [
            ("kibe", "FARM KIBE - MÁY 1-80", [5, 6, 7, 8, 3, 4]),
            ("admin", "FARM ADMIN - MÁY 201-280", [1, 2, 3, 4, 5, 6, 7, 8]),
        ]

        for c_id, c_label, c_tiks in cluster_order:
            if c_id not in stats_by_cluster:
                continue
            c_stats = stats_by_cluster[c_id]
            c_up = sum(c_stats.get(t, {}).get("uploaded_count", 0) for t in c_tiks)
            c_acc = sum(c_stats.get(t, {}).get("total_accounts", 0) for t in c_tiks)
            c_un = sum(len(c_stats.get(t, {}).get("unuploaded", [])) for t in c_tiks)
            c_pct = (c_up / c_acc * 100) if c_acc > 0 else 0.0

            tot_up += c_up
            tot_acc += c_acc
            tot_miss += c_un

            c_lines = [
                f"🏢 【{c_label}】: Đã có {c_up}/{c_acc} ({c_pct:.1f}%), còn {c_un} máy"
            ]

            done_tiks = []
            pending_lines = []

            for t in c_tiks:
                st = c_stats.get(t, {})
                un = st.get("unuploaded", [])
                up = st.get("uploaded_count", 0)
                tot = st.get("total_accounts", 0)
                pct = (up / tot * 100) if tot > 0 else 0.0

                if tot == 0:
                    continue
                elif un:
                    preview = ", ".join(map(str, un[:10]))
                    suffix = f"... (+{len(un)-10})" if len(un) > 10 else ""
                    pending_lines.append(
                        f"  • Tik {t}: Đã có {up}/{tot} ({pct:.1f}%) — còn {len(un)} máy ({preview}{suffix})"
                    )
                else:
                    done_tiks.append(f"Tik {t}")

            if pending_lines:
                c_lines.extend(pending_lines)
            if done_tiks:
                c_lines.append(f"  • Hoàn tất 100%: {', '.join(done_tiks)}")

            cluster_blocks.append("\n".join(c_lines))

        tot_pct = (tot_up / tot_acc * 100) if tot_acc > 0 else 0.0
        if all_done or tot_miss == 0:
            title = "🎉 [FARM REPORT][TOÀN FARM] HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK"
            status_line = f"• Trạng thái: Tất cả các acc hiện có nick đã được up avatar ({tot_up}/{tot_acc} acc)"
        else:
            title = "⏰ [FARM REPORT][TOÀN FARM] BÁO CÁO UP AVATAR ĐỊNH KỲ (6H)"
            status_line = f"• Trạng thái: Đang chạy cuốn chiếu né giờ nuôi — Đã có: {tot_up}/{tot_acc} acc ({tot_pct:.1f}%), còn {tot_miss} máy chưa up"

        lines = [
            title,
            f"• Thời gian: {now_dt.strftime('%H:%M:%S %d/%m/%Y')}",
            status_line,
        ] + session_lines + ["", "\n\n".join(cluster_blocks)]
        return "\n".join(lines)

    # Chế độ báo cáo đơn cụm (backward-compatible cho unit test)
    if target_tiks is None:
        target_tiks = list(stats_by_tik.keys())

    total_unuploaded = sum(len(stats_by_tik.get(tik, {}).get("unuploaded", [])) for tik in target_tiks)
    total_uploaded = sum(stats_by_tik.get(tik, {}).get("uploaded_count", 0) for tik in target_tiks)
    total_accounts = sum(stats_by_tik.get(tik, {}).get("total_accounts", 0) for tik in target_tiks)
    total_pct = (total_uploaded / total_accounts * 100) if total_accounts > 0 else 0.0

    tik_lines = []
    unassigned_tiks = []
    for tik in target_tiks:
        st = stats_by_tik.get(tik, {})
        unuploaded = st.get("unuploaded", [])
        up_cnt = st.get("uploaded_count", 0)
        tot_cnt = st.get("total_accounts", 0)
        pct = (up_cnt / tot_cnt * 100) if tot_cnt > 0 else 0.0

        if tot_cnt == 0:
            unassigned_tiks.append(tik)
        elif unuploaded:
            preview = ",".join(map(str, unuploaded[:15]))
            suffix = f"... (+{len(unuploaded)-15})" if len(unuploaded) > 15 else ""
            tik_lines.append(
                f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} ({pct:.1f}%) — còn {len(unuploaded)} máy ({preview}{suffix})"
            )
        else:
            tik_lines.append(f"• <b>Tik {tik}:</b> Đã có {up_cnt}/{tot_cnt} (hoàn tất 100%)")

    if unassigned_tiks:
        tik_lines.append(f"• <b>Chưa gán nick:</b> {', '.join(f'Tik {t}' for t in unassigned_tiks)}")

    if (all_done and total_accounts > 0) or (total_unuploaded == 0 and total_accounts > 0):
        title = f"🎉 <b>[FARM REPORT][{host_id.upper()}] HOÀN TẤT UP AVATAR CHO CÁC ACC ĐÃ CÓ NICK</b>"
        status_line = f"• <b>Trạng thái:</b> Tất cả các acc hiện có nick đã được up avatar ({total_uploaded}/{total_accounts} acc)"
    elif total_accounts == 0:
        title = f"⏰ <b>[FARM REPORT][{host_id.upper()}] BÁO CÁO UP AVATAR: CHƯA CÓ NICK</b>"
        status_line = "• <b>Trạng thái:</b> Chưa có tài khoản nào được gán trên các Tik đã cấu hình"
    else:
        title = f"⏰ <b>[FARM REPORT][{host_id.upper()}] BÁO CÁO UP AVATAR: HẾT KHUNG GIỜ</b>"
        status_line = f"• <b>Trạng thái:</b> Hết khung giờ ca tối (sau 23:30) — Đã có: {total_uploaded}/{total_accounts} acc ({total_pct:.1f}%), còn {total_unuploaded} máy chưa up"

    lines = [
        title,
        f"• <b>Thời gian:</b> {now_dt.strftime('%H:%M:%S %d/%m/%Y')}",
        status_line,
    ] + session_lines + ["• <b>Chi tiết từng Tik:</b>"] + tik_lines

    return "\n".join(lines)


def report_final_summary(
    state: dict,
    all_done: bool,
    host_context: dict | None = None,
    stats_by_tik: dict[int, dict] | None = None,
) -> None:
    """Gửi DUY NHẤT 1 báo cáo tổng kết khi tất cả Tik hoàn tất 100% hoặc hết khung giờ ca tối.
    Khi host_id == 'kibe', tự động thu thập thêm thống kê từ cụm Admin để xuất báo cáo [TOÀN FARM].
    """
    now = now_hcmc()
    slot_6h = (now.hour // 6) * 6
    sess_key = f"{now.strftime('%Y-%m-%d')}_{slot_6h:02d}"
    if not all_done and (
        state.get("last_reported_6h") == sess_key
        or state.get("last_reported_session") == sess_key
        or state.get("last_reported_date") == sess_key
    ):
        return
    if all_done and state.get("last_reported_all_done"):
        return

    ctx = host_context or get_host_context()
    target_tiks = ctx["target_tiks"]
    wb_dir = ctx["workbook_dir"]
    host_id = ctx["host_id"]

    if stats_by_tik is None:
        stats_by_tik = {tik: get_tik_avatar_stats(tik, workbook_dir=wb_dir) for tik in target_tiks}

    # Kibe là master: báo cáo tổng hợp phải xác nhận cả hai cluster.
    stats_by_cluster = None
    if host_id == "kibe":
        admin_tiks = [1, 2, 3, 4, 5, 6, 7, 8]
        admin_wb = Path(os.environ.get("TAADAA_ADMIN_WORKBOOK_ROOT", r"D:\OneDrive\TaadaaData\admin"))
        admin_host_cfg = Path(os.environ.get("TAADAA_ADMIN_HOST_CONFIG", ADMIN_HOST_CONFIG))
        admin_stats = {
            tik: get_tik_avatar_stats(
                tik,
                workbook_dir=admin_wb,
                host_context={
                    "host_id": "admin",
                    "host_config_path": admin_host_cfg,
                    "workbook_dir": admin_wb,
                },
            )
            for tik in admin_tiks
        }
        stats_by_cluster = {"kibe": stats_by_tik, "admin": admin_stats}
        all_done = all_done and all(
            not admin_stats[tik].get("unuploaded", [])
            for tik in admin_tiks
        )

    session_stats = {
        "session_uploaded_machines": state.get("session_uploaded_machines", []),
        "session_failed_by_reason": state.get("session_failed_by_reason", {}),
    }
    report_msg = format_report_html(
        host_id=host_id,
        all_done=all_done,
        stats_by_tik=stats_by_tik,
        target_tiks=target_tiks,
        now_dt=now,
        stats_by_cluster=stats_by_cluster,
        session_stats=session_stats,
    )
    # Gửi báo cáo trực tiếp qua Telegram Bot API (không in STDOUT để tránh rò rỉ cron)
    try:
        send_farm_alert(report_msg)
    except Exception as e:
        sys.stderr.write(f"[WATCHDOG] send_farm_alert failed: {e}\n")

    if all_done:
        state["last_reported_all_done"] = True
    state["last_reported_6h"] = sess_key
    state["last_reported_session"] = sess_key
    state["last_reported_date"] = sess_key
    save_state(state, state_file=ctx["state_file"])


def trigger_avatar_batch(tik: int, machines: list[int], state: dict, host_context: dict | None = None) -> bool:
    """Khởi chạy batch upload avatar qua PowerShell background (hoàn toàn im lặng)."""
    ctx = host_context or get_host_context()
    machine_list_str = ",".join(str(m) for m in machines)
    host_cfg = ctx.get("host_config_path")
    if not host_cfg:
        if str(ctx.get("host_id", "kibe")).lower() == "admin":
            host_cfg = Path(os.environ.get("TAADAA_ADMIN_HOST_CONFIG", ADMIN_HOST_CONFIG))
        else:
            host_cfg = HOST_CONFIG

    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(LAUNCHER),
        "-Tik", str(tik),
        "-ForceAvatarMachineList", machine_list_str,
        "-MaxParallel", "30",
        "-HostConfigPath", str(host_cfg),
    ]

    try:
        kwargs = {
            "cwd": str(TIKTOK_VIDEO_DIR),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "close_fds": True,
        }
        if str(ctx.get("host_id", "kibe")).lower() == "admin":
            kwargs["env"] = dict(os.environ)
            kwargs["env"]["ADB_SERVER_SOCKET"] = os.environ.get("TAADAA_ADMIN_ADB_SOCKET", ADMIN_ADB_SOCKET)
            kwargs["env"]["TAADAA_HOST_CONFIG"] = str(host_cfg)
        else:
            # Never let a remote Admin setting leak into a local Kibe batch.
            kwargs["env"] = dict(os.environ)
            kwargs["env"].pop("ADB_SERVER_SOCKET", None)
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000200  # CREATE_NO_WINDOW
        proc = subprocess.Popen(cmd, **kwargs)

        # Lưu state đang chạy, KHÔNG gửi tin nhắn bắt đầu
        batch_info = {
            "tik": tik,
            "machines": machines,
            "start_time": time.time(),
            "pid": proc.pid,
            "host_id": str(ctx.get("host_id", "kibe")).lower(),
        }
        cluster_id = batch_info["host_id"]
        state.setdefault("running_batches", {})[cluster_id] = batch_info
        state["running_batch"] = batch_info
        save_state(state, state_file=ctx["state_file"])
        return True

    except Exception as e:
        sys.stderr.write(f"post_evening_avatar: Failed to spawn Tik{tik}: {e}\n")
        return False


def main() -> int:
    ctx = get_host_context()
    now = now_hcmc()
    state = get_state(state_file=ctx["state_file"])

    # 1. Chỉ hoạt động trong khung giờ ca tối hoặc ngay sau ca tối (21:00 -> 04:00)
    in_window = is_post_evening_window(now)
    after_window = is_after_evening_window(now)
    if not (in_window or after_window):
        return 0

    # Kibe is the master and also drives the Admin cluster through remote ADB.
    if ctx["host_id"] == "kibe":
        admin_ctx = {
            "host_id": "admin",
            "host_config_path": Path(os.environ.get("TAADAA_ADMIN_HOST_CONFIG", ADMIN_HOST_CONFIG)),
            "target_tiks": [1, 2, 3, 4, 5, 6, 7, 8],
            "workbook_dir": Path(os.environ.get("TAADAA_ADMIN_WORKBOOK_ROOT", r"D:\OneDrive\TaadaaData\admin")),
            "state_file": ctx["state_file"],
        }
        clusters = [ctx, admin_ctx]
    else:
        clusters = [ctx]

    # 2. Dọn dẹp độc lập từng cluster; không còn cuốn chiếu giữa Kibe/Admin.
    for cluster_ctx in clusters:
        check_batch_status(state, state_file=ctx["state_file"], cluster_id=cluster_ctx["host_id"])

    # 3. Thu thập danh sách máy chưa up avatar cho tất cả các cluster/Tik.
    stats_by_cluster = {}
    all_unuploaded_by_cluster = {}
    cluster_missing = {}
    cluster_accounts = {}
    for cluster_ctx in clusters:
        cluster_id = cluster_ctx["host_id"]
        cluster_stats = {}
        cluster_unuploaded = {}
        for tik in cluster_ctx["target_tiks"]:
            st = get_tik_avatar_stats(tik, workbook_dir=cluster_ctx["workbook_dir"], host_context=cluster_ctx)
            cluster_stats[tik] = st
            cluster_unuploaded[tik] = st.get("unuploaded", [])
        stats_by_cluster[cluster_id] = cluster_stats
        all_unuploaded_by_cluster[cluster_id] = cluster_unuploaded
        cluster_missing[cluster_id] = sum(len(v) for v in cluster_unuploaded.values())
        cluster_accounts[cluster_id] = sum(st.get("total_accounts", 0) for st in cluster_stats.values())
        logger.info(f"[WATCHDOG] Cluster '{cluster_id}' scan: missing={cluster_missing[cluster_id]}, accounts={cluster_accounts[cluster_id]}")

    total_missing = sum(cluster_missing.values())
    total_accounts = sum(cluster_accounts.values())
    stats_by_tik = stats_by_cluster[ctx["host_id"]]

    # 4. Chỉ báo hoàn tất khi cả Kibe và Admin đều hoàn tất.
    all_clusters_done = (
        total_missing == 0
        and total_accounts > 0
        and all(cluster_accounts[c["host_id"]] > 0 and cluster_missing[c["host_id"]] == 0 for c in clusters)
    )
    if all_clusters_done:
        report_final_summary(state, all_done=True, host_context=ctx, stats_by_tik=stats_by_tik)
        return 0

    # 5. Nếu đã hết khung giờ ca tối -> báo cáo tổng kết cả hai cluster.
    if after_window:
        report_final_summary(state, all_done=False, host_context=ctx, stats_by_tik=stats_by_tik)
        return 0

    # 6. Trong khung giờ & còn máy chưa up: kiểm tra an toàn.
    if is_clear_cache_active():
        return 0
    if is_feed_active():
        return 0

    if not is_feed_session_finished_for_window(now):
        return 0
    if count_active_locks() > 5:
        return 0
    # Kích hoạt tối đa một batch cho MỖI cluster trong cùng một lượt watchdog.
    recent_launches = state.get("avatar_launch_history", [])
    for cluster_ctx in clusters:
        cluster_id = cluster_ctx["host_id"]
        cur_running = state.get("running_batches", {}).get(cluster_id)
        if cur_running and is_cluster_batch_alive(cluster_id, pid=cur_running.get("pid")):
            continue
        target_tiks = cluster_ctx["target_tiks"]
        cursor_key = f"avatar_rr_cursor_{cluster_id}"
        cursor = int(state.get(cursor_key, 0)) % len(target_tiks)
        ordered_tiks = target_tiks[cursor:] + target_tiks[:cursor]
        for offset, tik in enumerate(ordered_tiks):
            missing_machines = all_unuploaded_by_cluster[cluster_id].get(tik, [])
            if not missing_machines:
                continue
            last_for_tik = next(
                (l for l in reversed(recent_launches)
                 if l.get("host_id", "kibe") == cluster_id and l.get("tik") == tik),
                None,
            )
            if last_for_tik and (time.time() - last_for_tik.get("timestamp", 0) < 900):
                continue
            launch_ctx = dict(cluster_ctx)
            launch_ctx["state_file"] = ctx["state_file"]
            logger.info(f"[WATCHDOG] Triggering batch for cluster '{cluster_id}' Tik {tik} with {len(missing_machines)} machines: {missing_machines[:5]}...")
            if trigger_avatar_batch(tik, missing_machines, state, host_context=launch_ctx):
                recent_launches.append({"host_id": cluster_id, "tik": tik, "timestamp": time.time()})
                state["avatar_launch_history"] = recent_launches[-100:]
                state[cursor_key] = (cursor + offset + 1) % len(target_tiks)
                save_state(state, state_file=ctx["state_file"])
                break

    return 0


if __name__ == "__main__":
    sys.exit(main())
