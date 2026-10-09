# Profile Username Mismatch Recovery & Random Canary Swipes Pattern

## 1. Lỗi "profile username still mismatched after switch"

### Triệu chứng & Bối cảnh
- **Báo động Farm:** `[FARM ALERT: MÁY N]` với triệu chứng `profile username still mismatched after switch`.
- **Hiện trường:** Điện thoại đang mở tab Hồ sơ (Profile), nhưng username hiển thị trên header (ví dụ: `khoa4597`) không khớp với nick mục tiêu được phân bổ trong phiên nuôi (ví dụ: `lamnhu3003`).

### Nguyên nhân gốc rễ
1. **Thiếu thời gian settle sau khi tap switcher:** Khi người dùng có nhiều tài khoản trên app TikTok, việc chuyển đổi tài khoản qua Bottom Sheet Switcher yêu cầu tải lại session và cập nhật DOM/XML. Nếu thời gian chờ quá ngắn (chỉ 2.0–3.0s), quá trình transition chưa hoàn tất, hàm `_read_profile_identity_with_add_phone_guard` đọc trúng username cũ và ném lỗi mismatch.
2. **Cơ chế Auto-Login Reconcile bị bỏ sót:** Trong `feed_swipe_smoke.py`, hàm `_is_account_switcher_missing_expected_reason` ban đầu chỉ bắt chuỗi `"account-switcher-missing-expected"`. Khi gặp `last_reason = "profile username still mismatched after switch"`, flow không kích hoạt `_maybe_recover_missing_account_via_login` mà rơi thẳng vào trạng thái dừng `ExitStatus.MANUAL_NEEDED`.

### Giải pháp kỹ thuật chuẩn hóa (Repo `tiktok-luot nuoi acc`)
Trong `python_runner/flows/feed_swipe_smoke.py`:
1. **Mở rộng nhận diện Auto-Reconcile:**
   ```python
   def _is_account_switcher_missing_expected_reason(reason: str | None) -> bool:
       r = str(reason or "").lower()
       return "account-switcher-missing-expected" in r or "profile username still mismatched after switch" in r
   ```
2. **Tăng thời gian chờ settle sau khi tap switcher:**
   ```python
   # Tại verify_and_switch_profile:
   # Tăng từ random.uniform(2.0, 3.0) lên:
   time.sleep(random.uniform(3.5, 5.0))
   ```

---

## 2. Quy Chuẩn Random Canary Swipes (2–4 Swipes)

### Vấn đề Behavioral Footprint (Dấu vân tay hành vi)
- Nếu mọi lượt kiểm thử Canary sau phục hồi đều cố định đúng 2 swipes rồi thoát app về Home, chuỗi telemetry lặp đi lặp lại dễ bị hệ thống chống bot của TikTok ghi nhận pattern tự động hóa cơ học.
- Để hành vi tự nhiên hơn, Canary test cần ngẫu nhiên hóa số lần vuốt trong dải `2–4` swipes.

### Cấu hình Range trong Mã Nguồn
1. **PowerShell Launcher (`scripts/run-feed-session.ps1`):**
   - Mở rộng ValidateRange: `[ValidateRange(1, 4)][int]$RecoveryTestSwipes`.
2. **Python Flow Runner (`python_runner/flows/multi_machine_feed_session.py`):**
   - Mở rộng điều kiện chặn:
     ```python
     def _session_targets(config: dict[str, Any]) -> tuple[int, int, int]:
         recovery_test_swipes = config.get("_recovery_test_swipes")
         if recovery_test_swipes is None:
             return FEED_SESSION_MIN_TOTAL_VIDEOS, FEED_SESSION_MAX_TOTAL_VIDEOS, FEED_SESSION_MAX_SWIPES
         target = int(recovery_test_swipes)
         if not 1 <= target <= 4:
             raise RuntimeError("--recovery-test-swipes requires 1 <= value <= 4")
         return target, target, target
     ```

### Lệnh Chạy Canary Test B4 Chuẩn Hóa
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes (Get-Random -Minimum 2 -Maximum 5) -SkipAccountWorkbookSync -Run
```
*(Lưu ý: `Get-Random -Minimum 2 -Maximum 5` sinh ngẫu nhiên số nguyên từ 2 đến 4).*
