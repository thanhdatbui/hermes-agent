# Quy tắc Canary Recovery Test Swipes (Random 2-3)

## 1. Vấn đề thực tế
- Khi chạy B4 Canary Test phục hồi máy lỗi hoặc verify code fix:
  Nếu lần nào canary cũng cố định đúng 2 quẹt (`-RecoveryTestSwipes 2`) rồi đóng app thì thuật toán chống bot của TikTok dễ ghi nhận pattern máy móc (Behavioral footprint).
- Trước đây template câu lệnh B4 thường gán cứng `-RecoveryTestSwipes 2`, khiến các phiên chạy canary đều thực hiện đúng 2 swipe, dù user đã yêu cầu chạy ngẫu nhiên 2-3 swipe.

## 2. Câu lệnh Canary chuẩn kích hoạt Random 2-3 Swipes
- Trong PowerShell, dùng `(Get-Random -Minimum 2 -Maximum 4)` để sinh ngẫu nhiên số nguyên thuộc tập `{2, 3}`:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <ID> -Row 1 -RecoveryTestSwipes (Get-Random -Minimum 2 -Maximum 4) -SkipAccountWorkbookSync -Run
```

## 3. Cấu hình và ràng buộc trong Codebase (`tiktok-luot nuoi acc`)
- **`scripts\run-feed-session.ps1`**:
  - Tham số `$RecoveryTestSwipes` có ràng buộc `[ValidateRange(1, 4)]`.
  - Nếu truyền giá trị trong khoảng 2-3 (hoặc dùng `Get-Random`), launcher sẽ chuyển tiếp qua `--recovery-test-swipes <N>`.
- **`python_runner\run_tiktok.py`**:
  - Nhận argument `--recovery-test-swipes`. Cần đảm bảo validator kiểm tra `1 <= target <= 4`.
- **`python_runner\flows\multi_machine_feed_session.py`**:
  - Hàm `_session_targets(config)` nhận `_recovery_test_swipes` và áp dụng làm số video/swipe đích cho child session (`target, target, target`).
