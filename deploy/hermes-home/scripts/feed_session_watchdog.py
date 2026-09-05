"""Watchdog báo cáo kết quả nuôi TikTok theo từng CA / PHIÊN chuẩn xác theo tiến trình máy thật.

Một ngày có 3 Ca, mỗi Ca có 3 Phiên:
- Ca 1 (Sáng):
  + Phiên 1: Khung ~06:00 - 07:30
  + Phiên 2: Khung ~07:30 - 09:00
  + Phiên 3: Khung ~09:00 - 12:00
- Ca 2 (Chiều):
  + Phiên 1: Khung ~12:00 - 13:40
  + Phiên 2: Khung ~13:40 - 15:15
  + Phiên 3: Khung ~15:15 - 18:30
- Ca 3 (Tối):
  + Phiên 1: Khung ~18:30 - 20:15
  + Phiên 2: Khung ~20:15 - 21:45
  + Phiên 3: Khung ~21:45 - 23:59

Cơ chế thông minh:
- Đọc danh sách target machines theo Row từ config (hoặc số máy dự kiến).
- Theo dõi tiến trình máy thật: Khi TẤT CẢ các máy trong ca/phiên đã hoàn tất (hoặc phiên hết giờ và runner đã dừng hẳn):
  -> Gửi đúng 1 BÁO CÁO TỔNG KẾT PHIÊN đầy đủ: gộp cả phần LƯỚT FEED, FOLLOW HOOK và UPLOAD HOOK.
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
LIVE_ROOT = r"D:\Taadaa\runtime\kibe\live"
STATE_FILE = r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json"
SOURCE_CONFIG = r"D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json"
SHIFT_UPLOAD_LEDGER_PATH = r"C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json"

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


# Định nghĩa các khung phiên chuẩn bao phủ liên tục, không lọt khe giữa các phiên
# NOTE: 00:00 - 06:00 là khoảng thời gian farm nghỉ/bảo trì/reg acc đêm, không có phiên nuôi feed chính
# Sử dụng half-open interval [start, end) để đảm bảo không trùng boundary giữa các phiên
SESSION_WINDOWS = [
    # Ca 1
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/3 (Sáng)", "start": "06:00", "end": "07:30"},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/3 (Sáng)", "start": "07:30", "end": "09:00"},
    {"ca": 1, "phien": 3, "name": "Ca 1 - Phiên 3/3 (Sáng - Đăng video)", "start": "09:00", "end": "12:00"},
    # Ca 2
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/3 (Chiều)", "start": "12:00", "end": "13:40"},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/3 (Chiều)", "start": "13:40", "end": "15:15"},
    {"ca": 2, "phien": 3, "name": "Ca 2 - Phiên 3/3 (Chiều - Đăng video)", "start": "15:15", "end": "18:30"},
    # Ca 3
    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/3 (Tối)", "start": "18:30", "end": "20:15"},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/3 (Tối)", "start": "20:15", "end": "21:45"},
    {"ca": 3, "phien": 3, "name": "Ca 3 - Phiên 3/3 (Tối - Đăng video)", "start": "21:45", "end": "23:59"},
]


def is_feed_runner_active() -> bool:
    """Kiểm tra có process feed runner hay powershell feed nào đang chạy không."""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                if not name.startswith(('python', 'powershell', 'pwsh')):
                    continue
                cmd = " ".join(p.info.get('cmdline') or [])
                if "multi_machine_feed_session" in cmd or "run-feed-session.ps1" in cmd or "run_follow" in cmd:
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


def merge_machine_result(prev: Optional[Dict[str, Any]], new: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not prev:
        return new
    if not new:
        return prev
    if prev.get("status") == "success":
        return prev
    if new.get("status") == "success":
        return new
    return new


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

    prev_released = (str(prev.get("status") or "").upper() == "FOLLOW_FAILED" and prev.get("follow_failed") is True)
    new_released = (str(new.get("status") or "").upper() == "FOLLOW_FAILED" and new.get("follow_failed") is True)

    if prev_released or new_released:
        res = dict(new if new_released else prev)
        res["status"] = "FOLLOW_FAILED"
        res["follow_failed"] = True
        res["followed"] = combined_flist
        return res

    prev_ok = (str(prev.get("status") or "").upper() in {"OK", "SUCCESS"} and len(prev_flist) > 0)
    new_ok = (str(new.get("status") or "").upper() in {"OK", "SUCCESS"} and len(new_flist) > 0)

    if new_ok:
        res = dict(new)
        res["followed"] = combined_flist
        return res
    if prev_ok and str(new.get("status") or "").upper() in {"SKIPPED", "MANUAL_REVIEW"}:
        res = dict(prev)
        res["followed"] = combined_flist
        return res

    res = dict(new)
    res["followed"] = combined_flist
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
                    res_m[m_str] = merge_machine_result(res_m.get(m_str), {"status": st, "reason": reason})
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
                            f_item = {
                                "status": raw_status,
                                "followed": flist,
                                "follow_failed": is_clean_ff,
                                "failed": raw_failed,
                                "reason": str(d.get("reason") or ""),
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


def can_report_session(
    is_today: bool,
    completed_expected_count: int,
    expected_count: int,
    now_hm: str,
    window_end_hm: str,
    runner_busy: bool,
) -> bool:
    """Xác định điều kiện chốt báo cáo cho một phiên."""
    if is_today:
        return (completed_expected_count >= expected_count and not runner_busy) or (now_hm >= window_end_hm)
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
            date_live = os.path.join(LIVE_ROOT, target_date)
            runs = sorted(os.listdir(date_live))
            try:
                d_obj = datetime.fromisoformat(target_date)
                default_row = 1 if (d_obj.day % 2 != 0) else 2
            except Exception:
                default_row = 1

            for win in SESSION_WINDOWS:
                session_key = f"{target_date}_ca{win['ca']}_phien{win['phien']}"
                if session_key in new_reported:
                    continue

                # Tìm các run folder thuộc khung giờ phiên này và sort theo HHMMSS
                # Dùng half-open interval [start, end) để tránh đè boundary trừ window cuối ngày [start, end]
                is_last_window = (win == SESSION_WINDOWS[-1])
                session_runs = []
                for r in runs:
                    parts = r.split("-")
                    if len(parts) >= 3 and parts[0] == "row":
                        hhmmss = parts[2]
                        if len(hhmmss) >= 4:
                            r_hm = f"{hhmmss[:2]}:{hhmmss[2:4]}"
                            in_window = (win["start"] <= r_hm <= win["end"]) if is_last_window else (win["start"] <= r_hm < win["end"])
                            if in_window:
                                session_runs.append((hhmmss, r))

                if not session_runs:
                    continue

                # Sắp xếp các run theo thứ tự thời gian tăng dần
                session_runs.sort(key=lambda x: x[0])
                sorted_run_names = [x[1] for x in session_runs]

                # Lấy row của run mới nhất trong session (chỉ chọn từ run name parse được row hợp lệ)
                active_row = default_row
                for r_name in reversed(sorted_run_names):
                    r_parts = r_name.split("-")
                    if len(r_parts) >= 3 and r_parts[0] == "row":
                        try:
                            active_row = int(r_parts[1])
                            break
                        except (ValueError, TypeError):
                            continue

                # Gom kết quả toàn bộ máy chạy trong phiên (Feed + Follow + Upload)
                # Chỉ lấy các run thuộc active_row để tránh merge lộn các row khác nhau
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

                expected_machines = get_expected_machines_for_row(active_row)
                expected_count = len(expected_machines)
                completed_expected = set(all_machines.keys()).intersection(expected_machines)

                # ĐIỀU KIỆN CHỐT BÁO CÁO:
                can_report = can_report_session(
                    is_today=is_today,
                    completed_expected_count=len(completed_expected),
                    expected_count=expected_count,
                    now_hm=now_hm,
                    window_end_hm=win["end"],
                    runner_busy=runner_busy,
                )

                if not can_report:
                    continue

                def num_key(s):
                    nums = re.findall(r"\d+", str(s))
                    return int(nums[0]) if nums else 0

                # Phân loại Feed
                succ = sorted([m for m, d in all_machines.items() if d["status"] == "success"], key=num_key)
                fail = sorted([f"M{m}" for m, d in all_machines.items() if d["status"] != "success"], key=num_key)
                total_machines = len(all_machines)

                succ_str = ", ".join(succ) if succ else "Không có"
                fail_str = ", ".join(fail) if fail else "Không có"

                # Phân loại Follow
                total_followed_count = 0
                fl_success = []
                fl_released = []
                fl_error = []
                fl_skipped = []

                for m in sorted(all_machines.keys(), key=num_key):
                    if m in all_follows:
                        fd = all_follows[m]
                        flist = fd.get("followed", [])
                        total_followed_count += len(flist)
                        status = str(fd.get("status") or "").upper()

                        # Only explicit post-verify FOLLOW_FAILED with follow_failed=True means TikTok
                        # released the follow. Script/manual/timeout/unverified errors stay errors.
                        if status == "FOLLOW_FAILED" and fd.get("follow_failed") is True:
                            fl_released.append(m)
                        elif status == "SKIPPED":
                            fl_skipped.append(m)
                        elif status in {"OK", "SUCCESS"} and len(flist) > 0:
                            fl_success.append(m)
                        else:
                            fl_error.append(m)
                    else:
                        # Chỉ tính lỗi follow nếu máy lướt Feed thành công nhưng follow hook không chạy được
                        if all_machines[m].get("status") == "success":
                            fl_error.append(m)

                s_str = ", ".join(fl_success) if fl_success else "Không có"
                r_str = ", ".join(fl_released) if fl_released else "Không có"
                e_str = ", ".join(fl_error) if fl_error else "Không có"
                k_str = ", ".join(fl_skipped) if fl_skipped else "Không có"

                msg_lines = [
                    f"📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})",
                    f"• Tổng máy xử lý: {total_machines} máy",
                    f"• Lướt Feed:",
                    f"  + Success ({len(succ)}): {succ_str}",
                    f"  + Fail ({len(fail)}): {fail_str}",
                    f"• Follow chéo ({total_followed_count} lượt follow):",
                    f"  + Success ({len(fl_success)}): {s_str}",
                    f"  + Nhả follow ({len(fl_released)}): {r_str}",
                    f"  + Lỗi script/xác minh ({len(fl_error)}): {e_str}",
                    f"  + Bỏ qua ({len(fl_skipped)}): {k_str}"
                ]

                # Phân loại Upload (Phiên 3)
                if win["phien"] == 3 or any(all_uploads.values()):
                    up_success = []
                    up_timeout = []
                    up_error = []
                    up_skipped = []

                    for m in sorted(all_machines.keys(), key=num_key):
                        if m in all_uploads:
                            ud = all_uploads[m]
                            u_status = str(ud.get("status") or "").lower()
                            u_code = int(ud.get("exit_code", 0) or 0)
                            u_reason = str(ud.get("reason") or "").lower()

                            if u_status == "success" and u_code == 0:
                                up_success.append(m)
                            elif win["phien"] == 3 and u_reason.startswith("already_uploaded") and is_machine_upload_successful_in_shift(target_date, m, active_row):
                                up_success.append(m)
                            elif u_status == "skipped" or any(k in u_reason for k in ("video_not_rendered", "missing_video_folder", "missing_account_id", "not-final-session", "sensitive-skip", "cooling_period", "account_cooling_period", "age_gate", "under_10_days", "already_uploaded")):
                                up_skipped.append(m)
                            elif "timeout" in u_status or "timeout" in u_reason:
                                up_timeout.append(m)
                            else:
                                up_error.append(m)
                        else:
                            # Kiểm tra nếu máy đã upload thành công trong ledger (chỉ xét ở Phiên 3)
                            if win["phien"] == 3 and is_machine_upload_successful_in_shift(target_date, m, active_row):
                                up_success.append(m)
                            # Chỉ tính lỗi upload nếu máy lướt Feed thành công nhưng upload hook không chạy được ở Phiên 3
                            elif win["phien"] == 3 and all_machines[m].get("status") == "success":
                                up_error.append(m)

                    up_s_str = ", ".join(up_success) if up_success else "Không có"
                    up_t_str = ", ".join(up_timeout) if up_timeout else "Không có"
                    up_e_str = ", ".join(up_error) if up_error else "Không có"
                    up_k_str = ", ".join(up_skipped) if up_skipped else "Không có"

                    msg_lines.extend([
                        f"• Đăng Video (Phiên 3 - {len(up_success)} video đã đăng):",
                        f"  + Success ({len(up_success)}): {up_s_str}",
                        f"  + Timeout/Quá giờ ({len(up_timeout)}): {up_t_str}",
                        f"  + Lỗi script/xác minh ({len(up_error)}): {up_e_str}",
                        f"  + Bỏ qua ({len(up_skipped)}): {up_k_str}"
                    ])

                msg = "\n".join(msg_lines)
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
