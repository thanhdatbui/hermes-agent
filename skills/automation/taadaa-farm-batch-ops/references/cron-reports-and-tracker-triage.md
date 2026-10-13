# Chẩn Đoán & Khai Thác Báo Cáo Farm (Hermes Cron Output, Tracker Report & Bẫy MISSING_ID)

## 1. Kiến Trúc & Vị Trí Lưu Báo Cáo Hermes Cron

### A. Vị trí & Cấu trúc thư mục
- Toàn bộ output của cronjob được lưu tại:
  `C:/Users/Kibe/AppData/Local/hermes/cron/output/<job_id>/`
- **CẠM BẪY PERMISSION ERROR [Errno 13]**:
  Mỗi `<job_id>` là một **thư mục (directory)** chứa các file log theo timestamp `YYYY-MM-DD_HH-MM-SS.md`, **KHÔNG PHẢI file đơn lẻ**. Mở trực tiếp đường dẫn `output/<job_id>` bằng `open()` sẽ văng lỗi `PermissionError: [Errno 13] Permission denied`.

### B. Mẫu Python O(1) đọc báo cáo mới nhất an toàn
```python
import os

job_id = "9c7a147d48b8"  # Thay bằng job_id cần tra cứu
output_dir = f"C:/Users/Kibe/AppData/Local/hermes/cron/output/{job_id}"

if os.path.exists(output_dir) and os.path.isdir(output_dir):
    files = sorted(os.listdir(output_dir))
    if files:
        latest_file = os.path.join(output_dir, files[-1])
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
        print(f"=== LATEST REPORT ({files[-1]}) ===\n{content}")
```

### C. Cơ chế Silent Watchdog
- Nếu file markdown chỉ có nội dung:
  `Status: silent (empty output)`
  -> Watchdog vận hành chuẩn xác theo nguyên tắc **"Im lặng khi bình yên"** (không có lỗi nền tảng hoặc không có sự kiện mới cần alert). Tuyệt đối không phán đoán watchdog bị lỗi khi thấy output rỗng.

---

## 2. Các Cronjob Báo Cáo Trọng Yếu & File Artifact

| Tên Cronjob | Job ID | Lịch chạy | Script điều phối | Chức năng & File Artifact |
| :--- | :---: | :---: | :--- | :--- |
| `farm-render-download-watchdog` | `9c7a147d48b8` | `0 */6 * * *` | `farm_render_download_watchdog.py` | Báo cáo tiến độ Render Tik1..Tik8 và Download video gốc cho Farm Kibe (M1-80) và Farm Admin (M201-280). |
| `daily-tiktok-farm-tracker` | `9f7a9a3969b2` | `0 7 * * *` | `cron_tiktok_daily_tracker.py` | Gọi `D:/Taadaa/tools/tiktok_account_tracker.py`. Xuất bảng tính `D:/Taadaa/reports/tiktok_tracker_report.xlsx`. |
| `tiktok-feed-session-watchdog` | `1d62cb3562e0` | `*/5 * * * *` | `feed_session_watchdog.py` | Báo cáo tổng kết từng phiên nuôi, tự động phân tách 3 kênh Telegram riêng biệt: Lướt Feed ➔ nhóm `Tiktok Luot Nuoi Acc` (`-5377611430`), Follow chéo ➔ nhóm `Tiktok Follow` (`-5127276494`), Đăng video ➔ nhóm `Tiktok video` (`-5435853713`). |
| `gpm-oauth-pool-6h-report` | `55599d8b1551` | `0 */6 * * *` | `cron_gpm_oauth_pool_6h_report.py` | Báo cáo tiến độ bốc session GPM nạp OAuth OmniRoute pool (:20129). |
| `hotmail-gpm-lifecycle-6h-report` | `61570a1e37b1` | `0 */6 * * *` | `cron_hotmail_gpm_lifecycle_6h_report.py` | Báo cáo vòng đời Hotmail ➔ GPM ➔ ChatGPT ➔ Codex. |
| `gmail-gpm-2fa-6h-report` | `88a5cd11c3a9` | `0 */6 * * *` | `cron_gmail_gpm_2fa_6h_report.py` | Báo cáo tiến độ bật 2FA Gmail qua profile GPM Group 10. |

### D. Quy Chuẩn Phân Tách Kênh Báo Cáo Cron TikTok (3 Kênh Riêng Biệt)
Từ ngày 2026-10-09, theo chỉ đạo User, báo cáo nuôi TikTok không còn gom chung mà bắt buộc phân tách thành 3 nhóm Telegram độc lập:
1. **Lướt feed**: Gửi về nhóm **Tiktok Luot Nuoi Acc** (`-5377611430`) thông qua stdout của cronjob `tiktok-feed-session-watchdog`.
2. **Follow chéo**: Gửi về nhóm **Tiktok Follow** (`-5127276494`) thông qua hàm `dispatch_split_reports` gọi Telegram API trực tiếp.
3. **Upload video**: Gửi về nhóm **Tiktok video** (`-5435853713`) thông qua hàm `dispatch_split_reports` gọi Telegram API trực tiếp.

### E. Cấu trúc bảng tính `tiktok_tracker_report.xlsx`
File tại `D:/Taadaa/reports/tiktok_tracker_report.xlsx`, sheet `TikTok Accounts` gồm 14 cột chuẩn:
1. `Máy`
2. `Username`
3. `Tên hiển thị`
4. `UID`
5. `Ngày Tạo`
6. `Follower`
7. `Tăng Follow`
8. `Tổng Like`
9. `Tăng Like`
10. `Số Video`
11. `Trạng Thái` (`LIVE`, `ERROR`, `PENDING`)
12. `Avatar` (`CÓ`, `CHƯA CÓ`)
13. `Cắn Đề Xuất` (`CÓ`, `KHÔNG` — Nick có 0 video luôn là `KHÔNG`)
14. `Cập Nhật` (Timestamp quét)

---

## 3. Chẩn Đoán Nick Dừng Đăng Video Lâu Ngày (Bẫy MISSING_ID trong Tik<N>.xlsx)

### A. Hiện tượng thực tế
- User hỏi: *"Nick @abc trên Máy M sao đăng video cuối cùng từ tận ngày X (nhiều tuần trước) vậy?"*.
- Kiểm tra `taikhoan_run_safe.xlsx`: Nick vẫn tồn tại, tài khoản vẫn sống.
- Kiểm tra TikTok Web / Tracker: Nick vẫn `LIVE`, nhưng số lượng video dừng lại ở một con số cố định.

### B. Căn nguyên cốt lõi
- Script runner (`D:/Taadaa/Tiktok-video/scripts/tiktok_workflow`) đọc danh sách account từ file workbook cụ thể của slot đó: `D:/OneDrive/TaadaaData/kibe/Tik<N>.xlsx`.
- Trong file `Tik<N>.xlsx`:
  ```text
  Row M: (Máy: M, Serial: '...', ID: None, Folder: F, Video: V, Note: 'MISSING_ID')
  ```
- Khi cột `ID` mang giá trị `None` hoặc chuỗi rỗng kèm nhãn `MISSING_ID`, runner tự động coi dòng đó không có tài khoản hợp lệ và **skip hoàn toàn Máy M** trong mọi ca chạy.

### C. Quy trình khắc phục O(1)
1. **Truy vấn ID gốc**:
   Tra cứu ID của Máy M trong `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` hoặc master sheet `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`.
2. **Khôi phục ô ID & gỡ cờ**:
   Cập nhật lại giá trị username vào cột ID (cột C) của dòng Máy M trong `Tik<N>.xlsx`, xóa nhãn `MISSING_ID` (dùng cơ chế atomic update hoặc ghi an toàn).
3. **Đối soát Folder video**:
   Xác nhận folder video `D:/TIKTOK-videonuoinick/<folder_id>` đã được render đủ $\ge 30$ clip và có `avatar.jpg`.
4. **Vận hành**:
   Ở ca đăng video tiếp theo của Tik đó, runner sẽ tự động nạp nick và tiếp tục đăng video bình thường.

---

## 4. Xử Lý Tình Huống Render 1 Tik Báo 79/80 (98.8%)
- Khi báo cáo 6h `farm-render-download-watchdog` ghi nhận một Tik đạt `79/80 folder [98.8%]`:
  + Tuyệt đối không suy đoán toàn cụm bị treo.
  + Dùng script kiểm tra số lượng clip `.mp4` trong từng folder của Tik đó (`formula: (m - 1) * 8 + slot`).
  + Tìm folder có `< 30 clip` (thường là 29 clip, thiếu đúng 1 clip).
  + Chạy render bù đơn lẻ đúng folder đó bằng FFmpeg hoặc single-task script để đưa toàn bộ cụm về 100% (80/80).

---

## 5. Bẫy Ngộ Nhận Thiết Bị Offline vs Nick Kẹt Khi Đọc Báo Cáo Stale Watchdog (> 14 Ngày)

### A. Triệu chứng & Bẫy kết luận vội vàng
- Watchdog `daily-stale-upload-accounts-watchdog` hoặc lệnh audit báo:
  `🚨 M10, M44, M55, M69... kẹt > 14-26 ngày (1-3 clip)`.
- Khi agent chạy `adb devices` thấy máy đó đang offline (do vừa nghẽn bus USB), agent vội vàng phán: *"Máy M bị hỏng phần cứng / tuột cáp suốt 20+ ngày qua"*.
- **HẬU QUẢ**: Bị User bắt bẻ và chỉnh đốn ngay lập tức vì thực tế máy đó hôm qua và sáng nay vẫn online chạy bình thường.

### B. Kỷ luật kiểm chứng đối soát O(1) (BẮT BUỘC)
- Trước khi tuyên bố máy bị hỏng phần cứng lâu ngày, BẮT BUỘC kiểm tra trạng thái **7 slot còn lại trên cùng máy** trong `taikhoan_run_safe.xlsx` hoặc database SQLite `snapshots`:
  ```python
  # Kiểm tra số video của cả 8 slot trên máy M
  # Nếu các slot khác vẫn có video tăng đều (10 - 33 clip) và có snapshot trong 24h qua:
  # -> THIẾT BỊ PHẦN CỨNG HOÀN TOÀN BÌNH THƯỜNG!
  ```
- **Quy tắc phân định**:
  1. Con số "kẹt > 20 ngày" là thời gian trôi của **riêng 1 tài khoản/slot cụ thể**, KHÔNG PHẢI thời gian máy bị offline.
  2. Hiện tượng nhiều máy rớt ADB cùng lúc (như 30–40 máy) trên Host chạy >24h là do **nghẽn buffer bus USB 2.0 EHCI tạm thời**, sẽ tự động được giải phóng sạch sẽ bằng System Bus Reset lúc 11:35 trưa qua Task Scheduler `Taadaa_Farm_Daily_Reboot_1135`.

---

## 6. Căn Nguyên Kẹt Slot Lẻ Trên Máy Online (Draft Resume Trap & Chu Kỳ 96h)

### A. Bug "Bản Nháp Trap" (Draft Resume Fallthrough)
- **Cơ chế gây lỗi trong `state_machine.py`**:
  1. Khi tài khoản có bản nháp cũ lưu trên Profile, hàm `_handle_video_pick` phát hiện `has_profile_draft` và gọi `_resume_draft_from_profile`.
  2. Script tap vào bản nháp để mở nhưng không xác nhận được màn hình Composer (`COMPOSER_NOT_CONFIRMED`).
  3. Script log cảnh báo và fallthrough sang luồng upload thông thường:
     `[VIDEO_PICK] Mở bản nháp không thành công; tiếp tục fallthrough luồng upload chuẩn`.
  4. **Tử huyệt**: Sau khi mở bản nháp thất bại, màn hình điện thoại **vẫn đang kẹt trong giao diện Thư viện Bản nháp**, hoàn toàn không có thanh điều hướng Home với nút `[+]` (Quay) ở đáy màn hình.
  5. Luồng upload thường tìm không thấy nút `[+]` $\rightarrow$ văng lỗi `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control` $\rightarrow$ abort sang `MANUAL_REVIEW`.
  6. Các chu kỳ sau lặp lại y hệt do bản nháp vẫn nằm trên Profile, khiến nick đó bị kẹt vĩnh viễn ở số clip thấp.
- **Cách khắc phục**:
  - Tức thời: Vào app TikTok trên máy đó xóa sạch bản nháp đang lưu trên Profile.
  - Tận gốc: Trong `state_machine.py`, nếu resume bản nháp thất bại, BẮT BUỘC phải thực hiện lệnh `Back` hoặc `Home` để đưa app về màn hình chính có thanh điều hướng trước khi fallthrough sang luồng upload thường.

### B. Hiệu ứng cộng dồn chu kỳ nuôi 4 ngày (96h)
- Farm vận hành theo chu kỳ cố định 4 ngày: **Day 0 (Row 1, 3, 5) — Day 1 (Row 2, 4, 6) — Day 2 (Row 7, 8) — Day 3 (Nghỉ)**.
- Mỗi row chỉ đến lượt chạy đúng **1 lần duy nhất sau mỗi 96 giờ**.
- Nếu 1 nick dính cờ nghỉ dưỡng sinh (trước ngày 11/10) hoặc gặp lỗi UI (như bug bản nháp ở trên), nick đó phải chờ tiếp **4 ngày sau** mới có cơ hội thử lại.
- Chỉ cần trượt 4 chu kỳ liên tiếp là nick đã trôi thành **16 ngày kẹt**, dẫn đến cảnh báo stale > 14 ngày của watchdog trong khi dàn máy vẫn chạy đều đặn mỗi ngày.
