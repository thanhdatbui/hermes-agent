# Quy Trình Chạy & Đo Đạc Canary Test TikTok Feed Session

## ⚠️ Quy Chuẩn Python Runtime (Bắt Buộc)
- **Đúng Python Runtime:** `D:\Taadaa\python-envs\automation\Scripts\python.exe` (Python 3.12.4, gắn `automation-core 0.4.45` ở chế độ editable).
- **CẤM:**
  - CẤM gọi `python` trần không truyền cờ `-Python` trong PowerShell / bash, vì sẽ bị dính `WindowsApps` stub hoặc Hermes Agent internal venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`) gây lỗi thiếu `automation_core`.
  - CẤM đoán mò đường dẫn `Python310` hay `.venv` trong repo vì không tồn tại trên máy này.
- **Thư mục repo có khoảng trắng:** Luôn bọc nháy kép `"D:\Taadaa\tiktok-luot nuoi acc\..."` hoặc dùng `-LiteralPath` khi gọi PowerShell cmdlets.

## Lệnh Canary Chuẩn
```powershell
# Bắt buộc truyền tham số -Python trỏ đúng runtime của farm
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" `
  -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" `
  -Machines <N> -Row <Row> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```

### 1. Quy Tắc Xác Định Đúng Row Theo Ca Chạy Thực Tế (Parity Lanes)
- **CẤM mặc định chạy `-Row 1`**: Khi nhận alert hoặc tái hiện lỗi ở một ca cụ thể, BẮT BUỘC tra cứu ca chạy thực tế tại thời điểm alert:
  - **Ngày Lẻ**: Ca 1 (06:00 - Row 1) | Ca 2 (12:30 - Row 3) | Ca 3 (19:00 - Row 5).
  - **Ngày Chẵn**: Ca 1 (06:00 - Row 2) | Ca 2 (12:30 - Row 4) | Ca 3 (19:00 - Row 6).
- Mở `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` (hoặc `tik<N>.xlsx`) để tra cứu đúng nickname của Máy `<N>` ở Row tương ứng trước khi chạy và đối chiếu sau khi chạy.

### 2. Pre-Flight An Toàn: Kiểm Tra Máy Bận / Device Lock
- Trước khi chạy Canary trên máy `<N>`, BẮT BUỘC kiểm tra xem máy có đang chạy trong batch live hay không:
  ```bash
  ls -la ~/.codex/device-locks/machine_<N>.lock.json
  ```
- Nếu tồn tại lock và PID còn sống (`Get-Process -Id <PID>`): **TUYỆT ĐỐI CẤM kill tiến trình hoặc xóa lock**. Phải đợi ca chạy live của máy đó hoàn tất (nhả lock thành công) mới tiến hành chạy Canary test.

### 3. Cơ Chế `-RecoveryTestSwipes 2`
- Trong `run-feed-session.ps1`, tham số `-RecoveryTestSwipes 2` sẽ tự động chọn ngẫu nhiên từ 2 đến 3 lượt swipe (`Get-Random -Minimum 2 -Maximum 4`).
- Điều này đảm bảo kiểm chứng đầy đủ toàn bộ chu trình (App launch -> Profile Switcher -> Feed Swipes -> Profile Verify) với thời gian thực thi tối ưu nhất (~3-4 phút).

## Đặc Tính Thời Gian & Timeout
- **Chu trình thực tế gồm các giai đoạn:**
  1. `prepare_tiktok`: wake device, xoay màn hình portrait, close apps, force stop & launch TikTok, verify focus (~35s - 45s).
  2. `baseline` screen inspection & dismiss popup khởi động / Shop CTA (~30s - 45s).
  3. `profile_preflight` & account switcher navigation (`_navigate_profile_for_preflight`): tap profile tab, nhận diện profile sheet, tap switch anchor, mở switcher sheet, chọn tài khoản đúng, dismiss popup gợi ý bạn bè, verify lại account name, tap home quay về Feed (~60s - 90s).
  4. Feed Swipes (với `-RecoveryTestSwipes 2`):
     - Swipe 1 + blind popup checks (~30s - 40s).
     - Swipe 2 + blind popup checks (~30s - 40s).
- **Tổng thời gian chạy:** Thường rơi vào **3.5 đến 5 phút** cho 1 máy đơn lẻ.
- **Kỷ luật Timeout:** Công cụ `terminal` hoặc lệnh wrapper bên ngoài PHẢI cấu hình timeout **>= 360 - 600s** (không dùng timeout mặc định 180s hay 300s vì sẽ kill non tiến trình ngay khi đang xử lý swipe 2).

## Vị Trí Log & Trích Xuất Hiện Trường
- CẤM quét toàn bộ ổ đĩa (`grep -rn`, `find`, `os.walk`).
- File log chi tiết từng step của máy `<N>` được ghi trực tiếp tại:
  `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\machines\machine_<N>\<TIMESTAMP>\log.jsonl`
- Kiểm tra các step trọng yếu trong `log.jsonl`:
  - `profile_preflight` / `tap_profile` / `tap_expected_account`: Trạng thái switch account thành công (`"reason": "profile switched to expected account"`).
  - `feed-session-smoke/tap_home`: Trạng thái quay lại màn hình Home For You.
  - `swipe_1_after`, `swipe_2_after`: Xác nhận Feed (`"reason": "feed confirmed"`).
