# GPM Backup File Lock Prevention & Pre-Closure Protocol

## 1. Bản chất lỗi `[Errno 13] Permission Denied` khi Backup GPM
Khi tiến hành sao lưu định kỳ thư mục profiles GPMLogin (`...\AppData\Local\Programs\GPMLogin\profile`):
- Nếu profile đang được mở (ngâm tài khoản, nuôi YouTube/Search, hoặc chạy batch), Chromium/Chrome giữ exclusive file lock đối với:
  + `Default/Network/Cookies` & `Cookies-journal`
  + `Default/Web Data` & `Web Data-journal`
  + `Default/Login Data`
- Khi script backup nén file vào `.zip`, Windows kernel sẽ chặn với lỗi `[Errno 13] Permission denied`.
- Dù database SQLite `profile_data.db` được backup an toàn bằng API `sqlite3.backup`, file session nén vẫn sẽ bị thiếu cookies nếu không giải phóng file lock.

## 2. Cơ chế đóng 2 lớp an toàn chuẩn hóa (`close_all_running_gpm_profiles`)
Trước khi bắt đầu đọc file hoặc nén zip, bắt buộc gọi hàm tiền xử lý giải phóng lock:

```python
def close_all_running_gpm_profiles(gpm_api: str = "http://127.0.0.1:19995", delay: float = 2.0) -> int:
    """
    Đóng toàn bộ GPM profiles đang mở trước khi backup:
    1. Graceful Stop qua GPM API để flush cookies/session êm ái.
    2. Fallback quét psutil lọc chrome.exe/gpm.exe thuộc GPM profile dir.
    3. Bảo vệ tuyệt đối: CẤM đụng Chrome User ("google\\chrome\\user data"), Python, Hermes, ADB.
    4. Settle delay để OS nhả lock.
    """
    closed = 0
    # 1. Graceful API Stop
    try:
        import requests
        r = requests.get(f"{gpm_api}/api/v3/profiles", timeout=3)
        if r.status_code == 200:
            profiles = r.json().get("data") or []
            for p in profiles:
                pid = p.get("id") or p.get("profile_id")
                if pid and p.get("status") in ("running", "open", 1, True):
                    try:
                        stop_res = requests.get(f"{gpm_api}/api/v3/profiles/stop/{pid}", timeout=3)
                        if stop_res.status_code == 200:
                            closed += 1
                            logger.info(f"Đã dừng profile {pid} qua GPM API")
                    except Exception as err:
                        logger.warning(f"Lỗi dừng profile {pid} qua API: {err}")
    except Exception as api_err:
        logger.info(f"GPM Local API không phản hồi ({api_err}), quét tiến trình qua psutil")

    # 2. Targeted Process Cleanup (Bảo vệ nghiêm ngặt chống kill nhầm)
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            name = (proc.info.get('name') or "").lower()
            # BẮT BUỘC chỉ nhắm vào browser processes
            if name not in ('chrome.exe', 'gpm.exe', 'gpmlogin.exe'):
                continue
            cmd = " ".join(proc.info.get('cmdline') or []).lower()
            # Rào chắn an toàn: Chrome cá nhân của User & tiến trình farm
            if "google\\chrome\\user data" in cmd or "google/chrome/user data" in cmd:
                continue
            if any(k in name for k in ("python", "hermes", "adb", "node", "xiaowei")):
                continue
            # Chỉ match tiến trình Chrome gắn profile dưới thư mục GPMLogin
            if any(m in cmd for m in ("gpmlogin\\profile", "gpmlogin/profile", "programs\\gpmlogin\\profile")):
                try:
                    proc.terminate()
                    closed += 1
                    logger.info(f"Đã dừng tiến trình GPM {name} PID {proc.pid}")
                except Exception as p_err:
                    logger.warning(f"Không thể terminate tiến trình PID {proc.pid}: {p_err}")
    except Exception as proc_err:
        logger.warning(f"Lỗi quét tiến trình psutil: {proc_err}")

    if closed > 0:
        logger.info(f"Đã đóng {closed} profile/tiến trình GPM. Chờ {delay}s để giải phóng lock...")
        time.sleep(delay)
    return closed
```

## 3. Quy tắc tích hợp & Vận hành (Production Hardened)
1. **Gọi đầu routine:** Đặt `close_all_running_gpm_profiles()` ngay đầu `main()` trước bước `sqlite3.backup` và nén file ZIP.
2. **Kiểm tra process name nghiêm ngặt:** Bắt buộc lọc `name in ('chrome.exe', 'gpm.exe', 'gpmlogin.exe')`, cấm match lỏng lẻo chỉ dựa trên cmdline để chống terminate nhầm tiến trình khác.
3. **Lọc loại trừ chính xác:** Cấm dùng chuỗi rộng `user data` (có thể nuốt nhầm GPM `--user-data-dir`), bắt buộc kiểm tra đích danh `google\chrome\user data` của trình duyệt cá nhân.
4. **Settle delay >= 2.0s:** Cần thiết trên Windows để file handle được giải phóng hoàn toàn trong filesystem cache sau khi tiến trình kết thúc.
5. **Telemetry & Log rõ ràng:** Ghi nhận số profile đã đóng trước khi backup vào structured telemetry (`closed_profiles_before_backup`), log warning/info có ý nghĩa thay vì nuốt `pass` âm thầm.
