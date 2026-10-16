# Immediate Avatar Upload End-to-End & Switcher Header Anchor Collision (2026-10-17)

## 1. Kỷ Luật Vận Hành End-to-End: Upload Ngay Lập Tức, CẤM Treo Watchdog
- **Phản hồi của User**: *"Sao k up luôn mà phải chờ v"* (Khi chuẩn hoá acc, user duyệt ảnh xong mà agent chỉ set PENDING rồi dừng chờ cron là vi phạm nghiêm trọng).
- **Quy tắc**: Ngay sau khi User chốt Phương án Avatar:
  1. Đồng bộ file `avatar.jpg` vào các kho (`video goc/<src>`, `video goc/<out>`, `TIKTOK-videonuoinick/<out>`).
  2. Cắm marker `.manual_avatar_locked` và ghi registry `manual_avatar_protected_folders.json`.
  3. Cập nhật `Tik<N>.xlsx` và `avatar_replace_queue` trong `tiktok_tracker.db`.
  4. **KÍCH HOẠT NGAY LẬP TỨC runner upload avatar**:
     ```powershell
     powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik <tik> -ForceAvatarMachineList "<may>" -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml
     ```
  5. Đợi runner hoàn thành -> Mở ảnh kiểm tra bằng chứng thực tế (`avatar-uploaded-confirmed.png` hoặc screencap profile) -> Soi mắt qua `browser_vision` (Gate 6) -> Báo cáo kèm `MEDIA:`.
  6. **TUYỆT ĐỐI CẤM**: Dừng lại ở bước enqueue `PENDING` và bảo user chờ watchdog / cron 5 phút!

## 2. Lỗi Account Switcher Anchor: Bẫy Trùng Tên Header (`len(candidates) == 1`)
- **Triệu chứng**: Runner chạy mở profile thành công nhưng không mở được Account Switcher, log ghi:
  `[PREPARE_SWITCHER] Header candidates=2 centers=[(277, 298), (504, 483)] limit=672`
  Sau đó báo lỗi `[ACCOUNT_SWITCHER_FAILED] open_switcher failed: SWITCHER_NOT_CONFIRMED: switcher markers were not confirmed`.
- **Nguyên nhân**: Trên layout TikTok mới của một số tài khoản, tên hiển thị (display name, ví dụ "Ngô Thị Vy") xuất hiện ở cả 2 vị trí:
  - Thanh top bar trên cùng ($cy \approx 298$)
  - Dưới avatar ($cy \approx 483$)
  Đoạn code trong `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/adapter.py` hàm `prepare_switcher_anchor()` kiểm tra cứng nhắc `if len(candidates) == 1:`, nên khi có 2 candidates trùng tên nằm trong vùng `top < header_limit`, nó không tap vào đâu cả dẫn đến timeout!
- **Giải pháp**: Sắp xếp candidates theo tọa độ $y$ tăng dần và tap vào candidate trên cùng ($cy$ nhỏ nhất, chính là top bar):
  ```python
  if candidates:
      candidates.sort(key=lambda c: c[2])
      t, cx, cy = candidates[0]
      self.tap(cx, cy)
      logger.info(f"[PREPARE_SWITCHER] Tapped profile name at ({cx}, {cy})")
      time.sleep(0.75)
      return True
  ```

## 3. Lỗi UnicodeDecodeError Khi Subprocess Gọi PowerShell Trên Windows
- **Triệu chứng**:
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xad in position 83: invalid start byte`
  gây crash `_readerthread` của Python subprocess khi đọc stdout của `powershell.exe`.
- **Nguyên nhân**: PowerShell trên Windows console xuất dữ liệu theo codepage hệ thống (CP1252 / CP1258 / ANSI) chứa các byte ngoài bảng mã UTF-8. Nếu dùng `text=True` mặc định mà không chỉ định error handling, luồng đọc sẽ crash ngay lập tức.
- **Giải pháp**: Luôn truyền `errors="replace"` (hoặc dùng `encoding="utf-8", errors="replace"`):
  ```python
  proc = subprocess.Popen(
      cmd,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      errors="replace",
  )
  stdout, _ = proc.communicate(input="RUN\n")
  ```
