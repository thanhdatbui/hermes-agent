# Canary Single-Device Test Quy Trình Đăng Video TikTok & Báo Cáo Chuẩn B5 (2026-09-06)

## 1. Mục Đích & Bối Cảnh
Khi cần chạy Canary Test đăng video trên một máy cụ thể trong farm (sau khi patch code, sửa lỗi UI hoặc verify recovery), quy trình bắt buộc phải tuân thủ chuẩn an toàn farm, chống ô nhiễm môi trường Python, quản lý device lock chặt chẽ và báo cáo kết quả theo định dạng chuẩn B5.

## 2. Quy Trình Thực Thi 5 Bước Chuẩn

### Bước 1: Dọn Dẹp Stale Device Lock (Nếu Có)
Trước khi khởi chạy, kiểm tra thư mục lock:
`C:/Users/Kibe/.codex/device-locks/`
- Tìm các file lock liên quan đến máy: `machine_<id>.lock.json` hoặc `serial_<serial>.lock.json`.
- Nếu file lock tồn tại nhưng tiến trình (PID) bên trong đã chết hoặc không còn hoạt động, tiến hành xóa (unlink) file lock để tránh bị chặn `SKIPPED_LOCKED`.

### Bước 2: Khởi Chạy Lệnh Canary & Bẫy Timeout 600s (Windows Process Lifecycle)
- **CẤM TUYỆT ĐỐI** quét đĩa diện rộng (`os.walk`, `find`, `grep -r`, `search_files`).
- **BẮT BUỘC** dùng `env -u PYTHONPATH` để tránh ô nhiễm môi trường PIL/Hermes venv làm crash import C-extensions.
- **Thời lượng thực tế:** Quy trình đăng video đầy đủ (20 states: connect, wake/unlock, dismiss popups, switch account, draft cleanup, video pick, caption/hashtag fill, post, verify post profile grid 120s, post recheck, workbook update, delete remote media, release) kéo dài **12 - 15 phút** (~720 - 900 giây).
- ⚠️ **Bẫy Terminal Timeout 600s (Foreground Expiry):**
  - Công cụ `terminal` ở chế độ foreground có giới hạn trần timeout 600s. Khi hết 600s, terminal tool sẽ báo `[Command timed out after 600s]` (exit code 124).
  - **CỰC KỲ QUAN TRỌNG:** Shell bash ngắt nhưng tiến trình con Windows `python.exe` của `scripts.tiktok_workflow` **VẪN ĐANG TIẾP TỤC CHẠY NGẦM** trong hệ điều hành Windows!
  - **TUYỆT ĐỐI CẤM** kết luận là run thất bại, và **CẤM CHẠY LẠI LỆNH MỚI NGAY** vì sẽ gây xung đột Device Lock hoặc double-post video lên TikTok.
  - **Cách xử lý đúng:**
    1. Kiểm tra tiến trình ngầm bằng PowerShell:
       ```powershell
       Get-CimInstance Win32_Process -Filter "CommandLine like '%scripts.tiktok_workflow%'" | Select-Object ProcessId, CommandLine
       ```
    2. Theo dõi tiến độ state machine qua 20 dòng cuối của file log:
       `tail -n 20 D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/execution.log`
    3. Đợi tiến trình hoàn tất an toàn qua PowerShell `WaitForExit`:
       ```powershell
       $p = Get-Process -Id <pid> -ErrorAction SilentlyContinue
       if ($p) { $p.WaitForExit(300000); Write-Host "Exit Code: $($p.ExitCode)" }
       ```
    4. Chỉ đọc kết quả từ `report.json` và checkpoint sau khi tiến trình đã kết thúc hoàn toàn.

**Lệnh thực thi chuẩn (Workdir: `D:\Taadaa\Tiktok-video`):**
```bash
env -u PYTHONPATH python -m scripts.tiktok_workflow \
  --config "D:\Taadaa\Tiktok-video\config.example.yaml" \
  --workflow-workbook "D:\OneDrive\TaadaaData\kibe\Tik<N>.xlsx" \
  --single-device <serial> \
  --video-number <num> \
  --no-dry-run
```

### Bước 3: Thu Thập Bằng Chứng & Artifacts
Sau khi lệnh kết thúc (bất kể exit code 0 hay non-zero):
1. **Kiểm tra Exit Code:** (0: DONE/Success, 2: MANUAL_REVIEW, 1: Error).
2. **Xác định Run Directory:** Tìm thư mục chạy mới nhất dưới:
   `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\`
3. **Đọc Ground Truth Reports:**
   - Đọc file `report.json` (kiểm tra `status`, `reason`, `last_state`).
   - Đọc các dòng cuối của `execution.log`.

### Bước 4: Chụp Ảnh Hiện Trường Khi Có Lỗi (Screencap)
Nếu kết quả không đạt `DONE` / `SUCCESS` (rơi vào `MANUAL_REVIEW` hoặc `ERROR`):
- Chụp ảnh màn hình thiết bị qua ADB exec-out:
  ```bash
  adb -s <serial> exec-out screencap -p > C:/Users/Kibe/AppData/Local/hermes/cache/images/m<id>_canary_error.png
  ```
- Đồng thời lưu 1 bản sao lưu trong run directory:
  `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\error_screen.png`

### Bước 5: Báo Cáo Kết Quả Theo Chuẩn B5 (Standard B5 Closeout)
Báo cáo kết quả ngắn gọn, rõ ràng theo đúng 6 trường thông tin cốt lõi của chuẩn B5:
```markdown
### Báo Cáo Canary Test Đăng Video (Máy <id> - Chuẩn B5)

- **Status:** <status> (SUCCESS / MANUAL_REVIEW / FAILED)
- **Account:** <account_username> (Hàng X trong Tik<N>.xlsx)
- **Video Number:** <video_number> (<path_to_video>, SHA-256: <hash>)
- **Last State:** <last_state> (ví dụ: RELEASE)
- **Post Verified:** <true/false> (Submission rời composer / POST_RECHECK)
- **Exit code:** <exit_code> (0: thành công)
```
---

### Chi Tiết Thực Thi & Bằng Chứng
- **Device Lock:** Đã kiểm tra/dọn stale lock.
- **Run Directory:** `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>`
- **Lý do dừng phiên (report.json):** `<reason>`
- **Ảnh chụp màn hình hiện trường (Screencap):**
  - `<path_to_image>`
```
