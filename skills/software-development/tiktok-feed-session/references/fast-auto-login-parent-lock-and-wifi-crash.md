# Pitfall & Recovery: Fast Auto-Login Parent Lock Deadlock & Android System Server Wi-Fi Drop (2026-09-23)

## 1. Fast Auto-Login Parent Lock Deadlock (`--allow-parent-lock`)

### Hiện tượng
Khi chạy multi-machine-feed-session (`tiktok-luot nuoi acc`), nếu `feed_swipe_smoke.py` phát hiện thiếu tài khoản trong Account Switcher (`manual-needed:account-switcher-missing-expected`), luồng `auto_login_recovery` sẽ kích hoạt Fast Auto-Login:
```bash
python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <machine_id> --email <expected_id> --ss
```
Tuy nhiên, tiến trình cha `run_tiktok.py` (project: `tiktok-luot nuoi acc`) đang nắm active device lock `machine_<N>.lock.json`. Khi `tiktok_login_v1.py` khởi động:
- Gọi `acquire_device_lock(machine=..., serial=..., project="Tiktok_Reg", user_authorized=False)`.
- Phát hiện thiết bị đã bị khóa bởi project khác (`tiktok-luot nuoi acc`), `acquire_device_lock` ném ra ngoại lệ `DeviceLockNeedsUserDecision` hoặc `DeviceLockUnavailable`.
- Script login thoát ngay lập tức với mã lỗi `2` (`[device-lock] NEEDS_USER_DECISION: device lock active...`).
- `feed_swipe_smoke.py` nhận thấy Fast Login thất bại nên fallback sang `reconcile_tiktok_accounts.py` với timeout 300s, làm treo ca chạy và cuối cùng fail phiên.

### Nguyên nhân gốc rễ
Khác với `reconcile_tiktok_accounts.py` đã được trang bị cơ chế `--allow-parent-lock` để kế thừa lock của tiến trình mẹ, `tiktok_login_v1.py` thiếu argument `--allow-parent-lock` và logic kế thừa `InheritedDeviceLock`.

### Giải pháp kỹ thuật chuẩn hóa
1. **Repository `D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py`:**
   - Thêm argument vào CLI:
     ```python
     parser.add_argument(
         "--allow-parent-lock",
         action="store_true",
         help="Ke thua active device lock neu duoc goi tu parent automation (vi du: tiktok-luot nuoi acc)",
     )
     ```
   - Định nghĩa `PARENT_LOCK_PROJECTS = ("tiktok-luot nuoi acc", "tiktok-feed", "multi-machine-feed-session")`.
   - Bổ sung helper `_is_parent_lock_owner(exc)` và class `InheritedDeviceLock`.
   - Trong `main()`:
     ```python
     device_lock = None
     try:
         device_lock = acquire_device_lock(...)
     except (DeviceLockNeedsUserDecision, DeviceLockUnavailable) as e:
         is_parent, parent_proj, parent_pid = _is_parent_lock_owner(e)
         if getattr(args, "allow_parent_lock", False) and is_parent:
             log(f"[device-lock] Ke thua active device lock tu parent project '{parent_proj}' (pid {parent_pid})")
             device_lock = InheritedDeviceLock(machine=args.stt, serial=device_id)
         elif isinstance(e, DeviceLockNeedsUserDecision):
             log(f"[device-lock] NEEDS_USER_DECISION: {e.describe()}")
             return 2
         else:
             log(f"[device-lock] SKIP login STT {args.stt}: {e.describe()}")
             return 0
     ...
     finally:
         if device_lock is not None:
             device_lock.release()
     ```
2. **Repository `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`:**
   - Trong `_run_fast_targeted_login`:
     ```python
     fast_cmd = [
         str(python_exe),
         str(fast_login_script),
         str(machine_id),
         "--email", str(expected),
         "--ss",
         "--allow-parent-lock",
     ]
     ```

---

## 2. Chẩn đoán Lỗi Wi-Fi Not Connected: Proxy Sống vs Android System Server Crash

### Hiện tượng
Khi chạy preflight hoặc nuôi acc, script báo lỗi:
`required router proxy is unreachable for <serial> (kill switch active or no connection): dumpsys connectivity: Wi-Fi not connected`

### Quy trình phân biệt nguyên nhân O(1)
1. **Kiểm tra liveness của Proxy trước tiên:**
   - Dùng curl probe trực tiếp từ host:
     ```bash
     curl -x http://<ip_or_host>:<port> -U "<user>:<pass>" http://icanhazip.com -m 10
     ```
   - Nếu trả về IP sạch -> **100% Proxy không lỗi**. Không kết luận vội là do hạ tầng proxy.
2. **Kiểm tra trạng thái interface Wi-Fi trên thiết bị:**
   - `adb -s <serial> shell ip addr show wlan0`
   - Nếu `state DOWN` hoặc không có IP.
3. **Phát hiện Android `system_server` crash ngầm:**
   - Chạy:
     ```bash
     adb -s <serial> shell dumpsys wifi
     adb -s <serial> shell dumpsys window
     ```
   - Nếu ADB trả về: `Can't find service: wifi` hoặc `Can't find service: window`.
   - **Bản chất:** Kernel và ADB daemon (USB) vẫn hoạt động, nhưng tiến trình Android `system_server` đã bị chết/treo cứng, dẫn đến sập toàn bộ hệ thống quản lý Wi-Fi và UI.
4. **Hành động xử lý dứt điểm:**
   - Chạy `adb -s <serial> reboot`.
   - Sau khi máy boot lại (~30-45s), `system_server` phục hồi, Wi-Fi sẽ tự động kết nối lại (`wlan0 state UP`, ping gateway thông suốt).
