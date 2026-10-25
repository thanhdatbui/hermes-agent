# Admin Render Worker: In-Flight Game Guard & Auto-Pause Architecture

## 1. Bối Cảnh & Vấn Đề (Root Cause Analysis)
Trên máy Admin (`admin-farm`), tiến trình render video `run_admin_render_worker.py` gọi `random_batch_render.py` và `ffmpeg.exe` ngốn từ 70% - 95% CPU và ~2GB RAM.
Khi người dùng chơi game thi đấu (**Warcraft III / TFT**), máy bị giật lag nghiêm trọng nếu render vẫn chạy.

### Các Lỗ Hổng Của Giải Pháp Watchdog Định Kỳ (Task Scheduler 15m):
1. **Độ trễ quá lớn (Up to 15 minutes):** Khi người dùng mở game, render worker tiếp tục chiếm CPU tới 15 phút trước khi watchdog theo lịch kịp quét.
2. **Hiện tượng "Giết xong tự đẻ lại" (Task Loop Respawn):** Khi watchdog quét và kill tiến trình `ffmpeg` hoặc `random_batch_render.py` (văng `returncode 15`), vòng lặp `for t in tasks:` của worker cũ chỉ ghi log `[WARN]` rồi ngay lập tức nhảy sang task tiếp theo và spawn `ffmpeg` mới trong cùng 1 giây! Kết quả là CPU lập tức bị nghẽn trở lại.

---

## 2. Kiến Trúc Chuẩn (In-Flight Game Guard Nhúng Trực Tiếp Vào Worker)

### A. Danh Sách Tiến Trình Game Được Bảo Vệ
- **Warcraft III:** `war3.exe`, `frozen throne.exe`, `w3l.exe`, `warcraft iii.exe` (kiểm tra exact name hoặc substring `war3` / `frozen throne`).
- **TFT (In-Match):** `league of legends.exe`, `tftclient.exe`, `tftclient-win64-shipping.exe`.
- **CẤM đưa vào danh sách:** Các ứng dụng khay hệ thống / overlay như `TFTAcademy.exe`, `Overwolf.exe`, `RiotClientServices.exe` vì chúng chạy nền 24/7, sẽ làm render bị treo vĩnh viễn.

### B. Cơ Chế 3 Tầng Bảo Vệ Của `run_admin_render_worker.py`
1. **Pre-Flight Check:** Trước khi quét file Excel hoặc nhận task, kiểm tra `is_gaming_active()`. Nếu đang chơi game, dọn sạch `ffmpeg` mồ côi và ngủ 10s lặp lại, tuyệt đối không tạo job mới.
2. **In-Flight Guard (Polling mỗi 2 giây):**
   - Không dùng `subprocess.run()` chặn cứng (blocking) 40 phút.
   - Dùng `subprocess.Popen(..., creationflags=CREATE_NO_WINDOW)` và vòng lặp `while proc.poll() is None: time.sleep(2)`.
   - Ngay khi phát hiện game được mở lên trong lúc clip đang render dở:
     + Lập tức kill toàn bộ cây tiến trình: `proc`, các process con của nó (`ffmpeg.exe`).
     + Chạy hàm quét `kill_all_ffmpeg()` dọn sạch mọi tiến trình render rác.
     + Thoát khỏi vòng render trong vòng **$\le 2$ giây**.
3. **Standby & Auto-Resume:**
   - Worker chuyển sang trạng thái ngủ kiểm tra mỗi 5s (`time.sleep(5)`).
   - Ngay khi người dùng thoát game hoàn toàn (`not is_gaming_active()`), worker tự động ghi log `[RESUME]` và tiếp tục render mà không cần bất kỳ can thiệp tay nào.

---

## 4. Cạm Bẫy Chẩn Đoán Khi User Báo "Đã Thoát Game Sao Không Tự Resume Render?"
- **Triệu chứng:** Người dùng đã đóng trận TFT/War3, nhưng báo rằng render worker không chịu chạy lại (không thấy ffmpeg trong task manager, số clip không tăng).
- **Nguyên nhân gốc rễ (False Standby / Disk Full Crash):**
  1. Worker THỰC CHẤT ĐÃ RESUME và đang gọi `ffmpeg`.
  2. Tuy nhiên, ổ `D:` Admin bị cạn kiệt dung lượng (`Free = 0 Byte` do downloader 40 workers cào video gốc dồn đống).
  3. Mỗi lần spawn `ffmpeg` hoặc mở file ghi, hệ điều hành trả về `ERROR: [Errno 28] No space left on device` sau đúng 1–2 giây.
  4. Worker chỉ bắt mã lỗi returncode 2, ghi log `[WARN]` rồi nhảy sang folder kế tiếp. Trong vòng vài chục giây, worker quét qua hàng chục folder mà không có tiến trình `ffmpeg` nào tồn tại lâu dài, khiến người dùng tưởng worker bị đơ hoặc Game Guard không nhả.
- **Quy trình kiểm tra & xử lý:**
  1. BẮT BUỘC kiểm tra dung lượng ổ đĩa trước tiên: `Get-PSDrive D`.
  2. Đọc 40 dòng cuối log worker: `Get-Content C:\Users\Admin\admin_render_worker.log -Tail 40` để kiểm tra có xuất hiện `Errno 28` hay không.
  3. Nếu đĩa D chạm đáy 0 Byte:
     - Tạm dừng supervisor downloader (`run_admin_downloader_service.py`) và tiến trình cào con `download_by_niche.py`. Lưu ý Task Scheduler có task `Taadaa_Admin_Downloader_15m` tự bật lại mỗi 15m.
     - Giải phóng đĩa tức thì: Xóa video gốc của các folder đã có đủ $\ge 45$ clip thành phẩm.
     - Sau khi có buffer đĩa (>= 15–20 GB), worker render sẽ tự động chạy mượt mà trở lại.

---

## 3. Deployment & Command Line Limits
- Khi deploy cập nhật code từ xa qua `admin_ssh.py`, chú ý giới hạn độ dài dòng lệnh của Windows (8191 ký tự).
- Không nhồi toàn bộ code python thô dạng base64 nếu vượt quá giới hạn.
- Sử dụng chuẩn nén `zlib.compress()` kết hợp base64 để nén code trước khi gửi qua SSH, hoặc deploy từng file riêng biệt.
