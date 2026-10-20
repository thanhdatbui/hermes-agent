import os
import sys
# Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (56 cores)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import subprocess
"""Watchdog báo cáo kết quả nuôi TikTok theo từng CA (1 spawn per Ca)."""
import glob
import json
import re
import time
import uuid
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple, Any, List
from zoneinfo import ZoneInfo
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_repo_scripts = os.environ.get("TAADAA_SCRIPTS_DIR")
_candidates = [_curr_dir, _repo_scripts, os.path.normpath(os.path.join(_curr_dir, "..", "scripts")), os.path.normpath(os.path.join(os.environ.get("TAADAA_ROOT", "D:/Taadaa"), "tiktok-luot nuoi acc", "scripts"))]
for _cand in _candidates:
    if _cand and os.path.isdir(os.path.join(_cand, "watchdog")) and _cand not in sys.path:
        sys.path.insert(0, _cand)
        print(f"[WATCHDOG_PATH_TELEMETRY] injected_sys_path={_cand}", file=sys.stderr)
        break
try:
    from watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
    from watchdog.merger import is_device_locked_skip, merge_machine_result, merge_follow_result, merge_upload_result
    from watchdog.alerts import DEFAULT_FARM_ALERT_THRESHOLD, NURTURE_CYCLE_H, STARVATION_THRESHOLD_H, should_trigger_farm_alert, get_row_nurture_summary, normalize_machine_key, get_expected_machines_for_cluster
    from watchdog.formatters import (
        classify_machine_follow_result,
        format_success_follows,
        format_released_follows,
        format_ip_circuit_breaker_report,
        classify_feed_failure,
        classify_error_reason,
    )
    from watchdog.parser import parse_run_all, parse_run_machines, parse_follow_results, parse_upload_results
except ImportError:
    from scripts.watchdog.lock import ProcessLock, is_feed_runner_active, is_pid_alive
    from scripts.watchdog.merger import is_device_locked_skip, merge_machine_result, merge_follow_result, merge_upload_result
    from scripts.watchdog.alerts import DEFAULT_FARM_ALERT_THRESHOLD, NURTURE_CYCLE_H, STARVATION_THRESHOLD_H, should_trigger_farm_alert, get_row_nurture_summary, normalize_machine_key, get_expected_machines_for_cluster
    from scripts.watchdog.formatters import (
        classify_machine_follow_result,
        format_success_follows,
        format_released_follows,
        format_ip_circuit_breaker_report,
        classify_feed_failure,
        classify_error_reason,
    )
    from scripts.watchdog.parser import parse_run_all, parse_run_machines, parse_follow_results, parse_upload_results

logger = logging.getLogger("feed_session_watchdog")
HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
def _get_runtime_root() -> str:
    cfg_path = os.environ.get("TAADAA_HOST_CONFIG", r"D:\Taadaa\machine-config\kibe.yaml")
    rt_root = r"D:\Taadaa\runtime\kibe"
    if os.path.exists(cfg_path):
        try:
            import yaml
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "runtime_root" in data:
                    rt_root = data["runtime_root"]
        except Exception:
            pass
    return rt_root

_RT_ROOT = _get_runtime_root()
LIVE_ROOT = os.path.join(_RT_ROOT, "live")
STATE_FILE = os.path.join(_RT_ROOT, "cron-state", "feed_session_reported.json")
FOLLOW_STATE_FILE = os.path.join(_RT_ROOT, "cron-state", "follow_session_reported.json")
SOURCE_CONFIG = os.path.join(_RT_ROOT, "cron-source", "hermes_cron_source_config.json")
SHIFT_UPLOAD_LEDGER_PATH = r"C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json"

CLUSTERS: list[dict[str, Any]] = [
    {
        "name": "kibe",
        "label": "FARM KIBE - MÁY 1-80",
        "runtime_root": r"D:/Taadaa/runtime\kibe",
        "live_root": r"D:/Taadaa/runtime\kibe\live",
        "account_workbook": r"D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx",
        "fleet_min": 1,
        "fleet_max": 80,
    },
    {
        "name": "admin",
        "label": "FARM ADMIN - MÁY 201-280",
        "runtime_root": r"D:/Taadaa/runtime\admin",
        "live_root": r"D:/Taadaa/runtime\admin\live",
        "account_workbook": r"D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx",
        "fleet_min": 201,
        "fleet_max": 280,
    },
]

DEFAULT_ROW1_MACHINES_COUNT = 74
DEFAULT_ROW2_MACHINES_COUNT = 72
_LEDGER_LOCK = threading.Lock()
_LEDGER_CACHE: Optional[Dict[str, Any]] = None
_LEDGER_SUCCESS_SET: frozenset = frozenset()
_LEDGER_CACHE_MTIME_NS: int = 0


def _load_reported_sessions(path: str) -> set:
    """Tải tập hợp các session đã report từ state file, chỉ lấy các session ID dạng string hợp lệ."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            sessions = data.get("reported_sessions")
            if isinstance(sessions, list):
                res = set()
                for s in sessions:
                    if isinstance(s, str) and s.strip():
                        res.add(s.strip())
                    else:
                        logger.warning("Bỏ qua session ID không hợp lệ trong state file: %r (type: %s)", s, type(s).__name__)
                return res
    except Exception:
        pass
    return set()

# Định nghĩa các khung Ca chuẩn, mỗi Ca chia 2 Phiên, bao phủ liên tục 24h
SESSION_WINDOWS = [
    # Ca 1 (Sáng) - Row 1 ngày lẻ, Row 2 ngày chẵn
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/2 (Sáng)", "start": "06:00", "end": "08:00"},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/2 (Sáng)", "start": "08:00", "end": "12:00"},
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/2 (Chiều)", "start": "12:00", "end": "14:00"},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/2 (Chiều)", "start": "14:00", "end": "18:00"},

    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/2 (Tối)", "start": "18:00", "end": "20:00"},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/2 (Tối)", "start": "20:00", "end": "24:00"},

    {"ca": 4, "phien": 1, "name": "Ca 4 - Phiên 1/2 (Đêm)", "start": "00:00", "end": "01:30"},
    {"ca": 4, "phien": 2, "name": "Ca 4 - Phiên 2/2 (Đêm)", "start": "01:30", "end": "06:00"},
]


def get_expected_machines_for_row(row_num: Any) -> set:
    """Lấy danh sách set các máy dự kiến theo row từ hermes_cron_source_config.json."""
    if not os.path.exists(SOURCE_CONFIG):
        default_count = DEFAULT_ROW1_MACHINES_COUNT if str(row_num) == "1" else DEFAULT_ROW2_MACHINES_COUNT
        return set(str(i) for i in range(1, default_count + 1))
    try:
        with open(SOURCE_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
        accounts = data.get("feed_source", {}).get("accounts", [])
        m_list = [
            str(a["machine"]) for a in accounts
            if str(a.get("account_row", "")).strip() == str(row_num).strip() and "machine" in a
        ]
        if m_list:
            return set(m_list)
        default_count = DEFAULT_ROW1_MACHINES_COUNT if str(row_num) == "1" else DEFAULT_ROW2_MACHINES_COUNT
        return set(str(i) for i in range(1, default_count + 1))
    except Exception:
        default_count = DEFAULT_ROW1_MACHINES_COUNT if str(row_num) == "1" else DEFAULT_ROW2_MACHINES_COUNT
        return set(str(i) for i in range(1, default_count + 1))


def get_all_fleet_machines() -> set:
    """Lấy toàn bộ danh sách 80 máy của Farm."""
    if os.path.exists(SOURCE_CONFIG):
        try:
            with open(SOURCE_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
            accounts = data.get("feed_source", {}).get("accounts", [])
            m_set = {str(a["machine"]) for a in accounts if "machine" in a}
            if m_set:
                max_m = max(int(x) for x in m_set if x.isdigit())
                target_cnt = max(max_m, 80)
                return set(str(i) for i in range(1, target_cnt + 1))
        except Exception as exc:
            logger.debug("get_all_fleet_machines read error from %s: %s", SOURCE_CONFIG, exc)
    return set(str(i) for i in range(1, 81))


def _build_ledger_success_index(data: dict) -> set:
    """Tạo indexed lookup set (machine, row, date) từ ledger payload để đạt O(1) query."""
    res = set()
    if not isinstance(data, dict):
        return res
    for _, v in data.items():
        if not isinstance(v, dict):
            continue
        if str(v.get("status", "")).strip().lower() != "success":
            continue
        m_str = str(v.get("machine", "")).strip()
        r_str = str(v.get("row", "")).strip()
        if not m_str or not r_str:
            continue
        day_str = str(v.get("logical_day", "")).strip()
        if day_str and re.match(r"^\d{4}-\d{2}-\d{2}$", day_str):
            res.add((m_str, r_str, day_str))
        ts = str(v.get("timestamp", "")).strip()
        if len(ts) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2}$", ts[:10]) and ts[:10] != day_str:
            res.add((m_str, r_str, ts[:10]))
    return res


def _get_shift_upload_ledger_cached() -> frozenset:
    """Đọc ledger shift upload với in-memory cache, thread-safe, O(1) indexed set và mtime_ns invalidation."""
    global _LEDGER_CACHE, _LEDGER_SUCCESS_SET, _LEDGER_CACHE_MTIME_NS
    with _LEDGER_LOCK:
        if not os.path.exists(SHIFT_UPLOAD_LEDGER_PATH):
            return frozenset()
        try:
            st = os.stat(SHIFT_UPLOAD_LEDGER_PATH)
            if st.st_size > 50 * 1024 * 1024:  # 50MB safety cap
                logger.warning("Shift upload ledger size exceeds 50MB safety cap: %d bytes", st.st_size)
                return frozenset()
            if _LEDGER_CACHE is not None and st.st_mtime_ns == _LEDGER_CACHE_MTIME_NS:
                return _LEDGER_SUCCESS_SET
            with open(SHIFT_UPLOAD_LEDGER_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            new_cache = loaded if isinstance(loaded, dict) else {}
            new_set = frozenset(_build_ledger_success_index(new_cache))
            _LEDGER_SUCCESS_SET = new_set
            _LEDGER_CACHE = new_cache
            _LEDGER_CACHE_MTIME_NS = st.st_mtime_ns
            return _LEDGER_SUCCESS_SET
        except Exception as e:
            logger.warning("Error loading shift upload ledger: %s", e)
            return frozenset()


def is_machine_upload_successful_in_shift(target_date: str, machine: Any, row: Any) -> bool:
    """Kiểm tra O(1) ledger shift_upload_history.json xem máy có ghi nhận success trong ca/shift ngày đó không."""
    date_str = str(target_date).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        logger.warning("Invalid target_date format: %s", date_str)
        return False
    success_set = _get_shift_upload_ledger_cached()
    if not success_set:
        return False
    m_str = str(machine).strip()
    r_str = str(row).strip()
    return (m_str, r_str, date_str) in success_set



def _add_minutes_to_hm(hm_str: str, minutes: int) -> str:
    h, m = map(int, hm_str.split(":"))
    total = h * 60 + m + minutes
    new_h = (total // 60) % 24
    new_m = total % 60
    return f"{new_h:02d}:{new_m:02d}"


def calculate_session_natural_follows(
    all_machines: dict[str, Any],
    all_follows: dict[str, Any],
    fl_released: list[Any] | None = None,
) -> tuple[int, int, int, int, int]:
    """Tính toán số lượt follow tự nhiên hợp lệ sau khi trừ các nick bị nhả/drop.
    
    Trả về: (valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot)
    """
    fl_released = fl_released or []
    # Chỉ bỏ follow tự nhiên của các máy mà lượt đầu follow chéo = 0 (cnt == 0).
    # Nếu lượt đầu follow chéo đã thành công (cnt > 0) thì tính hết follow tự nhiên.
    released_machine_set = set()
    for m in fl_released:
        norm_m = normalize_machine_key(m)
        f_data = all_follows.get(norm_m) or all_follows.get(str(m)) or {}
        followed_val = f_data.get("followed") if isinstance(f_data, dict) else []
        cnt = len(followed_val) if isinstance(followed_val, (list, tuple)) else 0
        if cnt == 0:
            released_machine_set.add(norm_m)

    for m_k, f_data in all_follows.items():
        if isinstance(f_data, dict) and (
            f_data.get("follow_failed") is True
            or str(f_data.get("status") or "").upper() == "FOLLOW_FAILED"
        ):
            norm_k = normalize_machine_key(m_k)
            followed_val = f_data.get("followed")
            cnt = len(followed_val) if isinstance(followed_val, (list, tuple)) else 0
            if cnt == 0:
                released_machine_set.add(norm_k)

    tot_fy = 0
    tot_fl = 0
    tot_fr = 0
    dropped_fy = 0
    dropped_fl = 0
    dropped_fr = 0

    for m, d in all_machines.items():
        if not isinstance(d, dict) or d.get("status") != "success":
            continue
        norm_m = normalize_machine_key(m)
        nf = d.get("natural_follows") or {}
        fy = int(nf.get("for-you", 0) or 0)
        fl = int(nf.get("following", 0) or 0)
        fr = int(nf.get("friends", 0) or 0)
        tot_fy += fy
        tot_fl += fl
        tot_fr += fr
        if norm_m in released_machine_set:
            dropped_fy += fy
            dropped_fl += fl
            dropped_fr += fr

    dropped_tot = dropped_fy + dropped_fl + dropped_fr
    valid_fy = max(0, tot_fy - dropped_fy)
    valid_fl = max(0, tot_fl - dropped_fl)
    valid_fr = max(0, tot_fr - dropped_fr)
    valid_tot = max(0, (tot_fy + tot_fl + tot_fr) - dropped_tot)

    return valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot


def save_session_action_stats(
    db_path: str,
    session_key: str,
    cluster_name: str,
    target_date: str,
    internal_fl: int,
    natural_fl: int,
    likes: int,
    swipes: int,
) -> None:
    """Lưu thống kê action (follow nội bộ vs follow tự nhiên) của phiên vào SQLite tiktok_tracker.db."""
    if not os.path.exists(db_path):
        return
    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=10.0)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS session_action_stats (
                session_key TEXT,
                cluster TEXT,
                target_date TEXT,
                internal_follows INTEGER DEFAULT 0,
                natural_follows INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                swipes INTEGER DEFAULT 0,
                created_at TEXT,
                PRIMARY KEY (session_key, cluster)
            )
        """)
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO session_action_stats (
                session_key, cluster, target_date, internal_follows, natural_follows, likes, swipes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_key, cluster) DO UPDATE SET
                internal_follows = excluded.internal_follows,
                natural_follows = excluded.natural_follows,
                likes = excluded.likes,
                swipes = excluded.swipes,
                created_at = excluded.created_at
        """, (session_key, cluster_name, target_date, internal_fl, natural_fl, likes, swipes, now_ts))
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("save_session_action_stats error: %s", exc)


RECONCILE_METRICS: dict[str, int] = {"buffer_applied": 0, "buffer_capped": 0, "subsecond_capped": 0, "guard_triggered": 0, "parse_fallback": 0}
_METRICS_LOCK: threading.Lock = threading.Lock()


def reset_reconcile_metrics() -> None:
    """Reset các counters đo đạc về 0 giữa các sessions/test cases."""
    with _METRICS_LOCK:
        RECONCILE_METRICS.update({k: 0 for k in RECONCILE_METRICS})


def get_reconcile_metrics() -> dict[str, int]:
    """Lấy bản sao thread-safe của RECONCILE_METRICS dưới bảo vệ của lock."""
    with _METRICS_LOCK:
        return dict(RECONCILE_METRICS)


def buffer_reconcile_iso(iso_val: Optional[str], minutes: int = 10) -> Optional[str]:
    """Mở rộng window ISO một khoảng thời gian (phút) để bắt kịp các snapshot cào trễ."""
    if not iso_val: return iso_val
    clean_val = iso_val.strip()
    if clean_val.endswith("23:59:59"):
        if minutes > 0:
            with _METRICS_LOCK: RECONCILE_METRICS["buffer_capped"] += 1
        return clean_val
    try:
        raw_dt = clean_val.replace("T", " ").split("+")[0].split("Z")[0].strip()
        dt = datetime.strptime(raw_dt, "%Y-%m-%d %H:%M:%S.%f" if "." in raw_dt else "%Y-%m-%d %H:%M:%S")
        buffered_dt = dt + timedelta(minutes=minutes)
        # Cap về 23:59:59 (microsecond=0) khớp định dạng SQLite; lệch <1s khi buffered_dt trong (23:59:59, 23:59:59.999999].
        end_of_day = dt.replace(hour=23, minute=59, second=59, microsecond=0)
        start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        was_capped = was_subsecond_capped = False
        if minutes > 0 and buffered_dt > end_of_day:
            was_subsecond_capped = buffered_dt <= end_of_day.replace(microsecond=999999)
            buffered_dt, was_capped = end_of_day, True
        elif minutes < 0 and buffered_dt < start_of_day:
            buffered_dt = start_of_day
            was_capped = True
        with _METRICS_LOCK:
            if was_capped:
                RECONCILE_METRICS["buffer_capped"] += 1
                if was_subsecond_capped:
                    RECONCILE_METRICS["subsecond_capped"] += 1
            elif minutes != 0:
                RECONCILE_METRICS["buffer_applied"] += 1
        res = buffered_dt.strftime("%Y-%m-%d %H:%M:%S")
        if minutes != 0:
            logger.info("[RECONCILE_BUFFER_TELEMETRY] iso=%s -> %s (minutes=%d, capped=%s, subsecond_capped=%s)", iso_val, res, minutes, was_capped, was_subsecond_capped)
        return res
    except Exception as exc:
        with _METRICS_LOCK: RECONCILE_METRICS["parse_fallback"] += 1
        logger.debug("buffer_reconcile_iso: cannot parse '%s': %s", iso_val, exc)
        return iso_val


def parse_reconcile_iso_dt(iso_val: Optional[str]) -> Optional[datetime]:
    """Parse an toàn ISO datetime string sang datetime object."""
    if not iso_val: return None
    try:
        raw = iso_val.strip().replace("T", " ").split("+")[0].split("Z")[0].strip()
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S.%f" if "." in raw else "%Y-%m-%d %H:%M:%S")
    except Exception: return None


def is_session_key_p1_or_unknown(session_key: Optional[str]) -> bool:
    """Unknown/empty keys default to Phiên 1 (fail-safe); p10/phien12 are later; explicit p1 wins over p2+."""
    if not session_key: return True
    s_lower = session_key.lower()
    has_p1 = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*1(?![0-9])", s_lower))
    has_later = bool(re.search(r"(?<![a-z0-9])(?:phien|session|p)[\s_.-]*([2-9]|\d{2,})", s_lower))
    return not (has_later and not has_p1)


def reconcile_cluster_following(
    cluster: dict[str, Any], fl_success: list, all_follows: dict, active_row: int,
    session_start_iso: Optional[str] = None, session_end_iso: Optional[str] = None,
    db_path: str = r"D:/Taadaa/data/tiktok_tracker.db", python_exe: str = r"D:/Taadaa/python-envs/automation/Scripts/python.exe",
    tracker_script: str = r"D:/Taadaa/tools/tiktok_account_tracker.py", all_machines: Optional[dict] = None,
    session_key: Optional[str] = None, auto_reset_metrics: bool = True,
) -> list[str]:
    """Cào và đối soát số lượng following tăng thật trên TikTok Web so với script báo cáo."""
    if auto_reset_metrics: reset_reconcile_metrics()
    wb_path = cluster.get("account_workbook")
    if not wb_path or not os.path.exists(wb_path):
        return []

    ws = None
    wb = None
    for attempt in range(1, 4):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(wb_path, read_only=True)
            ws = wb.active
            break
        except (IOError, OSError, PermissionError) as exc:
            logger.warning("reconcile_cluster_following: thử tải workbook lần %d thất bại (%s): %s", attempt, wb_path, exc)
            if attempt < 3:
                time.sleep(1)
        except Exception as exc:
            logger.error("reconcile_cluster_following: workbook hỏng hoặc không thể đọc (%s): %s", wb_path, exc)
            break
    if ws is None or wb is None:
        return [f"  + Đối soát TikTok Web: Không đọc được workbook ({wb_path})"]
    try:
        machine_slots: dict[str, list[Any]] = {}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or r[0] is None:
                continue
            try:
                m_str = str(int(str(r[0]).strip()))
            except (ValueError, TypeError):
                continue
            machine_slots.setdefault(m_str, []).append(r[2] if len(r) > 2 else None)
    except Exception as exc:
        logger.warning("reconcile_cluster_following: không đọc được workbook: %s", exc)
        return [f"  + Đối soát TikTok Web: Lỗi đọc dữ liệu workbook ({wb_path})"]
    finally:
        try:
            wb.close()
        except Exception:
            pass

    slot_idx = int(active_row) - 1
    m_to_user: dict[str, str] = {}
    m_to_reported: dict[str, int] = {}
    m_to_cross: dict[str, int] = {}
    m_to_natural: dict[str, int] = {}
    failed_reset_machines: list[str] = []
    all_machines = all_machines or {}
    natural_targets = {
        str(m): sum((v or 0) for v in (data.get("natural_follows") or {}).values())
        for m, data in all_machines.items()
        if sum((v or 0) for v in (data.get("natural_follows") or {}).values()) > 0
    }
    target_machines = (
        {str(m) for m in fl_success}
        | {str(m) for m, fd in all_follows.items() if isinstance(fd, dict) and len(fd.get("followed") or []) > 0}
        | set(natural_targets)
    )

    for m in target_machines:
        follow_data = all_follows.get(m, {})
        if not follow_data and str(m).isdigit():
            follow_data = all_follows.get(int(m), {})
        followed_val = follow_data.get("followed") if isinstance(follow_data, dict) else []
        cnt = len(followed_val) if isinstance(followed_val, (list, tuple)) else 0
        natural_cnt = natural_targets.get(m, 0)
        if cnt <= 0 and natural_cnt <= 0:
            continue
        slots = machine_slots.get(str(m), [])
        if slot_idx < len(slots):
            val = slots[slot_idx]
            if val and str(val).strip() and str(val).strip().lower() != "none":
                u = str(val).strip().lstrip('@')
                m_to_user[str(m)] = u
                failed = bool((all_follows.get(m) or {}).get("follow_failed"))
                if not failed and str(m).isdigit() and all_follows:
                    failed = bool((all_follows.get(int(m)) or {}).get("follow_failed"))
                # Nếu dính follow_failed ngay từ lượt đầu tiên (cnt == 0):
                # TikTok chưa nhận follow chéo nào -> coi như nick bị nhả/drop,
                # bỏ hết follow tự nhiên và chéo (reported = 0) để không tạo delta âm.
                # Ngược lại, nếu lượt đầu đã follow thành công (cnt > 0):
                # tính toàn bộ follow tự nhiên + các lượt chéo đã bấm thành công cho tới khi bị nhả.
                if failed and cnt == 0:
                    m_to_reported[str(m)] = 0
                    failed_reset_machines.append(str(m))
                else:
                    m_to_reported[str(m)] = cnt + natural_cnt
                m_to_cross[str(m)] = cnt
                m_to_natural[str(m)] = natural_cnt
                logger.info(
                    "[FOLLOW_RECONCILE_TELEMETRY] Machine %s: user=%s failed=%s cross_cnt=%d natural_cnt=%d reported=%d",
                    m, u, failed, cnt, natural_cnt, m_to_reported[str(m)]
                )

    if failed_reset_machines:
        logger.info(
            "reconcile_cluster_following: reset reported follow count to 0 for %d follow_failed machine(s): %s",
            len(failed_reset_machines),
            ", ".join(sorted(set(failed_reset_machines), key=lambda value: int(value) if value.isdigit() else value)),
        )

    if not m_to_user:
        if target_machines:
            return [f"  + Đối soát TikTok Web: Không tìm thấy username trong workbook cho {len(target_machines)} máy follow"]
        return []

    target_users = list(m_to_user.values())
    try:
        py_cmd = python_exe if os.path.exists(python_exe) else sys.executable
        if os.path.exists(tracker_script):
            cmd = [
                py_cmd,
                tracker_script,
                "--usernames", *target_users,
                "--workers", str(min(10, max(1, len(target_users)))),
            ]
            subprocess.run(cmd, capture_output=True, timeout=90, text=True)
    except Exception as exc:
        logger.warning("reconcile_cluster_following: lỗi chạy tracker: %s", exc)

    if not os.path.exists(db_path):
        return ["  + Đối soát TikTok Web: Không tìm thấy DB tiktok_tracker.db"]

    try:
        import sqlite3
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        except Exception:
            conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        details = []
        total_reported = 0
        total_scraped_delta = 0
        has_valid_delta_count = 0

        def _num_m(x):
            nums = re.findall(r"\d+", str(x))
            return int(nums[0]) if nums else 0

        is_p1_or_unknown = is_session_key_p1_or_unknown(session_key)
        query_start_iso = session_start_iso if is_p1_or_unknown else buffer_reconcile_iso(session_start_iso, 10)

        # Guard an toàn: Parse datetime chuẩn xác, tuyệt đối không để query_start_iso vượt qua session_end_iso gốc
        start_dt = parse_reconcile_iso_dt(query_start_iso)
        end_dt = parse_reconcile_iso_dt(session_end_iso)
        if start_dt and end_dt and start_dt >= end_dt:
            query_start_iso = session_start_iso
            with _METRICS_LOCK:
                RECONCILE_METRICS["guard_triggered"] += 1

        query_end_iso = buffer_reconcile_iso(session_end_iso, 10)
        logger.info(
            "[FOLLOW_RECONCILE_WINDOW] key=%s raw_window=[%s, %s] query_window=[%s, %s]",
            session_key, session_start_iso, session_end_iso, query_start_iso, query_end_iso
        )

        for m in sorted(m_to_user.keys(), key=_num_m):
            u = m_to_user[m]
            cross_cnt = m_to_cross[m]
            natural_cnt = m_to_natural.get(m, 0)
            expected_delta = m_to_reported[m]
            report_label = f"script báo {expected_delta} (chéo {cross_cnt}, tự nhiên {natural_cnt})"
            try:
                if query_end_iso:
                    cur.execute("""
                        SELECT following, timestamp
                        FROM snapshots
                        WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
                        ORDER BY timestamp DESC, id DESC
                        LIMIT 1
                    """, (u, query_end_iso))
                    l_rows = cur.fetchall()
                    latest_row = l_rows[0] if l_rows else None
                else:
                    cur.execute("""
                        SELECT following, timestamp
                        FROM snapshots
                        WHERE LOWER(username) = LOWER(?)
                        ORDER BY timestamp DESC, id DESC
                        LIMIT 2
                    """, (u,))
                    pair = cur.fetchall()
                    latest_row = pair[0] if len(pair) >= 1 else None

                baseline_row = None
                if latest_row and query_start_iso:
                    cur.execute("""
                        SELECT following, timestamp
                        FROM snapshots
                        WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
                        ORDER BY timestamp DESC, id DESC
                        LIMIT 1
                    """, (u, query_start_iso))
                    b_rows = cur.fetchall()
                    if b_rows:
                        baseline_row = b_rows[0]

                if latest_row and not session_start_iso and len(pair) >= 2:
                    baseline_row = pair[1]

                if latest_row and baseline_row:
                    latest_fl = latest_row[0] or 0
                    prev_fl = baseline_row[0] or 0
                    web_delta = latest_fl - prev_fl
                    total_scraped_delta += web_delta
                    has_valid_delta_count += 1
                    diff = web_delta - expected_delta
                    total_reported += expected_delta
                    match_str = "khớp" if diff == 0 else f"lệch ({diff:+d})"
                    u_str = f" (@{u})" if u else ""
                    sub_info = f" (chéo {cross_cnt}, tự nhiên {natural_cnt})" if (cross_cnt > 0 and natural_cnt > 0) else ""
                    details.append(f"    - M{m}{u_str} : script {expected_delta} lượt{sub_info} - web {web_delta} lượt - {match_str}")
                else:
                    details.append(
                        f"    - M{m} (@{u}): {report_label} | thiếu baseline/latest snapshot | UNPROVEN"
                    )
            except Exception as err:
                details.append(f"    - M{m} (@{u}): {report_label} | lỗi đọc snapshot: {err}")

        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        act_date = session_start_iso[:10] if session_start_iso else now_ts[:10]
        cluster_name = cluster.get("name", "unknown")
        s_key = session_key or f"{act_date}_unknown"
        conn_w = None
        try:
            conn_w = sqlite3.connect(db_path, timeout=10.0)
            cur_w = conn_w.cursor()
            cur_w.execute("""
                CREATE TABLE IF NOT EXISTS session_account_actions (
                    session_key TEXT,
                    cluster TEXT,
                    target_date TEXT,
                    username TEXT,
                    may INTEGER,
                    internal_follows INTEGER DEFAULT 0,
                    updated_at TEXT,
                    PRIMARY KEY (session_key, cluster, username)
                )
            """)
            cur_w.execute("""
                CREATE TABLE IF NOT EXISTS daily_account_actions (
                    target_date TEXT,
                    username TEXT,
                    may INTEGER,
                    internal_follows INTEGER DEFAULT 0,
                    updated_at TEXT,
                    PRIMARY KEY (target_date, username)
                )
            """)
            for m_num, u_name in m_to_user.items():
                is_failed = str(m_num) in failed_reset_machines
                c_cnt = 0 if is_failed else m_to_reported.get(str(m_num), 0)
                if u_name:
                    cur_w.execute("""
                        INSERT INTO session_account_actions (session_key, cluster, target_date, username, may, internal_follows, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(session_key, cluster, username) DO UPDATE SET
                            internal_follows = excluded.internal_follows,
                            updated_at = excluded.updated_at
                    """, (s_key, cluster_name, act_date, u_name.lower(), int(m_num) if str(m_num).isdigit() else None, c_cnt, now_ts))

            cur_w.execute("""
                INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
                SELECT target_date, username, MAX(may), SUM(internal_follows), MAX(updated_at)
                FROM session_account_actions
                WHERE target_date = ?
                GROUP BY target_date, username
                ON CONFLICT(target_date, username) DO UPDATE SET
                    internal_follows = excluded.internal_follows,
                    may = excluded.may,
                    updated_at = excluded.updated_at
            """, (act_date,))
            conn_w.commit()
            conn_w.close()
            logger.info(
                "[FOLLOW_RECONCILE_TELEMETRY] session_key=%s cluster=%s target_date=%s "
                "audited_accounts=%d failed_reset_count=%d reported_follows=%d scraped_delta=%d diff=%d",
                s_key, cluster_name, act_date,
                len(m_to_user), len(failed_reset_machines), total_reported, total_scraped_delta,
                (total_scraped_delta - total_reported),
            )
        except Exception as err:
            logger.error("[FOLLOW_RECONCILE_DB_ERROR] session_key=%s cluster=%s error=%s", s_key, cluster_name, err)
            if "conn_w" in locals() and conn_w:
                try:
                    conn_w.rollback()
                    conn_w.close()
                except Exception:
                    pass

        conn.close()

        if has_valid_delta_count > 0:
            total_diff = total_scraped_delta - total_reported
            if total_diff == 0:
                header_reconcile = f"  + Đối soát TikTok Web (+{total_scraped_delta} Following thật - Khớp 100% so với script báo):"
            else:
                diff_sign = f"+{total_diff}" if total_diff > 0 else f"{total_diff}"
                header_reconcile = f"  + Đối soát TikTok Web ({total_scraped_delta:+d} Following thật | Lệch {diff_sign} so với script báo {total_reported}):"
            return ([header_reconcile] + details) if details else [header_reconcile.rstrip(":")]
        elif details:
            return [f"  + Đối soát TikTok Web (Script báo {total_reported} lượt follow):"] + details
        return []
    except Exception as exc:
        logger.warning("reconcile_cluster_following: lỗi kết nối/đọc db: %s", exc)
        return [f"  + Đối soát TikTok Web: Lỗi truy vấn snapshot: {exc}"]


def _is_session_manifest_completed(date_live: str, run_name: str, win_end_hm: str) -> bool:
    """Kiểm tra run_manifest của lượt chạy đã hoàn thành và đạt mốc kết thúc phiên chưa."""
    latest_outer = os.path.join(date_live, run_name)
    manifest_paths = [os.path.join(latest_outer, "run_manifest.json")]
    try:
        for child in os.listdir(latest_outer):
            child_manifest = os.path.join(latest_outer, child, "run_manifest.json")
            if os.path.isfile(child_manifest):
                manifest_paths.append(child_manifest)
    except OSError:
        pass

    for manifest_path in manifest_paths:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            end_time = payload.get("end_time") if isinstance(payload, dict) else None
            if not end_time or not isinstance(end_time, str):
                continue
            if win_end_hm in {"24:00", "00:00"}:
                return True
            try:
                dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(HCMC)
                end_hm = dt.strftime("%H:%M")
            except Exception:
                end_hm = end_time.replace("T", " ").split(" ", 1)[-1][:5]
            if end_hm >= win_end_hm:
                return True
        except (OSError, ValueError, TypeError):
            continue
    return False


def _has_later_session_run_started(date_live: str, latest_run_name: str, latest_hhmmss: str) -> bool:
    """Kiểm tra đã có lượt chạy của phiên kế tiếp xuất hiện trong ngày chưa."""
    try:
        for name in os.listdir(date_live):
            if not name.startswith("row-") or name == latest_run_name:
                continue
            parts = name.split("-")
            if len(parts) >= 3 and parts[2][:6].isdigit() and str(latest_hhmmss)[:6].isdigit():
                if int(parts[2][:6]) > int(str(latest_hhmmss)[:6]):
                    return True
            elif name > latest_run_name:
                return True
    except OSError:
        pass
    return False


def is_cluster_session_busy(
    date_live: str,
    session_runs: list[tuple[str, str]],
    win_end_hm: str,
    global_runner_busy: bool,
) -> bool:
    """Return runner busy state for one session without blocking on a later session.

    Once the session window has ended, a completed latest run for this session and
    a later run in the same date folder prove that the next session owns any
    remaining runner activity. In that case the current session is reportable
    even while the global runner is still active.
    """
    if not global_runner_busy or not session_runs:
        return global_runner_busy

    latest_hhmmss, latest_run_name = max(session_runs, key=lambda item: item[0])
    completed_after_window = _is_session_manifest_completed(date_live, latest_run_name, win_end_hm)
    if not completed_after_window:
        return global_runner_busy

    has_later_run = _has_later_session_run_started(date_live, latest_run_name, latest_hhmmss)
    decision = False if has_later_run else global_runner_busy
    logger.info(
        "[WATCHDOG_BUSY_TELEMETRY] session_latest_run=%s completed_after_window=%s has_later_run=%s decision_busy=%s",
        latest_run_name,
        completed_after_window,
        has_later_run,
        decision,
    )
    return decision


def can_report_session(
    is_today: bool,
    completed_expected_count: int,
    expected_count: int,
    now_hm: str,
    window_end_hm: str,
    runner_busy: bool,
    has_unattempted_locked: bool = False,
    latest_run_minutes_ago: float = None,
) -> bool:
    """Xác định điều kiện chốt báo cáo cho một phiên."""
    # Nếu đang trong ngày hôm nay và runner/uploader vẫn đang bận: TUYỆT ĐỐI KHÔNG chốt sớm
    if is_today and runner_busy:
        return False

    # Nếu tất cả máy dự kiến đã hoàn tất thật (không còn lock dở dang): chốt ngay kể cả runner_busy
    if completed_expected_count >= expected_count and not has_unattempted_locked:
        return True

    # Nếu đang trong giờ phiên (now_hm < window_end_hm):
    if is_today and now_hm < window_end_hm:
        if runner_busy:
            return False
        # Nếu toàn bộ fail / chưa có máy pass (completed_expected_count == 0) và run mới nhất >= 15 phút
        if completed_expected_count == 0 and latest_run_minutes_ago is not None and latest_run_minutes_ago >= 15:
            return True
        if has_unattempted_locked:
            return False
        return completed_expected_count >= expected_count

    # Khi đã qua window_end_hm: nếu là hôm nay, TUYỆT ĐỐI KHÔNG chốt khi runner vẫn đang bận (phải đợi xong hẳn)
    if is_today and now_hm >= window_end_hm:
        if runner_busy:
            return False

    # Nếu là hôm qua (is_today=False): chỉ cho phép báo cáo sau 02:00 sáng hôm nay để tránh chốt vội phiên đêm đang chạy dở
    if not is_today:
        if now_hm < "02:00" and completed_expected_count < expected_count:
            return False
        return True

    # Khi runner không bận (đã xong hoàn toàn batch): BẮT BUỘC chốt báo cáo
    return True


def dispatch_split_reports(header: str, cluster_blocks: list[str], cluster_stats: list[dict] | None = None, win_name: str = "", active_row: Any = "") -> str:
    feed_p, fl_p, up_p = [], [], []
    for b in cluster_blocks:
        lines = b.splitlines()
        hdr = [l for l in lines if l.startswith("🏢") or l.startswith("• Tổng máy")]
        sec = lambda kw: next((lines[i:next((j for j in range(i+1, len(lines)) if lines[j].startswith("• ")), len(lines))] for i, l in enumerate(lines) if l.startswith(f"• {kw}")), [])
        fl_s, up_s = sec("Follow chéo"), sec("Đăng Video")
        f_s = [l for l in lines if l not in fl_s and l not in up_s and not l.startswith("• Follow chéo") and not l.startswith("• Đăng Video")]
        if f_s: feed_p.append("\n".join(f_s))
        if fl_s: fl_p.append("\n".join(hdr + fl_s))
        if up_s: up_p.append("\n".join(hdr + up_s))
    st = cluster_stats or []
    tot_fl = sum(len(b.get("fl_error", [])) for b in st)
    tot_up = sum(len(b.get("up_error", [])) + len(b.get("up_timeout", [])) for b in st)
    fl_hdr = f"🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT ({tot_fl} máy lỗi script Follow) - {win_name} (Row {active_row})" if tot_fl >= DEFAULT_FARM_ALERT_THRESHOLD else f"📊 [TIKTOK FOLLOW] {win_name} hoàn tất (Row {active_row})"
    up_hdr = f"🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT ({tot_up} máy lỗi script Upload) - {win_name} (Row {active_row})" if tot_up >= DEFAULT_FARM_ALERT_THRESHOLD else f"📊 [TIKTOK VIDEO] {win_name} hoàn tất (Row {active_row})"
    feed_hdr = f"📊 [TIKTOK NUÔI ACC] {win_name} hoàn tất (Row {active_row})" if win_name else header
    try:
        from automation_core.alerts import _load_bot_token
        import urllib.request, urllib.parse
        t = _load_bot_token()
        for cid, hdr, parts in [("-5435853713", up_hdr, up_p)]:
            if t and parts:
                full_msg = hdr + "\n\n" + "\n\n".join(parts)
                # Tự động chia nhỏ tin nhắn nếu vượt giới hạn 4000 ký tự của Telegram
                chunks = []
                if len(full_msg) <= 4000:
                    chunks = [full_msg]
                else:
                    curr_lines = []
                    curr_len = 0
                    for line in full_msg.splitlines(keepends=True):
                        if curr_len + len(line) > 3900:
                            chunks.append("".join(curr_lines))
                            curr_lines = [line]
                            curr_len = len(line)
                        else:
                            curr_lines.append(line)
                            curr_len += len(line)
                    if curr_lines:
                        chunks.append("".join(curr_lines))

                for chunk in chunks:
                    body = urllib.parse.urlencode({"chat_id": cid, "text": chunk}).encode("utf-8")
                    urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{t}/sendMessage", data=body), timeout=10)
                logger.info("[WATCHDOG_TELEGRAM_DISPATCH_SUCCESS] chat_id=%s hdr=%s chunks=%d", cid, hdr, len(chunks))
    except Exception as exc:
        logger.warning("[WATCHDOG_TELEGRAM_DISPATCH_FAIL] err=%s", exc)
    return feed_hdr + "\n\n" + "\n\n".join(feed_p)


def format_follow_report_from_blocks(cluster_blocks: list[str], cluster_stats: list[dict] | None = None, win_name: str = "", active_row: Any = "") -> str:
    fl_p = []
    for b in cluster_blocks:
        lines = b.splitlines()
        hdr = [l for l in lines if l.startswith("🏢") or l.startswith("• Tổng máy")]
        sec = lambda kw: next((lines[i:next((j for j in range(i+1, len(lines)) if lines[j].startswith("• ")), len(lines))] for i, l in enumerate(lines) if l.startswith(f"• {kw}")), [])
        fl_s = sec("Follow chéo")
        if fl_s:
            fl_p.append("\n".join(hdr + fl_s))
    st = cluster_stats or []
    tot_fl = sum(len(b.get("fl_error", [])) for b in st)
    fl_hdr = f"🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT FOLLOW HÀNG LOẠT ({tot_fl} máy lỗi script Follow) - {win_name} (Row {active_row})" if tot_fl >= DEFAULT_FARM_ALERT_THRESHOLD else f"📊 [TIKTOK FOLLOW] {win_name} hoàn tất (Row {active_row})"
    return fl_hdr + "\n\n" + "\n\n".join(fl_p)


def main(mode: str = "feed"):
    now = datetime.now(HCMC)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    now_hm = now.strftime("%H:%M")

    target_state_file = FOLLOW_STATE_FILE if mode == "follow" else STATE_FILE
    lock = ProcessLock(f"{target_state_file}.proc_lock")
    if not lock.acquire():
        return
    logger.info("[%s_WATCHDOG_START_TELEMETRY] mode=%s state_file=%s", mode.upper(), mode, os.path.basename(target_state_file))

    try:
        # Load state
        reported = _load_reported_sessions(target_state_file)
        messages = []
        new_reported = set(reported)
        runner_busy = is_feed_runner_active()

        # Check all unreported date folders within a 7-day retention window up to today
        retention_cutoff = (now.date() - timedelta(days=7)).isoformat()
        all_date_dirs = sorted([
            d for d in os.listdir(LIVE_ROOT)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= retention_cutoff and os.path.isdir(os.path.join(LIVE_ROOT, d))
        ]) if os.path.exists(LIVE_ROOT) else []

        dates_to_check = [(d, d == today) for d in all_date_dirs]

        for target_date, is_today in dates_to_check:
            try:
                d_obj = datetime.fromisoformat(target_date)
                default_row = 1 if (d_obj.day % 2 != 0) else 2
            except Exception:
                default_row = 1

            for win in SESSION_WINDOWS:
                session_key = f"{target_date}_ca{win['ca']}_phien{win.get('phien', 1)}"
                if session_key in new_reported:
                    continue

                cluster_blocks = []
                cluster_stats = []
                active_row = default_row
                can_report_all = True

                for cluster in CLUSTERS:
                    c_live = cluster.get("live_root")
                    if not c_live or not os.path.exists(c_live):
                        continue
                    date_live = os.path.join(c_live, target_date)
                    if not os.path.exists(date_live):
                        continue

                    runs = sorted(os.listdir(date_live))
                    session_runs = []
                    for r in runs:
                        parts = r.split("-")
                        if len(parts) >= 3 and parts[0] == "row":
                            hhmmss = parts[2]
                            if len(hhmmss) >= 4:
                                r_hm = f"{hhmmss[:2]}:{hhmmss[2:4]}"
                                if win["end"] == "24:00" or win["end"] == "00:00":
                                    in_window = (r_hm >= win["start"])
                                else:
                                    in_window = (win["start"] <= r_hm < win["end"])
                                if in_window:
                                    session_runs.append((hhmmss, r))

                    if not session_runs:
                        block_lines = [
                            f"🏢 【{cluster['label']}】",
                            "• Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)",
                        ]
                        cluster_blocks.append("\n".join(block_lines))
                        continue

                    session_runs.sort(key=lambda x: x[0])
                    sorted_run_names = [x[1] for x in session_runs]

                    c_active_row = default_row
                    for r_name in reversed(sorted_run_names):
                        r_parts = r_name.split("-")
                        if len(r_parts) >= 3 and r_parts[0] == "row":
                            try:
                                c_active_row = int(r_parts[1])
                                break
                            except (ValueError, TypeError):
                                continue

                    active_row = c_active_row

                    all_machines = {}
                    all_follows = {}
                    all_uploads = {}
                    for r in sorted_run_names:
                        parts = r.split("-")
                        if len(parts) >= 3 and parts[0] == "row":
                            try:
                                r_row = int(parts[1])
                            except (ValueError, TypeError):
                                continue
                            if r_row != active_row:
                                continue
                        r_path = os.path.join(date_live, r)
                        m_res, f_res, u_res = parse_run_all(r_path)
                        for m, data in m_res.items():
                            all_machines[m] = merge_machine_result(all_machines.get(m), data)
                        for m, data in f_res.items():
                            all_follows[m] = merge_follow_result(all_follows.get(m), data)
                        for m, data in u_res.items():
                            all_uploads[m] = merge_upload_result(all_uploads.get(m), data)

                    if not all_machines:
                        continue

                    expected_machines = get_expected_machines_for_cluster(cluster, active_row)
                    expected_count = len(expected_machines)
                    real_completed = {
                        m for m in all_machines.keys()
                        if not is_device_locked_skip(all_machines.get(m))
                    }
                    completed_expected = real_completed.intersection(expected_machines)
                    has_unattempted_locked = any(is_device_locked_skip(all_machines.get(m)) for m in expected_machines if m in all_machines)

                    latest_run_minutes_ago = None
                    if is_today and session_runs:
                        latest_hhmmss = session_runs[-1][0]
                        try:
                            latest_run_dt = datetime.strptime(f"{target_date} {latest_hhmmss}", "%Y-%m-%d %H%M%S").replace(tzinfo=HCMC)
                            latest_run_minutes_ago = (now - latest_run_dt).total_seconds() / 60.0
                        except Exception:
                            pass

                    can_rep = can_report_session(
                        is_today=is_today,
                        completed_expected_count=len(completed_expected),
                        expected_count=expected_count,
                        now_hm=now_hm,
                        window_end_hm=win["end"],
                        runner_busy=is_cluster_session_busy(
                            date_live=date_live,
                            session_runs=session_runs,
                            win_end_hm=win["end"],
                            global_runner_busy=runner_busy,
                        ),
                        has_unattempted_locked=has_unattempted_locked,
                        latest_run_minutes_ago=latest_run_minutes_ago,
                    )

                    if not can_rep:
                        can_report_all = False
                        break

                    def num_key(s):
                        nums = re.findall(r"\d+", str(s))
                        return int(nums[0]) if nums else 0

                    fleet_machines = {str(i) for i in range(cluster["fleet_min"], cluster["fleet_max"] + 1)}
                    for fm in fleet_machines:
                        if fm not in all_machines:
                            if fm not in expected_machines:
                                all_machines[fm] = {"status": "skipped-empty", "reason": f"account row {active_row} is empty (no username)"}
                            else:
                                all_machines[fm] = {"status": "fail", "reason": "no-run-recorded"}

                    succ = sorted([m for m, d in all_machines.items() if d.get("status") == "success"], key=num_key)
                    empty = sorted([
                        m for m, d in all_machines.items()
                        if d.get("status") == "skipped-empty"
                        or any(k in str(d.get("reason", "")).lower() for k in ("is empty (no username)", "does not have valid row"))
                        or (str(d.get("reason", "")) == "batch-config-error" and m not in expected_machines)
                        or (m not in expected_machines and d.get("status") != "success")
                    ], key=num_key)
                    fail = sorted([
                        f"M{m}" for m, d in all_machines.items()
                        if d.get("status") != "success" and m not in empty
                    ], key=num_key)
                    total_machines = len(all_machines)

                    succ_str = ", ".join(succ) if succ else "Không có"
                    fail_str = ", ".join(fail) if fail else "Không có"
                    empty_str = ", ".join(empty) if empty else "Không có"

                    feed_fail_detail_lines = []
                    if fail:
                        fail_groups: dict[str, list[str]] = {}
                        for m_label in fail:
                            raw_m = m_label[1:] if m_label.startswith("M") else m_label
                            r_text = all_machines.get(raw_m, {}).get("reason", "")
                            cat = classify_feed_failure(r_text)
                            fail_groups.setdefault(cat, []).append(m_label)
                        for cat, m_list in fail_groups.items():
                            feed_fail_detail_lines.append(f"    - {cat} ({len(m_list)}): {', '.join(m_list)}")

                    tot_swipes = sum(d.get("swipes", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fy_likes = sum(d.get("likes", {}).get("for-you", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fl_likes = sum(d.get("likes", {}).get("following", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fr_likes = sum(d.get("likes", {}).get("friends", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_likes = tot_fy_likes + tot_fl_likes + tot_fr_likes
                    tot_rate = (tot_likes / tot_swipes * 100.0) if tot_swipes > 0 else 0.0

                    tot_fy_swipes = sum(d.get("feed_counts", {}).get("for-you", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fl_swipes = sum(d.get("feed_counts", {}).get("following", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fr_swipes = sum(d.get("feed_counts", {}).get("friends", 0) for m, d in all_machines.items() if d.get("status") == "success")

                    fy_rate_str = f"{(tot_fy_likes / tot_fy_swipes * 100.0):.1f}%" if tot_fy_swipes > 0 else "0.0%"
                    fr_rate_str = f"{(tot_fr_likes / tot_fr_swipes * 100.0):.1f}%" if tot_fr_swipes > 0 else "0.0%"
                    fl_rate_str = f"{(tot_fl_likes / tot_fl_swipes * 100.0):.1f}%" if tot_fl_swipes > 0 else "0.0%"

                    tot_comment_peeks = sum(d.get("comment_peeks", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_comment_rate = (tot_comment_peeks / tot_swipes * 100.0) if tot_swipes > 0 else 0.0

                    total_followed_count = 0
                    total_m1_count = 0
                    total_m2_count = 0
                    fl_success = []
                    fl_released = []
                    fl_breaker = []
                    fl_error = []
                    fl_rest = []
                    fl_under6 = []
                    fl_other_skipped = []

                    for m in sorted(all_machines.keys(), key=num_key):
                        if m in all_follows:
                            fd = all_follows[m]
                            flist = fd.get("followed", []) if isinstance(fd.get("followed"), list) else []
                            total_followed_count += len(flist)
                            total_m1_count += int(fd.get("mode1_followed_count", 0) or 0)
                            total_m2_count += int(fd.get("mode2_followed_count", 0) or 0)
                            
                            category, _ = classify_machine_follow_result(fd)
                            if category == "released":
                                fl_released.append(m)
                            elif category == "breaker_skipped":
                                fl_breaker.append(m)
                            elif category == "success":
                                fl_success.append(m)
                            elif category == "rest":
                                fl_rest.append(m)
                            elif category == "under_video_gate":
                                fl_under6.append(m)
                            elif category == "error":
                                fl_error.append(m)
                                logger.warning(
                                    "[FOLLOW_WATCHDOG_TELEMETRY] event=follow_error_classified machine=%s status=%s reason=%s degraded=%s fl_error_count=%d",
                                    m, fd.get("status"), fd.get("reason"), bool(fd.get("details", {}).get("mode2_degraded")), len(fl_error)
                                )
                            else:
                                fl_other_skipped.append(m)
                        else:
                            if all_machines[m].get("status") == "success":
                                fl_error.append(m)

                    if fl_error:
                        fl_err_reasons = {}
                        for m in fl_error:
                            r_text = str(all_follows.get(m, {}).get("reason") or all_machines.get(m, {}).get("reason") or "Lỗi không xác định").strip()
                            lbl = classify_error_reason(r_text)
                            fl_err_reasons.setdefault(lbl, []).append(f"M{m}" if not str(m).startswith("M") else str(m))
                        e_str = "; ".join(f"{r} ({len(m_list)}: {', '.join(m_list)})" for r, m_list in fl_err_reasons.items())
                    else:
                        e_str = "Không có"

                    fl_skip_parts = []
                    if fl_rest:
                        fl_skip_parts.append(f"Đang dưỡng sinh ({len(fl_rest)})")
                    if fl_breaker:
                        fl_skip_parts.append(f"Khóa IP do máy cùng IP nhả ({len(fl_breaker)}: {', '.join(f'M{m}' for m in fl_breaker)})")
                    if fl_under6:
                        fl_skip_parts.append(f"Chưa đủ điều kiện ({len(fl_under6)})")
                    if fl_other_skipped:
                        reasons_map = {}
                        for m_val in fl_other_skipped:
                            r_text = str(all_follows.get(m_val, {}).get("reason") or all_machines.get(m_val, {}).get("reason") or "").strip()
                            r_lower = r_text.lower()
                            if "cooldown" in r_lower:
                                lbl = "Cooldown nhả follow"
                            elif "follow-released" in r_lower or "nhả" in r_lower:
                                lbl = "Bị nhả follow"
                            elif "đã follow sẵn" in r_lower or "already-followed" in r_lower:
                                lbl = "Đã follow sẵn"
                            elif "sensitive" in r_lower:
                                lbl = "Feed chưa ổn định"
                            elif r_text:
                                lbl = classify_error_reason(r_text)
                            else:
                                lbl = "Khác"
                            reasons_map.setdefault(lbl, []).append(m_val)
                        for lbl, m_list in reasons_map.items():
                            fl_skip_parts.append(f"{lbl} ({len(m_list)})")
                    fl_skip_summary = "; ".join(fl_skip_parts) if fl_skip_parts else "Không có"
                    total_fl_skipped = len(fl_rest) + len(fl_breaker) + len(fl_under6) + len(fl_other_skipped)

                    valid_tot_nat, valid_fy_nat, valid_fl_nat, valid_fr_nat, dropped_tot_nat = calculate_session_natural_follows(
                        all_machines, all_follows, fl_released
                    )
                    valid_nat_rate = (valid_tot_nat / tot_swipes * 100.0) if tot_swipes > 0 else 0.0
                    if dropped_tot_nat > 0:
                        nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}] (Đã tự trừ {dropped_tot_nat} lượt do nick bị nhả/drop)"
                    else:
                        nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}]"

                    block_lines = [
                        f"🏢 【{cluster['label']}】",
                        f"• Tổng máy xử lý: {total_machines} máy",
                        f"• Lướt Feed:",
                        f"  + Success ({len(succ)}): {succ_str}",
                        f"  + Fail ({len(fail)}): {fail_str}",
                    ]
                    if feed_fail_detail_lines:
                        block_lines.extend(feed_fail_detail_lines)
                    block_lines.extend([
                        f"  + Trống slot/chưa có nick ({len(empty)}): {empty_str}",
                        f"  + Thả tim: {tot_likes} tim / {tot_swipes} video ({tot_rate:.1f}%) [Đề xuất: {tot_fy_likes} ({fy_rate_str}) | Bạn bè: {tot_fr_likes} ({fr_rate_str}) | Following: {tot_fl_likes} ({fl_rate_str})]",
                        nat_follow_line,
                        f"  + Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)",
                    ])

                    if fl_rest:
                        rest_m_str = ", ".join(fl_rest)
                        block_lines.extend([
                            f"• Chế độ Dưỡng Sinh (Organic Rest ~33%):",
                            f"  🌿 Nghỉ dưỡng sinh ({len(fl_rest)} máy): {rest_m_str} (Chỉ lướt feed, 0 follow, 0 up)"
                        ])

                    total_fl_candidates = len(fl_success) + len(fl_released)
                    block_lines.append(f"• Follow chéo ({total_followed_count} lượt follow) [Module 2 (Anchor): {total_m2_count} | Module 1 (Bù): {total_m1_count}]:")
                    block_lines.extend(format_success_follows(fl_success, all_follows, total_attempt=total_fl_candidates))
                    save_session_action_stats(
                        db_path=r"D:/Taadaa/data/tiktok_tracker.db",
                        session_key=session_key,
                        cluster_name=cluster.get("name", "unknown"),
                        target_date=target_date,
                        internal_fl=total_followed_count,
                        natural_fl=valid_tot_nat,
                        likes=tot_likes,
                        swipes=tot_swipes,
                    )
                    end_time_str = "23:59:59" if win["end"] in {"24:00", "00:00"} else f"{win['end']}:00"
                    reconcile_lines = reconcile_cluster_following(
                        cluster, fl_success, all_follows, active_row,
                        session_start_iso=f"{target_date} {win['start']}:00",
                        session_end_iso=f"{target_date} {end_time_str}",
                        all_machines=all_machines,
                        session_key=session_key,
                    )
                    if reconcile_lines:
                        block_lines.extend(reconcile_lines)
                    block_lines.extend(format_released_follows(fl_released, all_follows, total_attempt=total_fl_candidates))
                    # Cầu dao IP: chỉ xuất ở cụm liên quan để tránh lặp trùng
                    if cluster.get("name") == "kibe":
                        cb_lines = format_ip_circuit_breaker_report(r"D:/Taadaa/data/tiktok_tracker.db", target_date=target_date)
                        if cb_lines:
                            block_lines.extend(cb_lines)
                    block_lines.extend([
                        f"  + Lỗi script/xác minh ({len(fl_error)}): {e_str}",
                        f"  + Bỏ qua ({total_fl_skipped}): {fl_skip_summary}"
                    ])

                    if any(all_uploads.values()):
                        up_success = []
                        up_timeout = []
                        up_error = []
                        up_rest = []
                        up_novideo = []
                        up_other_skipped = []

                        for m in sorted(all_machines.keys(), key=num_key):
                            if m in all_uploads:
                                ud = all_uploads[m]
                                u_status = str(ud.get("status") or "").lower()
                                u_code = int(ud.get("exit_code", 0) or 0)
                                u_reason = str(ud.get("reason") or "").lower()

                                if u_status == "success" and u_code == 0:
                                    up_success.append(m)
                                elif u_reason.startswith("already_uploaded") and is_machine_upload_successful_in_shift(target_date, m, active_row):
                                    up_success.append(m)
                                elif "organic-rest-day" in u_reason or "rest-day" in u_reason:
                                    up_rest.append(m)
                                elif any(k in u_reason for k in ("video_not_rendered", "missing_video_folder")):
                                    up_novideo.append(m)
                                elif u_status == "skipped" or any(k in u_reason for k in ("missing_account_id", "not-final-session", "sensitive-skip", "cooling_period", "account_cooling_period", "age_gate", "under_10_days", "already_uploaded")):
                                    up_other_skipped.append(m)
                                elif "timeout" in u_status or "timeout" in u_reason:
                                    up_timeout.append(m)
                                else:
                                    up_error.append(m)
                            else:
                                if is_machine_upload_successful_in_shift(target_date, m, active_row):
                                    up_success.append(m)
                                elif m in fl_rest:
                                    up_rest.append(m)
                                elif all_machines[m].get("status") == "success":
                                    up_error.append(m)

                        up_s_str = ", ".join(up_success) if up_success else "Không có"
                        up_t_str = ", ".join(up_timeout) if up_timeout else "Không có"
                        up_e_str = ", ".join(up_error) if up_error else "Không có"

                        up_skip_parts = []
                        if up_rest:
                            up_skip_parts.append(f"Đang dưỡng sinh ({len(up_rest)})")
                        if up_other_skipped:
                            up_skip_parts.append(f"Khác ({len(up_other_skipped)})")
                        up_skip_summary = "; ".join(up_skip_parts) if up_skip_parts else "Không có"
                        total_up_skipped = len(up_rest) + len(up_other_skipped)

                        block_lines.extend([
                            f"• Đăng Video ({win['phien']}/2 - {len(up_success)} video đã đăng):",
                            f"  + Success ({len(up_success)}): {up_s_str}",
                            f"  + Timeout/Quá giờ ({len(up_timeout)}): {up_t_str}",
                            f"  + Lỗi script/xác minh ({len(up_error)}): {up_e_str}",
                        ])
                        if up_novideo:
                            block_lines.append(f"  + Hết video/Cần cào ({len(up_novideo)}): {', '.join(up_novideo)}")
                        block_lines.append(f"  + Bỏ qua ({total_up_skipped}): {up_skip_summary}")

                    try:
                        c_live = cluster.get("live_root")
                        if c_live and os.path.exists(c_live):
                            n_sum, stv = get_row_nurture_summary(live_root=c_live, threshold_h=STARVATION_THRESHOLD_H)
                            block_lines.append(f"🌾 Sức khỏe 8 Row (Chu kỳ 4 ngày): {n_sum}")
                            if stv:
                                stv_str = ", ".join(f"Row {r}" for r in stv)
                                block_lines.append(f"  🚨 CẢNH BÁO BỎ ĐÓI: {stv_str} > {STARVATION_THRESHOLD_H:g}h chưa nuôi thành công!")
                    except Exception as nurture_err:
                        logger.warning("[NURTURE_SUMMARY_FAIL] cluster=%s err=%s", cluster.get("name"), nurture_err)

                    cluster_blocks.append("\n".join(block_lines))
                    cluster_stats.append({
                        "fl_error": fl_error if 'fl_error' in locals() else [],
                        "up_error": up_error if 'up_error' in locals() else [],
                        "up_timeout": up_timeout if 'up_timeout' in locals() else [],
                    })

                has_any_cluster_runs = any("• Tổng máy xử lý:" in b for b in cluster_blocks)
                if cluster_blocks and can_report_all and has_any_cluster_runs:
                    # Bắn Farm Alert khi phát hiện lỗi script hàng loạt (>= 8 máy ~ 10% farm dính lỗi follow hoặc upload)
                    has_script_alert = False
                    alert_reasons = []
                    # Tính tổng lỗi follow & upload của các cụm
                    tot_fl_err = sum(len(b.get("fl_error", [])) for b in cluster_stats)
                    tot_up_err = sum(len(b.get("up_error", [])) + len(b.get("up_timeout", [])) for b in cluster_stats)
                    has_script_alert, alert_reasons = should_trigger_farm_alert(tot_fl_err, tot_up_err, DEFAULT_FARM_ALERT_THRESHOLD)
                    logger.info(
                        "[FARM_ALERT_THRESHOLD_TELEMETRY] Evaluating alert trigger: fl_err=%d up_err=%d threshold=%d alert_triggered=%s reasons=%s",
                        tot_fl_err, tot_up_err, DEFAULT_FARM_ALERT_THRESHOLD, has_script_alert, alert_reasons
                    )

                    if mode == "follow":
                        msg = format_follow_report_from_blocks(cluster_blocks, cluster_stats, win['name'], active_row)
                    else:
                        if has_script_alert:
                            header = f"🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT ({', '.join(alert_reasons)}) - {win['name']} (Row {active_row})"
                        else:
                            header = f"📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})"
                        msg = dispatch_split_reports(header, cluster_blocks, cluster_stats, win['name'], active_row)
                    messages.append(msg)
                    new_reported.add(session_key)
                    break
                if messages:
                    break
        if messages:
            # Atomic claim và persist state
            state_written = False
            try:
                current_reported = _load_reported_sessions(target_state_file)
                combined = sorted(current_reported.union(new_reported))
                current_state = {"reported_sessions": combined}
                tmp = f"{target_state_file}.{os.getpid()}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(current_state, f, ensure_ascii=False, indent=2)
                os.replace(tmp, target_state_file)
                state_written = True
            except Exception:
                pass

            if state_written:
                logger.info(
                    "[%s_WATCHDOG_DELIVERY_TELEMETRY] event=one_message_delivered mode=%s session_key=%s",
                    mode.upper(),
                    mode,
                    list(new_reported - current_reported),
                )
                print(messages[0])

    finally:
        lock.release()


if __name__ == "__main__":
    mode_arg = "feed"
    if len(sys.argv) > 1 and any(arg in sys.argv[1].lower() for arg in ("follow", "--mode=follow")):
        mode_arg = "follow"
    main(mode=mode_arg)
