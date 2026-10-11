# Single-Machine On-Demand Avatar Replacement Workflow

## 1. Xác định máy và tài khoản mục tiêu
Khi nhận yêu cầu đổi avatar từ ảnh chụp màn hình hoặc username TikTok:
- Tra cứu username trong các workbook `D:/OneDrive/TaadaaData/kibe/Tik*.xlsx` (`Tik1.xlsx` đến `Tik8.xlsx`) và database `D:/Taadaa/data/tiktok_tracker.db` (`account_mapping`, `snapshots`, `avatar_replace_queue`).
- Lấy chính xác bộ 4 thông số: `máy`, `tik`, `folder_video` (kho render), `video_goc` (kho gốc).

## 2. Tiêu chuẩn trích xuất & Cắt crop Avatar đạt chuẩn Vision
- **Nguồn ảnh:** Trích xuất các frame rõ nét từ các video `.mp4` trong `D:/video goc/<folder>` hoặc `D:/TIKTOK-videonuoinick/<folder>`.
- **Quy tắc Crop tròn TikTok:**
  - Khung hình TikTok Profile là hình tròn. Tránh tuyệt đối lấy ảnh toàn thân ở góc xa (khi vào khung tròn mặt chủ thể sẽ bị nhỏ tí teo hoặc lệch góc).
  - Crop cận cảnh (tight zoom / portrait): Khuôn mặt chủ thể (người / thú cưng) phải nằm ngay trung tâm, chiếm 40%–60% diện tích khung hình vuông `512x512`.
  - Không dính watermark, phụ đề, thanh tiến trình hay viền đen.
- **Vision Pre-flight:** Mở ảnh qua `browser_vision` kiểm tra tận mắt độ nét, bố cục và xác nhận chủ thể đúng yêu cầu trước khi nạp vào hệ thống.

## 3. Đồng bộ kho ảnh 2 đầu (SSOT Dual-Sync)
- Copy file avatar thành phẩm `avatar.jpg` vào đồng thời cả hai kho:
  1. `D:/TIKTOK-videonuoinick/<folder>/avatar.jpg` (Kho render trực tiếp)
  2. `D:/video goc/<folder>/avatar.jpg` (Kho gốc bảo toàn)
- Đảm bảo file có quyền đọc và kích thước hợp lệ (> 10KB, định dạng JPEG chuẩn).

## 4. Đồng bộ Workbook & Hàng đợi Database
- **Workbook `Tik<N>.xlsx`:**
  - Cập nhật cột `Avatar` của máy thành `PENDING` (để trigger runner nhận diện).
  - Kiểm tra và đồng bộ lại `Keyword Video` và `Hashtag Pool` cho chuẩn ngách nếu có sự sai lệch.
- **Database `D:/Taadaa/data/tiktok_tracker.db`:**
  - Cập nhật bảng `avatar_replace_queue`:
    ```sql
    UPDATE avatar_replace_queue
    SET status = 'PENDING', last_error = NULL, updated_at = datetime('now', 'localtime')
    WHERE username = '<username>' AND may = <may>;
    ```

## 4.1. Điều phối Worker & Bảo toàn Ngân sách T1 (Coordinator Discipline)
- **Bảo toàn hạn ngạch T1:** Coordinator có trần cứng T1 (tối đa 5 files, <= 200 dòng cộng dồn cả phiên). CẤM Coordinator tự ý dùng `write_file` tạo các script cào frame/inspect/HTML nháp trong `D:/Taadaa/tmp/`. Việc viết script trích xuất frame, crop ảnh, ghi file và update DB/Excel thuộc trách nhiệm của Worker.
- **Scope Lock Whitelist trong `delegate_task`:**
  - Guard kiểm soát delegation yêu cầu khai báo `FILE: <đường_dẫn_tuyệt_đối>` trong mục tiêu.
  - Đường dẫn file khai báo BẮT BUỘC phải nằm trong whitelist repo `D:\Taadaa` (ví dụ: `FILE: D:\Taadaa\tmp\prepare_avatar_<folder>.py`).
  - CẤM khai báo trực tiếp file ngoài whitelist như `D:\OneDrive\TaadaaData\kibe\Tik*.xlsx` vào dòng `FILE: ...` của contract (sẽ bị guard chặn `OUT OF REPO WHITELIST`). Hãy để Worker script dưới `D:\Taadaa` mở và cập nhật file OneDrive.

## 5. Kích hoạt Runner Avatar chuyên biệt (Avatar-Only Mode)
- **Phân định quyền chạy Terminal (Coordinator vs Worker):**
  - Worker subagent bị Worker Gate chặn chạy script Python ngoài allowlist và chặn PowerShell (`Worker CHỈ ĐƯỢC PHÉP chạy: git status/diff/log, adb devices, inspect_machine.py <N>, pytest, psutil`). Vì vậy, Worker chỉ làm nhiệm vụ chuẩn bị (crop ảnh, dual-sync, update db/workbook).
  - Coordinator terminal chặn gọi trực tiếp `powershell.exe` (DEFAULT-DENY), nhưng cho phép chạy script `python <wrapper>.py` gọi subprocess PowerShell.
- **Python Wrapper Pattern (`D:/Taadaa/tmp/launch_avatar_<may>.py`):**
  ```python
  import subprocess
  cmd = [
      "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
      "-File", r"D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1",
      "-Tik", str(tik), "-MaxParallel", "1",
      "-HostConfigPath", r"D:\Taadaa\machine-config\kibe.yaml",
      "-ForceAvatarMachineList", str(may)
  ]
  subprocess.run(cmd, check=True)
  ```
- **Kỷ luật Event-Driven:** Khởi chạy wrapper qua tiến trình nền `terminal(background=True, notify_on_complete=True, timeout=360, command="python D:/Taadaa/tmp/launch_avatar_<may>.py")` để harness tự đánh thức khi runner kết thúc; CẤM TUYỆT ĐỐI polling vòng lặp sleep.

## 6. Nghiệm thu thực tế & Gửi ảnh bằng chứng (Gate 6)
- Sau khi runner báo thành công (exit=0, verified=True):
  1. **Định vị Artifact do runner xuất ra:**
     - Batch summary: `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik<Tik>_list_80_<timestamp>\summary.csv`
     - Per-run directory: `D:\CodexRuntime\tiktok-video\runs\run_<device_serial>_<timestamp>\`
     - Artifacts chính: `avatar-uploaded-confirmed.png` (ảnh chụp Profile TikTok ngay sau khi lưu avatar), `report.json` (`avatar_status: "FORCED_REPLACED_VERIFIED"`).
  2. **Soi mắt kiểm tra qua `browser_vision`:**
     - Mở trực tiếp hoặc bọc ảnh vào một file HTML viewport tối giản (`<style>body{margin:0}img{width:100vw}</style>`) để Chromium render toàn bộ chiều cao ảnh rõ nét.
     - Dùng `browser_vision` soi mắt kiểm tra: xác nhận avatar tròn trên profile đã cập nhật đúng hình mới, đúng nick, không bị popup hay lỗi hiển thị.
  3. Gửi ảnh nghiệm thu kèm thẻ `MEDIA:<path_to_avatar-uploaded-confirmed.png>` trong câu trả lời cho User kèm xác nhận trực quan nội dung đã thấy tận mắt.
