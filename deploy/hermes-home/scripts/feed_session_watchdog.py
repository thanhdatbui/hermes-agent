"""Watchdog báo cáo kết quả nuôi TikTok theo từng CA / PHIÊN chuẩn xác theo tiến trình máy thật.

Một ngày có 3 Ca, mỗi Ca có 3 Phiên:
- Ca 1 (Sáng):
  + Phiên 1: Khung ~06:00 - 07:30
  + Phiên 2: Khung ~07:35 - 09:30
  + Phiên 3: Khung ~09:35 - 11:30
- Ca 2 (Chiều):
  + Phiên 1: Khung ~12:00 - 13:45
  + Phiên 2: Khung ~13:45 - 15:30
  + Phiên 3: Khung ~15:30 - 18:15
- Ca 3 (Tối):
  + Phiên 1: Khung ~18:30 - 20:15
  + Phiên 2: Khung ~20:15 - 22:00
  + Phiên 3: Khung ~22:00 - 23:55

Cơ chế thông minh:
- Đọc danh sách target machines theo Row từ config (hoặc số máy dự kiến).
- Theo dõi tiến trình máy thật: Khi TẤT CẢ các máy trong ca/phiên đã hoàn tất (hoặc phiên hết giờ và runner đã dừng hẳn):
  -> Gửi đúng 1 BÁO CÁO TỔNG KẾT PHIÊN đầy đủ: gộp cả phần LƯỚT FEED và phần FOLLOW HOOK.
"""
import os
import glob
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
LIVE_ROOT = r"D:\Taadaa\runtime\kibe\live"
STATE_FILE = r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json"
SOURCE_CONFIG = r"D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json"


def _load_reported_sessions(path: str) -> set[str]:
    """Tải tập hợp các session đã report từ state file, chịu lỗi mọi schema biến dạng."""
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            sessions = data.get("reported_sessions")
            if isinstance(sessions, list):
                return set(str(s) for s in sessions if s)
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

# Định nghĩa các khung phiên chuẩn
SESSION_WINDOWS = [
    # Ca 1
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/3 (Sáng)", "start": "06:00", "end": "07:30"},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/3 (Sáng)", "start": "07:30", "end": "09:30"},
    {"ca": 1, "phien": 3, "name": "Ca 1 - Phiên 3/3 (Sáng - Đăng video)", "start": "09:30", "end": "12:00"},
    # Ca 2
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/3 (Chiều)", "start": "12:00", "end": "13:45"},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/3 (Chiều)", "start": "13:45", "end": "15:30"},
    {"ca": 2, "phien": 3, "name": "Ca 2 - Phiên 3/3 (Chiều - Đăng video)", "start": "15:30", "end": "18:30"},
    # Ca 3
    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/3 (Tối)", "start": "18:30", "end": "20:15"},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/3 (Tối)", "start": "20:15", "end": "22:00"},
    {"ca": 3, "phien": 3, "name": "Ca 3 - Phiên 3/3 (Tối - Đăng video)", "start": "22:00", "end": "23:59"},
]


def is_feed_runner_active():
    """Kiểm tra có process feed runner hay powershell feed nào đang chạy không."""
    try:
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                cmd = " ".join(p.info.get('cmdline') or [])
                if "multi_machine_feed_session" in cmd or "run-feed-session.ps1" in cmd or "run_follow" in cmd:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def get_expected_machines_for_row(row_num):
    """Lấy danh sách set các máy dự kiến theo row từ hermes_cron_source_config.json."""
    if not os.path.exists(SOURCE_CONFIG):
        return set(str(i) for i in range(1, 75 if row_num == 1 else 73))
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
        return set(str(i) for i in range(1, 75 if row_num == 1 else 73))
    except Exception:
        return set(str(i) for i in range(1, 75 if row_num == 1 else 73))


def parse_run_machines(run_dir):
    """Lấy map machine -> final_status từ 1 run dir."""
    summaries = glob.glob(os.path.join(run_dir, "**", "summary.txt"), recursive=True)
    res = {}
    for s in summaries:
        parts = os.path.normpath(s).split(os.sep)
        if "machines" in parts:
            m_idx = parts.index("machines") + 1
            if m_idx < len(parts):
                m_str = parts[m_idx].replace("machine_", "")
                c = open(s, encoding="utf-8", errors="ignore").read()
                st = "success" if "final_status: success" in c else "fail"
                reason = ""
                for line in c.splitlines():
                    if line.startswith("reason:") or line.startswith("final_status:"):
                        val = line.split(":", 1)[1].strip()
                        if val != "success":
                            reason = val
                            break
                res[m_str] = {"status": st, "reason": reason}
    return res


def parse_follow_results(run_dir):
    """Lấy kết quả follow hook từ 1 run dir."""
    follows = glob.glob(os.path.join(run_dir, "**", "follow_result.json"), recursive=True)
    res = {}
    for f in follows:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
                if not isinstance(d, dict):
                    continue
                m = str(d.get("machine", "")).strip()
                if not m:
                    continue
                flist = d.get("followed")
                if not isinstance(flist, list):
                    flist = []
                res[m] = {
                    "status": str(d.get("status") or "").strip(),
                    "followed": flist,
                    "follow_failed": bool(d.get("follow_failed", False)),
                    "reason": str(d.get("reason") or ""),
                }
        except Exception:
            pass
    return res


def parse_upload_results(run_dir):
    """Lấy kết quả upload hook từ 1 run dir."""
    uploads = glob.glob(os.path.join(run_dir, "**", "upload_result.json"), recursive=True)
    res = {}
    for u in uploads:
        try:
            with open(u, "r", encoding="utf-8") as fp:
                d = json.load(fp)
                m = str(d.get("machine", ""))
                if not m:
                    continue
                raw_code = d.get("exit_code", d.get("returncode", 0))
                try:
                    exit_code = int(raw_code)
                except (ValueError, TypeError):
                    exit_code = 1 if str(d.get("status", "")).lower() != "success" else 0
                res[m] = {
                    "status": str(d.get("status") or "").lower(),
                    "exit_code": exit_code,
                    "reason": str(d.get("reason") or ""),
                }
        except Exception:
            pass
    return res


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
                # Dùng half-open interval để tránh đè boundary trừ window cuối ngày
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
                    m_res = parse_run_machines(r_path)
                    f_res = parse_follow_results(r_path)
                    u_res = parse_upload_results(r_path)
                    for m, data in m_res.items():
                        all_machines[m] = data
                    for m, data in f_res.items():
                        all_follows[m] = data
                    for m, data in u_res.items():
                        all_uploads[m] = data

                if not all_machines:
                    continue

                expected_machines = get_expected_machines_for_row(active_row)
                expected_count = len(expected_machines)
                completed_expected = set(all_machines.keys()).intersection(expected_machines)

                # ĐIỀU KIỆN CHỐT BÁO CÁO:
                # Với ngày hôm nay:
                # 1. Toàn bộ máy dự kiến trong ca đã hoàn thành VÀ runner đã dừng hẳn
                # HOẶC
                # 2. Đã hết khung giờ phiên (chỉ áp dụng cho các phiên trong ngày trước 23:59) VÀ runner hiện tại đã chạy xong
                # Với ngày hôm qua (rollover): runner đã dừng hẳn là chốt báo cáo
                if is_today:
                    if is_last_window:
                        can_report = (len(completed_expected) >= expected_count and not runner_busy)
                    else:
                        can_report = (len(completed_expected) >= expected_count and not runner_busy) or (now_hm >= win["end"] and not runner_busy)
                else:
                    can_report = not runner_busy

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

                        # Only explicit post-verify FOLLOW_FAILED or follow_failed flag means TikTok
                        # released the follow. Script/manual/timeout errors stay errors.
                        if status == "FOLLOW_FAILED" or fd.get("follow_failed") is True:
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
                            elif u_status == "skipped" or any(k in u_reason for k in ("video_not_rendered", "missing_video_folder", "missing_account_id", "not-final-session", "sensitive-skip")):
                                up_skipped.append(m)
                            elif "timeout" in u_status or "timeout" in u_reason:
                                up_timeout.append(m)
                            else:
                                up_error.append(m)
                        else:
                            # Chỉ tính lỗi upload nếu máy lướt Feed thành công nhưng upload hook không chạy được ở Phiên 3
                            if win["phien"] == 3 and all_machines[m].get("status") == "success":
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
