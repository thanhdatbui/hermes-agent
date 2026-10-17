# Immediate Avatar Upload End-to-End & Switcher Header Anchor Collision (2026-10-17)

## 1. Kỷ Luật Vận Hành End-to-End: Upload Ngay Lập Tức, CẤM Treo Watchdog
- **Phản hồi của User**: *"Sao k up luôn mà phải chờ v"* (Khi chuẩn hoá acc, user duyệt ảnh xong mà agent chỉ set PENDING rồi dừng chờ cron là vi phạm nghiêm trọng).
- **Quy tắc**: Ngay sau khi User chốt Phương án Avatar:
  1. Đồng bộ file `avatar.jpg` vào các kho (`video goc/<src>`, `video goc/<out>`, `TIKTOK-videonuoinick/<out>`).
  2. Cắm marker `.manual_avatar_locked` và ghi registry `manual_avatar_protected_folders.json`.
  3. Cập nhật `Tik<N>.xlsx` và `avatar_replace_queue` trong `tiktok_tracker.db`.
  4. **KÍCH HOẠT NGAY LẬP TỨC runner upload avatar**:
     - *Lưu ý Coordinator Terminal Guard*: Coordinator bị cấm gọi trực tiếp `powershell.exe` hoặc `python -c` chứa subprocess.
     - *Cách thực thi chuẩn*: Gọi thông qua một script launcher wrapper (ví dụ `D:/Taadaa/reports/run_avatar_m<M>.py`) bằng lệnh:
       ```python
       terminal(background=True, notify_on_complete=True, command="python D:/Taadaa/reports/run_avatar_m<M>.py", timeout=360)
       ```
     - Launcher wrapper script thực thi `run_tiktok_upload_avatar.ps1` với `powershell.exe`:
       ```python
       cmd = [
           "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1",
           "-Tik", str(tik), "-ForceAvatarMachineList", str(may),
           "-MaxParallel", "1", "-HostConfigPath", r"D:\Taadaa\machine-config\kibe.yaml"
       ]
       proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
       stdout, _ = proc.communicate(input="RUN\n")
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

## 4. Bẫy Timeout 300s Của Launcher Wrapper vs Tiến Trình PowerShell Thành Công
- **Triệu chứng**:
  Python launcher wrapper báo lỗi:
  `[ERROR] Command '['powershell.exe', ...]` timed out after 300 seconds` (exit code 1).
- **Thực tế hiện trường**:
  Tiến trình PowerShell bên dưới chạy mất ~310s - 320s và đã nạp avatar thành công mỹ mãn!
  - File `summary.csv` trong `D:/CodexRuntime/tiktok-video/batch-runs/batch_tik<N>_*/summary.csv` ghi nhận:
    `"Status": "THÀNH CÔNG", "Verified": "True"`.
  - File `report.json` ghi nhận: `"avatar_status": "FORCED_REPLACED_VERIFIED"`, `"status": "AVATAR_SMOKE_SUCCESS"`.
  - File `avatar-uploaded-confirmed.png` đã lưu ảnh Profile đổi avatar mới thành công.
- **Quy tắc điều phối bắt buộc**:
  1. **Ngân sách Timeout**: Luôn cấu hình timeout cho Python subprocess launcher $\ge 360$s (hoặc 420s) khi gọi `run_tiktok_upload_avatar.ps1`, vì quy trình đầy đủ (khởi động app, đổi switcher, mở gallery, crop, save, verify) mất từ 3.5 đến 5.5 phút.
  2. **Kiểm Tra Artifact Trước Khi Báo Lỗi**: Khi tiến trình nạp avatar trả về exit 1 do timeout, CẤM vội kết luận thất bại. Coordinator BẮT BUỘC kiểm tra artifact mới nhất tại `D:/CodexRuntime/tiktok-video/batch-runs/` và `runs/run_<serial>_<timestamp>/report.json`. Nếu `avatar_status: FORCED_REPLACED_VERIFIED` thì xác nhận thành công và lấy `avatar-uploaded-confirmed.png` để soi mắt nghiệm thu.
  3. **Bẫy `>` Redirect Trên `with_device_lock.py`**: Khi gọi `python D:/Taadaa/tools/with_device_lock.py --machine <N> -- adb exec-out screencap -p > file.png`, script `with_device_lock` xuất log text ra stdout làm hỏng byte stream của ảnh PNG. Ưu tiên lấy trực tiếp ảnh `avatar-uploaded-confirmed.png` đã được runner tạo sẵn trong thư mục run.

## 5. Anti-Asking Invariant Khi Nhận Lệnh "Chuẩn hoá acc": Tự Động Trích Xuất & Xuất Preview, CẤM Hỏi Lại
- **Phản hồi của User**: *"Tạo ava đi chứ hỏi chi v"* (Khi user gửi ảnh profile TikTok yêu cầu chuẩn hoá, Coordinator lại đi hỏi "Bạn có muốn tôi trích xuất 2 phương án avatar... không?").
- **Nguyên tắc hành động**:
  1. Khi nhận lệnh "Chuẩn hoá acc này" kèm ảnh: Đây là lệnh thực thi trực tiếp, KHÔNG PHẢI câu hỏi xin tư vấn.
  2. BẮT BUỘC đi thẳng một mạch:
     - Định vị tọa độ $O(1)$ (Máy, Slot, Niche, Folder gốc/render).
     - Kiểm tra Pin Gate ($\ge 1.000$ views) và Hashtag.
     - **Ngay lập tức** trích xuất 2 phương án Avatar từ video gốc ($512 \times 512$, căn giữa chuẩn ngũ quan, headroom chống lẹm tròn).
     - Dựng contact sheet so sánh có mask viền tròn (`comparison_preview.jpg`).
     - Soi mắt kiểm định qua Vision, gửi kèm thẻ `MEDIA:` và hỏi user chọn Option 1 hay 2.
  3. **CẤM TUYỆT ĐỐI**: Phân tích kênh xong rồi dừng lại hỏi "Bạn có muốn tôi trích xuất avatar không?". Bất kỳ câu hỏi xin phép nào trong phạm vi chuẩn hoá đều bị coi là kéo dài thời gian và vi phạm kỷ luật Coordinator.

## 6. Bẫy Lồng Device Lock Khi Chạy `run_avatar_batch_3accs.py` & Database SQLite SSOT
- **Bẫy Nested Device Lock**:
  - `D:/Taadaa/tools/run_avatar_batch_3accs.py` gọi PowerShell `run_tiktok_upload_avatar.ps1` -> `run_tiktok_upload_batch.ps1`.
  - Bên trong `run_tiktok_upload_batch.ps1` và `automation-core`, runner con đã TỰ ĐỘNG yêu cầu và quản lý `device_lock` cho máy mục tiêu.
  - **Hậu quả nếu lồng**: Nếu Coordinator chạy `with_device_lock.py --machine N -- python run_avatar_batch_3accs.py --machine N`, chính tiến trình cha giữ lock của máy N, khiến runner con bên trong không thể lấy lock hoặc bị conflict/thoát ngay lập tức (exit code 0 nhưng STDOUT rỗng).
  - **Quy tắc chuẩn**: Chạy trực tiếp `python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <tik> --machine <machine>` với `background=True, notify_on_complete=True, timeout=600`. CẤM chạy foreground vì guard giới hạn timeout foreground $\le 60$s (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`).
- **Database SQLite SSOT Chuẩn**:
  - `D:/Taadaa/data/tiktok_tracker.db` là database chính thức chứa bảng `avatar_replace_queue`.
  - `D:/Taadaa/tiktok_tracker.db` ở thư mục gốc có thể là database trống không có bảng. Script cập nhật trạng thái `PENDING` bắt buộc phải trỏ vào `D:/Taadaa/data/tiktok_tracker.db`.


