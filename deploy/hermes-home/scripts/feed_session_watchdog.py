import os
# Prevent OpenBLAS/MKL memory allocation failure on high-core hosts (56 cores)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import subprocess
"""Watchdog báo cáo kết quả nuôi TikTok theo từng CA (1 spawn per Ca).

Một ngày có 4 Ca, runner spawn MỘT LẦN duy nhất tại giờ bắt đầu Ca:
- Ca 1 (Sáng): 06:00 - 12:00 -> Row 1/2, artifact row-X-0600XX
- Ca 2 (Trưa): 12:00 - 18:00 -> Row 3/4, artifact row-X-1200XX
- Ca 3 (Tối): 18:00 - 00:00 -> Row 5/6, artifact row-X-1800XX
- Ca 4 (Đêm): 00:00 - 06:00 -> Row 7/8, artifact row-X-0000XX

Cơ chế thông minh:
- Đọc danh sách target machines theo Row từ config (hoặc số máy dự kiến).
- Theo dõi tiến trình máy thật: Khi runner đã dừng và TẤT CẢ máy trong Ca đã hoàn tất (hoặc Ca hết giờ):
  -> Gửi đúng 1 BÁO CÁO TỔNG KẾT CA đầy đủ: gộp LƯỚT FEED, FOLLOW HOOK, UPLOAD HOOK.
  -> Nếu tỷ lệ lỗi > 30% (manual + blocked-proxy + failed / total) -> gửi RED ALERT.
"""
import os
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


def get_expected_machines_for_cluster(cluster: dict[str, Any], row_num: Any) -> set[str]:
    wb_path = cluster.get("account_workbook")
    fleet = {str(i) for i in range(cluster["fleet_min"], cluster["fleet_max"] + 1)}
    if not wb_path or not os.path.exists(wb_path):
        return fleet
    try:
        import openpyxl
        wb = openpyxl.load_workbook(wb_path, read_only=True)
        ws = wb.active
        machine_slots: dict[str, list[Any]] = {}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or r[0] is None:
                continue
            try:
                m_str = str(int(str(r[0]).strip()))
            except (ValueError, TypeError):
                continue
            machine_slots.setdefault(m_str, []).append(r[2] if len(r) > 2 else None)
        slot_idx = int(row_num) - 1
        expected = set()
        for m_str in fleet:
            slots = machine_slots.get(m_str, [])
            if slot_idx < len(slots):
                val = slots[slot_idx]
                if val and str(val).strip() and str(val).strip().lower() != "none":
                    expected.add(m_str)
        return expected if expected else fleet
    except Exception as exc:
        logger.warning("Error reading safe workbook for %s: %s", cluster["name"], exc)
        return fleet

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


def is_pid_alive(pid: int) -> bool:
    """Check if process with pid is still running."""
    if pid <= 0:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class ProcessLock:
    """Inter-process lock using OS file locking (msvcrt on Windows, fcntl on POSIX)."""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self._file = None
        self.acquired = False

    def acquire(self) -> bool:
        if self.acquired:
            return False
        handle = None
        try:
            lock_dir = os.path.dirname(self.lock_path)
            if lock_dir:
                os.makedirs(lock_dir, exist_ok=True)
            handle = open(self.lock_path, "a+b")
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._file = handle
            self.acquired = True
            return True
        except (OSError, IOError):
            if handle:
                try:
                    handle.close()
                except Exception:
                    pass
            return False

    def release(self):
        if not self.acquired or not self._file:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        finally:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None
            self.acquired = False


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


def is_feed_runner_active() -> bool:
    """Kiểm tra có process feed runner hay powershell feed nào đang chạy không."""
    try:
        import psutil
        my_pid = os.getpid()
        runner_patterns = (
            "multi_machine_feed_session",
            "multi-machine-feed-session",
            "run-feed-session.ps1",
            "run_follow",
            "run_tiktok.py",
            "hermes_cron_runner.py",
            "tiktok_runner.py",
            "run_post.py",
            "tiktok_workflow",
            "tiktok_upload",
        )
        now_ts = time.time()
        for p in psutil.process_iter(['name', 'cmdline', 'create_time']):
            try:
                if p.pid == my_pid:
                    continue
                name = (p.info.get('name') or '').lower()
                if not name.startswith(('python', 'powershell', 'pwsh')):
                    continue
                cmd = " ".join(p.info.get('cmdline') or []).lower()
                if any(pat in cmd for pat in runner_patterns):
                    try:
                        ctime = p.info.get('create_time') or p.create_time()
                        if ctime and (now_ts - ctime) > 9000:
                            logger.warning("Bỏ qua runner zombie PID %s chạy quá 2.5h (%.1fh)", p.pid, (now_ts - ctime)/3600)
                            continue
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


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
        except Exception:
            pass
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


def is_device_locked_skip(data: Optional[Dict[str, Any]]) -> bool:
    if not data:
        return False
    status = str(data.get("status") or "").strip().lower()
    reason = str(data.get("reason") or "").strip().lower()
    return status == "skipped-device-locked" or "device-lock" in reason or "device lock active" in reason


def merge_machine_result(prev: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not prev:
        return new
    if not new:
        return prev

    res = dict(new)
    # Merge likes and swipes accumulated across runs
    p_likes = prev.get("likes") or {}
    n_likes = new.get("likes") or {}
    all_like_keys = set(p_likes.keys()) | set(n_likes.keys())
    if all_like_keys:
        merged_likes = {}
        for k in all_like_keys:
            merged_likes[k] = max(p_likes.get(k, 0), n_likes.get(k, 0))
        res["likes"] = merged_likes
    p_nf = prev.get("natural_follows") or {}
    n_nf = new.get("natural_follows") or {}
    all_nf_keys = set(p_nf.keys()) | set(n_nf.keys())
    if all_nf_keys:
        merged_nf = {}
        for k in all_nf_keys:
            merged_nf[k] = max(p_nf.get(k, 0), n_nf.get(k, 0))
        res["natural_follows"] = merged_nf
    p_fc = prev.get("feed_counts") or {}
    n_fc = new.get("feed_counts") or {}
    all_fc_keys = set(p_fc.keys()) | set(n_fc.keys())
    if all_fc_keys:
        merged_fc = {}
        for k in all_fc_keys:
            merged_fc[k] = max(p_fc.get(k, 0), n_fc.get(k, 0))
        res["feed_counts"] = merged_fc
    if "swipes" in prev or "swipes" in new:
        res["swipes"] = max(prev.get("swipes", 0), new.get("swipes", 0))

    if prev.get("status") == "success":
        res["status"] = prev.get("status")
        res["reason"] = prev.get("reason", "")
        return res
    if new.get("status") == "success":
        return res
    # Nếu prev là skipped-device-locked còn new là kết quả chạy thật (không phải lock), ưu tiên new
    if is_device_locked_skip(prev) and not is_device_locked_skip(new):
        return res
    if is_device_locked_skip(new) and not is_device_locked_skip(prev):
        res["status"] = prev.get("status")
        res["reason"] = prev.get("reason", "")
        return res
    return res


def merge_follow_result(prev: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not prev:
        return new
    if not new:
        return prev
    prev_raw = prev.get("followed", []) if isinstance(prev.get("followed"), list) else []
    new_raw = new.get("followed", []) if isinstance(new.get("followed"), list) else []
    prev_flist = [str(x) for x in prev_raw if isinstance(x, (str, int, float))]
    new_flist = [str(x) for x in new_raw if isinstance(x, (str, int, float))]
    combined_flist = list(dict.fromkeys(prev_flist + new_flist))

    m1_cnt = max(int(prev.get("mode1_followed_count", 0) or 0), int(new.get("mode1_followed_count", 0) or 0))
    m2_cnt = max(int(prev.get("mode2_followed_count", 0) or 0), int(new.get("mode2_followed_count", 0) or 0))

    prev_released = (str(prev.get("status") or "").upper() == "FOLLOW_FAILED" and prev.get("follow_failed") is True)
    new_released = (str(new.get("status") or "").upper() == "FOLLOW_FAILED" and new.get("follow_failed") is True)

    if prev_released or new_released:
        res = dict(new if new_released else prev)
        res["status"] = "FOLLOW_FAILED"
        res["follow_failed"] = True
        res["followed"] = combined_flist
        res["mode1_followed_count"] = m1_cnt
        res["mode2_followed_count"] = m2_cnt
        return res

    prev_ok = (str(prev.get("status") or "").upper() in {"OK", "SUCCESS"} and len(prev_flist) > 0)
    new_ok = (str(new.get("status") or "").upper() in {"OK", "SUCCESS"} and len(new_flist) > 0)

    if new_ok:
        res = dict(new)
        res["followed"] = combined_flist
        res["mode1_followed_count"] = m1_cnt
        res["mode2_followed_count"] = m2_cnt
        return res
    if prev_ok and str(new.get("status") or "").upper() in {"SKIPPED", "MANUAL_REVIEW"}:
        res = dict(prev)
        res["followed"] = combined_flist
        res["mode1_followed_count"] = m1_cnt
        res["mode2_followed_count"] = m2_cnt
        return res

    res = dict(new)
    res["followed"] = combined_flist
    res["mode1_followed_count"] = m1_cnt
    res["mode2_followed_count"] = m2_cnt
    return res


def merge_upload_result(prev: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not prev:
        return new
    if not new:
        return prev
    prev_success = (str(prev.get("status") or "").lower() == "success" and int(prev.get("exit_code", 0) or 0) == 0)
    new_success = (str(new.get("status") or "").lower() == "success" and int(new.get("exit_code", 0) or 0) == 0)
    if prev_success and not new_success:
        return prev
    if new_success:
        return new

    # If prev had an active attempt with failure detail and new is just a generic skip, preserve failure detail
    if str(prev.get("status") or "").lower() in {"failed", "error"} and str(new.get("status") or "").lower() == "skipped":
        return prev
    return new


def parse_run_all(run_dir: str) -> tuple:
    """Parse toàn bộ summary, follow_result, upload_result trong 1 lần duyệt đệ quy duy nhất (tốc độ cao)."""
    res_m: dict = {}
    res_f: dict = {}
    res_u: dict = {}

    if not os.path.isdir(run_dir):
        return res_m, res_f, res_u

    try:
        for root, _, files in os.walk(run_dir):
            parts = os.path.normpath(root).split(os.sep)
            m_str = ""
            for p_idx, seg in enumerate(parts):
                if seg == "machines" and p_idx + 1 < len(parts):
                    raw_segment = parts[p_idx + 1]
                    if raw_segment.startswith("machine_"):
                        m_str = raw_segment[8:]
                        break

            # Parse run_manifest.json at run root to capture all machines (including skipped-empty)
            if "run_manifest.json" in files and not m_str:
                m_path = os.path.join(root, "run_manifest.json")
                try:
                    with open(m_path, "r", encoding="utf-8", errors="ignore") as f:
                        m_data = json.load(f)
                    mms = m_data.get("multi_machine_summary") if isinstance(m_data, dict) else None
                    if isinstance(mms, list):
                        for item in mms:
                            if not isinstance(item, dict) or "machine" not in item:
                                continue
                            m_num = str(item["machine"])
                            exp_u = str(item.get("expected_username", "")).strip()
                            s_reason = str(item.get("stop_reason", "")).strip()
                            f_status = str(item.get("final_status", "")).strip().lower()
                            if exp_u == "account:empty" or "is empty (no username)" in s_reason.lower() or "does not have valid row" in s_reason.lower():
                                m_st = "skipped-empty"
                            elif f_status == "success":
                                m_st = "success"
                            else:
                                m_st = "fail"
                            payload = {
                                "status": m_st,
                                "reason": s_reason,
                                "likes": {},
                                "feed_counts": {},
                                "swipes": int(item.get("swipes_completed", 0) or 0),
                                "comment_peeks": 0,
                            }
                            res_m[m_num] = merge_machine_result(res_m.get(m_num), payload)
                except Exception:
                    pass

            # Fallback parse batched summary.txt at run root
            if "summary.txt" in files and not m_str:
                s_path = os.path.join(root, "summary.txt")
                try:
                    with open(s_path, "r", encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                    import re
                    failed_m = re.findall(r"machine_(\d+)", c)
                    for m_num in set(failed_m):
                        if m_num not in res_m:
                            res_m[m_num] = {"status": "fail", "reason": "batch-config-error"}
                except Exception:
                    pass
            if "summary.txt" in files and m_str:
                s_path = os.path.join(root, "summary.txt")
                try:
                    with open(s_path, "r", encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                    st = "success" if "final_status: success" in c else "fail"
                    reason = ""
                    for line in c.splitlines():
                        if line.startswith("reason:") or line.startswith("final_status:"):
                            val = line.split(":", 1)[1].strip()
                            if val != "success":
                                reason = val
                                break
                    if any(k in reason.lower() for k in ("is empty (no username)", "does not have valid row")):
                        st = "skipped-empty"

                    # Extract likes and swipes from per-machine summary
                    likes_map = {}
                    feed_counts_map = {}
                    swipes_cnt = 0
                    try:
                        import re
                        m_sw = re.search(r'["\']?total_swipes_completed["\']?:\s*(\d+)', c)
                        if m_sw:
                            swipes_cnt = int(m_sw.group(1))
                        idx_lc = c.find('"like_counts":')
                        if idx_lc != -1:
                            chunk_lc = c[idx_lc:idx_lc + 150]
                            for ft in ("for-you", "following", "friends"):
                                m_ft = re.search(rf'["\']?{ft}["\']?:\s*(\d+)', chunk_lc)
                                if m_ft:
                                    likes_map[ft] = int(m_ft.group(1))
                        follow_counts_map = {}
                        idx_foc = c.find('"follow_counts":')
                        if idx_foc != -1:
                            chunk_foc = c[idx_foc:idx_foc + 150]
                            for ft in ("for-you", "following", "friends"):
                                m_ft = re.search(rf'["\']?{ft}["\']?:\s*(\d+)', chunk_foc)
                                if m_ft:
                                    follow_counts_map[ft] = int(m_ft.group(1))
                        idx_fc = c.find('"feed_counts":')
                        if idx_fc != -1:
                            chunk_fc = c[idx_fc:idx_fc + 150]
                            for ft in ("for-you", "following", "friends"):
                                m_ft = re.search(rf'["\']?{ft}["\']?:\s*(\d+)', chunk_fc)
                                if m_ft:
                                    feed_counts_map[ft] = int(m_ft.group(1))
                    except Exception:
                        pass

                    comment_peeks_cnt = 0
                    try:
                        m_cp = re.search(r'["\']?comment_peeks["\']?:\s*(\d+)', c)
                        if m_cp:
                            comment_peeks_cnt = int(m_cp.group(1))
                    except Exception:
                        pass
                    m_payload = {"status": st, "reason": reason, "likes": likes_map, "feed_counts": feed_counts_map, "swipes": swipes_cnt, "comment_peeks": comment_peeks_cnt, "natural_follows": follow_counts_map}
                    res_m[m_str] = merge_machine_result(res_m.get(m_str), m_payload)
                except Exception:
                    pass

            if "follow_result.json" in files:
                f_path = os.path.join(root, "follow_result.json")
                try:
                    with open(f_path, "r", encoding="utf-8") as fp:
                        d = json.load(fp)
                    if isinstance(d, dict):
                        payload_m = str(d.get("machine", "")).strip()
                        target_m = payload_m if payload_m else m_str
                        if target_m:
                            flist_raw = d.get("followed")
                            flist = [str(x) for x in flist_raw if isinstance(x, (str, int, float))] if isinstance(flist_raw, list) else []
                            raw_status = str(d.get("status") or "").strip()
                            raw_ff = d.get("follow_failed")
                            raw_failed = d.get("failed")
                            is_strict_zero_failed = (raw_failed is False) or (type(raw_failed) is int and raw_failed == 0)
                            is_clean_ff = (raw_status == "FOLLOW_FAILED" and raw_ff is True and type(raw_ff) is bool and is_strict_zero_failed)
                            details = d.get("details") if isinstance(d.get("details"), dict) else {}
                            m1_cnt = details.get("mode1_followed_count")
                            m2_cnt = details.get("mode2_followed_count")
                            try:
                                m1_cnt = int(m1_cnt) if m1_cnt is not None else 0
                            except (ValueError, TypeError):
                                m1_cnt = 0
                            try:
                                m2_cnt = int(m2_cnt) if m2_cnt is not None else 0
                            except (ValueError, TypeError):
                                m2_cnt = 0
                            f_item = {
                                "status": raw_status,
                                "followed": flist,
                                "follow_failed": is_clean_ff,
                                "failed": raw_failed,
                                "reason": str(d.get("reason") or ""),
                                "mode1_followed_count": m1_cnt,
                                "mode2_followed_count": m2_cnt,
                            }
                            res_f[target_m] = merge_follow_result(res_f.get(target_m), f_item)
                except Exception:
                    pass

            if "upload_result.json" in files:
                u_path = os.path.join(root, "upload_result.json")
                try:
                    with open(u_path, "r", encoding="utf-8") as fp:
                        d = json.load(fp)
                    if isinstance(d, dict):
                        payload_m = str(d.get("machine", "")).strip()
                        target_m = payload_m if payload_m else m_str
                        if target_m:
                            raw_code = d.get("exit_code", d.get("returncode", 0))
                            try:
                                exit_code = int(raw_code)
                            except (ValueError, TypeError):
                                exit_code = 1 if str(d.get("status", "")).lower() != "success" else 0
                            u_item = {
                                "status": str(d.get("status") or "").lower(),
                                "exit_code": exit_code,
                                "reason": str(d.get("reason") or ""),
                            }
                            res_u[target_m] = merge_upload_result(res_u.get(target_m), u_item)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("Error during single-pass walk of %s: %s", run_dir, e)

    return res_m, res_f, res_u


def parse_run_machines(run_dir: str) -> dict:
    """Lấy map machine -> final_status từ 1 run dir (chỉ dùng cho tests / CLI riêng lẻ)."""
    return parse_run_all(run_dir)[0]


def parse_follow_results(run_dir: str) -> dict:
    """Lấy kết quả follow hook từ 1 run dir (chỉ dùng cho tests / CLI riêng lẻ)."""
    return parse_run_all(run_dir)[1]


def parse_upload_results(run_dir: str) -> dict:
    """Lấy kết quả upload hook từ 1 run dir (chỉ dùng cho tests / CLI riêng lẻ)."""
    return parse_run_all(run_dir)[2]


def _add_minutes_to_hm(hm_str: str, minutes: int) -> str:
    h, m = map(int, hm_str.split(":"))
    total = h * 60 + m + minutes
    new_h = (total // 60) % 24
    new_m = total % 60
    return f"{new_h:02d}:{new_m:02d}"


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


def reconcile_cluster_following(
    cluster: dict[str, Any],
    fl_success: list,
    all_follows: dict,
    active_row: int,
    session_start_iso: Optional[str] = None,
    db_path: str = r"D:/Taadaa/data/tiktok_tracker.db",
    python_exe: str = r"D:/Taadaa/python-envs/automation/Scripts/python.exe",
    tracker_script: str = r"D:/Taadaa/tools/tiktok_account_tracker.py",
) -> list[str]:
    """Cào và đối soát số lượng following tăng thật trên TikTok Web so với script báo cáo."""
    if not fl_success:
        return []

    wb_path = cluster.get("account_workbook")
    if not wb_path or not os.path.exists(wb_path):
        return []

    try:
        import openpyxl
        wb = openpyxl.load_workbook(wb_path, read_only=True)
        ws = wb.active
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
        return []

    slot_idx = int(active_row) - 1
    m_to_user: dict[str, str] = {}
    m_to_reported: dict[str, int] = {}

    for m in fl_success:
        cnt = len(all_follows.get(m, {}).get("followed", []))
        if cnt <= 0:
            continue
        slots = machine_slots.get(str(m), [])
        if slot_idx < len(slots):
            val = slots[slot_idx]
            if val and str(val).strip() and str(val).strip().lower() != "none":
                u = str(val).strip().lstrip('@')
                m_to_user[str(m)] = u
                m_to_reported[str(m)] = cnt

    if not m_to_user:
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
        total_reported = sum(m_to_reported.values())
        total_scraped_delta = 0
        has_valid_delta_count = 0

        def _num_m(x):
            nums = re.findall(r"\d+", str(x))
            return int(nums[0]) if nums else 0

        for m in sorted(m_to_user.keys(), key=_num_m):
            u = m_to_user[m]
            rep_cnt = m_to_reported[m]
            try:
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
                if latest_row and session_start_iso:
                    cur.execute("""
                        SELECT following, timestamp
                        FROM snapshots
                        WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
                        ORDER BY timestamp DESC, id DESC
                        LIMIT 1
                    """, (u, session_start_iso))
                    b_rows = cur.fetchall()
                    if b_rows:
                        baseline_row = b_rows[0]

                if latest_row and not baseline_row and len(pair) >= 2:
                    baseline_row = pair[1]

                if latest_row and baseline_row:
                    latest_fl = latest_row[0] or 0
                    prev_fl = baseline_row[0] or 0
                    delta = latest_fl - prev_fl
                    total_scraped_delta += delta
                    has_valid_delta_count += 1
                    diff = delta - rep_cnt
                    if diff == 0:
                        status_str = f"web tăng +{delta} (Khớp 100%)"
                    else:
                        diff_sign = f"+{diff}" if diff > 0 else f"{diff}"
                        status_str = f"web tăng {delta:+d} (Lệch {diff_sign})"
                    details.append(f"    - M{m} (@{u}): script báo {rep_cnt} | {status_str}")
                elif latest_row:
                    cur_fl = latest_row[0] or 0
                    details.append(f"    - M{m} (@{u}): script báo {rep_cnt} | web ghi nhận {cur_fl} (mốc đầu tiên)")
                else:
                    details.append(f"    - M{m} (@{u}): script báo {rep_cnt} | chưa cào được profile web")
            except Exception as err:
                details.append(f"    - M{m} (@{u}): script báo {rep_cnt} | lỗi đọc snapshot: {err}")

        try:
            conn_w = sqlite3.connect(db_path, timeout=10.0)
            cur_w = conn_w.cursor()
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
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            act_date = session_start_iso[:10] if session_start_iso else now_ts[:10]
            for m_num, u_name in m_to_user.items():
                r_cnt = m_to_reported.get(m_num, 0)
                if r_cnt > 0 and u_name:
                    cur_w.execute("""
                        INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(target_date, username) DO UPDATE SET
                            internal_follows = daily_account_actions.internal_follows + excluded.internal_follows,
                            updated_at = excluded.updated_at
                    """, (act_date, u_name.lower(), int(m_num) if str(m_num).isdigit() else None, r_cnt, now_ts))
            conn_w.commit()
            conn_w.close()
        except Exception as err:
            logger.warning("reconcile_cluster_following: không ghi được daily_account_actions: %s", err)

        conn.close()

        if has_valid_delta_count > 0:
            total_diff = total_scraped_delta - total_reported
            if total_diff == 0:
                header_reconcile = f"  + Đối soát TikTok Web (+{total_scraped_delta} Following thật - Khớp 100% so với script báo):"
            else:
                diff_sign = f"+{total_diff}" if total_diff > 0 else f"{total_diff}"
                header_reconcile = f"  + Đối soát TikTok Web ({total_scraped_delta:+d} Following thật | Lệch {diff_sign} so với script báo {total_reported}):"
            return [header_reconcile] + details
        elif details:
            return [f"  + Đối soát TikTok Web (Script báo {total_reported} lượt follow):"] + details
        return []
    except Exception as exc:
        logger.warning("reconcile_cluster_following: lỗi kết nối/đọc db: %s", exc)
        return [f"  + Đối soát TikTok Web: Lỗi truy vấn snapshot: {exc}"]


def format_success_follows(fl_success: list, all_follows: dict) -> list:
    """Phân nhóm và format danh sách các máy follow thành công theo số lượt hoàn thành."""
    if not fl_success:
        return ["  + Success (0): Không có"]

    succ_1_4 = []
    succ_5_9 = []
    succ_10_plus = []

    for m in fl_success:
        cnt = len(all_follows.get(m, {}).get("followed", []))
        if 1 <= cnt <= 4:
            succ_1_4.append((m, cnt))
        elif 5 <= cnt <= 9:
            succ_5_9.append((m, cnt))
        else:
            succ_10_plus.append((m, cnt))

    def _format_m(m) -> str:
        s = str(m).strip()
        if s.upper().startswith("M"):
            return f"M{s[1:]}"
        return f"M{s}"

    lines = [f"  + Success ({len(fl_success)} máy):"]
    if succ_1_4:
        lines.append(f"    - 1 - 4 lượt ({len(succ_1_4)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in succ_1_4)}")
    if succ_5_9:
        lines.append(f"    - 5 - 9 lượt ({len(succ_5_9)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in succ_5_9)}")
    if succ_10_plus:
        lines.append(f"    - 10+ lượt ({len(succ_10_plus)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in succ_10_plus)}")
    return lines


def format_released_follows(fl_released: list, all_follows: dict) -> list:
    """Phân nhóm và format danh sách các máy bị nhả follow theo số lượt hoàn thành."""
    if not fl_released:
        return ["  + Nhả follow (0): Không có"]

    rel_0 = []
    rel_1_4 = []
    rel_5_9 = []
    rel_10_plus = []

    for m in fl_released:
        cnt = len(all_follows.get(m, {}).get("followed", []))
        if cnt == 0:
            rel_0.append(m)
        elif 1 <= cnt <= 4:
            rel_1_4.append((m, cnt))
        elif 5 <= cnt <= 9:
            rel_5_9.append((m, cnt))
        else:
            rel_10_plus.append((m, cnt))

    def _format_m(m: Any) -> str:
        s = str(m).strip()
        if s.upper().startswith("M"):
            return f"M{s[1:]}"
        return f"M{s}"

    lines = [f"  + Nhả follow ({len(fl_released)} máy):"]
    if rel_0:
        lines.append(f"    - Nhả liền (0 lượt - {len(rel_0)} máy): {', '.join(_format_m(m) for m in rel_0)}")
    if rel_1_4:
        lines.append(f"    - 1 - 4 lượt ({len(rel_1_4)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_1_4)}")
    if rel_5_9:
        lines.append(f"    - 5 - 9 lượt ({len(rel_5_9)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_5_9)}")
    if rel_10_plus:
        lines.append(f"    - 10+ lượt ({len(rel_10_plus)} máy): {', '.join(f'{_format_m(m)} ({cnt} lượt)' for m, cnt in rel_10_plus)}")
    return lines


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


def main():
    now = datetime.now(HCMC)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    now_hm = now.strftime("%H:%M")

    lock = ProcessLock(f"{STATE_FILE}.proc_lock")
    if not lock.acquire():
        return

    try:
        # Load state
        reported = _load_reported_sessions(STATE_FILE)
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
                        runner_busy=runner_busy,
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
                    tot_fy_nat_follows = sum(d.get("natural_follows", {}).get("for-you", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fl_nat_follows = sum(d.get("natural_follows", {}).get("following", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_fr_nat_follows = sum(d.get("natural_follows", {}).get("friends", 0) for m, d in all_machines.items() if d.get("status") == "success")
                    tot_nat_follows = tot_fy_nat_follows + tot_fl_nat_follows + tot_fr_nat_follows
                    tot_nat_follow_rate = (tot_nat_follows / tot_swipes * 100.0) if tot_swipes > 0 else 0.0

                    total_followed_count = 0
                    total_m1_count = 0
                    total_m2_count = 0
                    fl_success = []
                    fl_released = []
                    fl_error = []
                    fl_rest = []
                    fl_under10 = []
                    fl_other_skipped = []

                    for m in sorted(all_machines.keys(), key=num_key):
                        if m in all_follows:
                            fd = all_follows[m]
                            flist = fd.get("followed", [])
                            total_followed_count += len(flist)
                            total_m1_count += int(fd.get("mode1_followed_count", 0) or 0)
                            total_m2_count += int(fd.get("mode2_followed_count", 0) or 0)
                            status = str(fd.get("status") or "").upper()
                            f_reason = str(fd.get("reason") or "").lower()

                            if status == "FOLLOW_FAILED" and fd.get("follow_failed") is True:
                                fl_released.append(m)
                            elif status == "SKIPPED" or (status in {"OK", "SUCCESS"} and len(flist) == 0):
                                if "organic-rest-day" in f_reason or "rest-day" in f_reason:
                                    fl_rest.append(m)
                                elif "under-10-videos" in f_reason or "under_10_videos" in f_reason:
                                    fl_under10.append(m)
                                else:
                                    fl_other_skipped.append(m)
                            elif status in {"OK", "SUCCESS"} and len(flist) > 0:
                                fl_success.append(m)
                            else:
                                fl_error.append(m)
                        else:
                            if all_machines[m].get("status") == "success":
                                fl_error.append(m)

                    e_str = ", ".join(fl_error) if fl_error else "Không có"

                    fl_skip_parts = []
                    if fl_rest:
                        fl_skip_parts.append(f"Đang dưỡng sinh ({len(fl_rest)})")
                    if fl_under10:
                        fl_skip_parts.append(f"Chưa đủ 10 video ({len(fl_under10)})")
                    if fl_other_skipped:
                        fl_skip_parts.append(f"Khác ({len(fl_other_skipped)})")
                    fl_skip_summary = "; ".join(fl_skip_parts) if fl_skip_parts else "Không có"
                    total_fl_skipped = len(fl_rest) + len(fl_under10) + len(fl_other_skipped)

                    block_lines = [
                        f"🏢 【{cluster['label']}】",
                        f"• Tổng máy xử lý: {total_machines} máy",
                        f"• Lướt Feed:",
                        f"  + Success ({len(succ)}): {succ_str}",
                        f"  + Fail ({len(fail)}): {fail_str}",
                        f"  + Trống slot/chưa có nick ({len(empty)}): {empty_str}",
                        f"  + Thả tim: {tot_likes} tim / {tot_swipes} video ({tot_rate:.1f}%) [Đề xuất: {tot_fy_likes} ({fy_rate_str}) | Bạn bè: {tot_fr_likes} ({fr_rate_str}) | Following: {tot_fl_likes} ({fl_rate_str})]",
                        f"  + Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]",
                        f"  + Đọc comment: {tot_comment_peeks} lượt / {tot_swipes} video ({tot_comment_rate:.1f}%)",
                    ]

                    if fl_rest:
                        rest_m_str = ", ".join(fl_rest)
                        block_lines.extend([
                            f"• Chế độ Dưỡng Sinh (Organic Rest ~33%):",
                            f"  🌿 Nghỉ dưỡng sinh ({len(fl_rest)} máy): {rest_m_str} (Chỉ lướt feed, 0 follow, 0 up)"
                        ])

                    block_lines.append(f"• Follow chéo ({total_followed_count} lượt follow) [Module 2 (Anchor): {total_m2_count} | Module 1 (Bù): {total_m1_count}]:")
                    block_lines.extend(format_success_follows(fl_success, all_follows))
                    save_session_action_stats(
                        db_path=r"D:/Taadaa/data/tiktok_tracker.db",
                        session_key=session_key,
                        cluster_name=cluster.get("name", "unknown"),
                        target_date=target_date,
                        internal_fl=total_followed_count,
                        natural_fl=tot_nat_follows,
                        likes=tot_likes,
                        swipes=tot_swipes,
                    )
                    reconcile_lines = reconcile_cluster_following(
                        cluster, fl_success, all_follows, active_row,
                        session_start_iso=f"{target_date} {win['start']}:00"
                    )
                    if reconcile_lines:
                        block_lines.extend(reconcile_lines)
                    block_lines.extend(format_released_follows(fl_released, all_follows))
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
                        if up_novideo:
                            up_skip_parts.append(f"Chưa render/thiếu video ({len(up_novideo)})")
                        if up_other_skipped:
                            up_skip_parts.append(f"Khác ({len(up_other_skipped)})")
                        up_skip_summary = "; ".join(up_skip_parts) if up_skip_parts else "Không có"
                        total_up_skipped = len(up_rest) + len(up_novideo) + len(up_other_skipped)

                        block_lines.extend([
                            f"• Đăng Video ({win['phien']}/2 - {len(up_success)} video đã đăng):",
                            f"  + Success ({len(up_success)}): {up_s_str}",
                            f"  + Timeout/Quá giờ ({len(up_timeout)}): {up_t_str}",
                            f"  + Lỗi script/xác minh ({len(up_error)}): {up_e_str}",
                            f"  + Bỏ qua ({total_up_skipped}): {up_skip_summary}"
                        ])

                    cluster_blocks.append("\n".join(block_lines))

                if cluster_blocks and can_report_all:
                    header = f"📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})"
                    msg = header + "\n\n" + "\n\n".join(cluster_blocks)
                    messages.append(msg)
                    new_reported.add(session_key)
        if messages:
            # Atomic claim và persist state
            state_written = False
            try:
                current_reported = _load_reported_sessions(STATE_FILE)
                combined = sorted(current_reported.union(new_reported))
                current_state = {"reported_sessions": combined}
                tmp = f"{STATE_FILE}.{os.getpid()}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(current_state, f, ensure_ascii=False, indent=2)
                os.replace(tmp, STATE_FILE)
                state_written = True
            except Exception:
                pass

            if state_written:
                print("\n\n".join(messages))

    finally:
        lock.release()


if __name__ == "__main__":
    main()
