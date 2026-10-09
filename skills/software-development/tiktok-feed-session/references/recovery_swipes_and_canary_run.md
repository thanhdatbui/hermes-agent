# Recovery Test Swipes & Canary Run Protocol

## 1. Cơ chế Auto-Random 2-3 Swipes khi Recovery (Chống Bot-Pattern)
- Trong template alert lỗi của bot giám sát máy farm, cờ `-RecoveryTestSwipes 2` thường được tự động sinh ra cho các phiên kiểm tra phục hồi (Canary / Recovery).
- Nhằm tránh pattern cố định (fixed fingerprinting) khiến TikTok phát hiện tài khoản liên tục chỉ lướt đúng 2 video rồi thoát, `scripts/run-feed-session.ps1` đã được cấu hình tự động phân nhánh ngẫu nhiên:
  ```powershell
  if ($PSBoundParameters.ContainsKey("RecoveryTestSwipes")) {
      $effectiveSwipes = $RecoveryTestSwipes
      if ($RecoveryTestSwipes -eq 2) {
          $effectiveSwipes = Get-Random -Minimum 2 -Maximum 4
      }
      $arguments += "--recovery-test-swipes", "$effectiveSwipes"
  }
  ```
  *(Lưu ý: `Get-Random -Minimum 2 -Maximum 4` sinh ngẫu nhiên số nguyên thuộc tập {2, 3})*.
- Console log của launcher sẽ in giá trị thực tế sau khi random:
  `Targeted recovery swipes: <effectiveSwipes>`

---

## 2. Đồng Bộ Giới Hạn Validation 1 <= Swipes <= 4
Mọi thành phần trong chuỗi call stack phải thống nhất range swipe `[1, 4]`:
1. **PowerShell Launcher (`scripts/run-feed-session.ps1`)**:
   `[ValidateRange(1, 4)] [int]$RecoveryTestSwipes`
2. **CLI Entrypoint (`python_runner/run_tiktok.py`)**:
   `if args.recovery_test_swipes is not None and not 1 <= int(args.recovery_test_swipes) <= 4:`
   *(Trước đây là `<= 3`, cần giữ `<= 4` để không gây CONFIG_ERROR khi launcher truyền 4).*
3. **Flow Core (`python_runner/flows/multi_machine_feed_session.py`)**:
   Hàm `_session_targets()` kiểm tra `1 <= target <= 4`.
4. **Unit Tests (`python_runner/tests/test_multi_machine_feed_session.py`)**:
   `test_recovery_test_swipes_rejects_invalid_value` kiểm tra từ chối giá trị 5 (thay vì 4) với thông báo lỗi:
   `--recovery-test-swipes requires 1 <= value <= 4`.

---

## 3. Lệnh Canary Chuẩn Cho Máy Cần Phục Hồi
Khi test phục hồi đơn máy (ví dụ Máy 36) theo quy trình B4 Canary Live:
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 36 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
- `-SkipAccountWorkbookSync`: Bỏ qua bước sync workbook chậm để test ngay lập tức.
- `-Run`: Bắt buộc truyền để thực thi thật trên máy (không có `-Run` script chỉ in preview).

---

## 4. Chụp Ảnh Screencap & Nghiệm Thu
Sau khi Canary hoàn thành, bắt buộc lấy bằng chứng hiện trường:
```cmd
adb -s <serial> exec-out screencap -p > D:/Taadaa/runtime/kibe/live/canary_m<N>_done.png
```
- **Kiểm tra dung lượng**: File ảnh screencap đạt chuẩn phải > 100KB (thông thường ~150KB - 800KB). Nếu dưới 10KB hoặc 0 byte, có thể do ADB timeout hoặc lỗi pipe shell.
