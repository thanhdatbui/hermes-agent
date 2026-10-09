# Cross-Device Duplicate & Deferred Sync Pitfalls (Case REG-25 & REG-26)

## 1. Bản chất sự cố lệch pha Excel ↔ Máy thật
- **Triệu chứng**: Đến ca nuôi báo "máy thiếu nick" (trên Excel mới ghi 6-7 ID), hệ thống tự động trigger batch reg bù. Nhưng khi vào máy thật thì script báo lỗi `[04_add_account] Không tìm thấy ('Thêm tài khoản')`.
- **Nguyên nhân kép**:
  1. **Thiếu cơ chế Auto-Sync sau batch reg**: Trước đây `_run_all_targets.py` chạy với `--defer-tracking-write` và chỉ coi mình là proof-only launcher, sinh ra các file `tracking_result_stt*.json` nhưng **không tự động sync vào Excel**. Dẫn đến nick đã vào thiết bị thật thành công nhưng file Excel vẫn để trống ô ID.
  2. **Obfuscated Resource-IDs trong Bottom Sheet TikTok**: Khi thiết bị đạt trần cứng 8 tài khoản, TikTok ẩn nút "Thêm tài khoản". Bộ đếm `_acc_count` cũ chỉ check `n72` và `lkp`, trong khi app TikTok phiên bản mới đã obfuscate ID thành: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`. Do đếm ra 0, script không kích hoạt `MACHINE_FULL_8_ACCOUNTS` mà raise nhầm `[04_add_account] Không tìm thấy`.
  3. **Nick Ký Sinh Đăng Nhập Chéo Máy (Cross-Device Duplicate)**: Do các batch reg cũ chạy nhầm serial, một số nick chính chủ của máy khác (ví dụ nick chính chủ của Máy 26, 36, 16, 56) bị login nhầm vào Máy 53, 42, 76, 40, 34. Nick ký sinh chiếm mất 1 slot phần cứng khiến máy kịch trần 8 nick, trong khi slot thật của chính máy đó trên Excel vẫn để trống.

## 2. Quy tắc đối soát chuẩn (BẮT BUỘC ĐỐI SOÁT QUA XML MÁY THẬT)
- **CẤM TUYỆT ĐỐI chỉ đối soát nội bộ trên file Excel**: Kiểm tra trùng lặp trên các dòng của Excel là hoàn toàn vô dụng vì nick ký sinh chỉ tồn tại trên UI của máy thật, không hề có dòng nào trên Excel của máy bị ký sinh.
- **Phương pháp đối soát chuẩn**:
  1. Lấy UI XML thật của thiết bị qua atx-agent hoặc screencap: Quét các button row trong dropdown account switcher (`com.ss.android.ugc.trill:id/...` có bounds `[0, y][1080, y]`).
  2. Trích xuất danh sách 8 username TikTok thực tế đang đăng nhập trên thiết bị.
  3. So sánh 8 username đó với 8 dòng của máy trên file Excel `taikhoan_dat_v2_updated .xlsx`:
     - Nếu có nick trên máy mà không có trên Excel của máy đó: Lập tức truy vấn xem nick đó thuộc máy nào trong toàn bộ workbook.
     - Nếu nick thuộc máy khác: Đó là **Nick ký sinh**.
     - Nếu nick không có ở bất kỳ đâu: Đó là **Nick mồ côi**.

## 3. Quy trình giải phóng và xử lý:
1. **Dùng Watchdog Idle Reconcile**:
   - Dùng `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py` chạy event-driven: Chờ máy mục tiêu hoàn toàn rảnh (0 locks, HomeScreen/Idle).
   - Mở TikTok, chuyển đúng sang nick ký sinh, vào Settings & Privacy -> Logout duy nhất nick ký sinh đó để trả lại slot trống (từ 8 về 7 nick).
   - Tuyệt đối cấm logout nhầm 7 nick chính chủ còn lại.
2. **Auto-Sync sau Batch Reg**:
   - `_run_all_targets.py` sau khi hoàn thành batch bắt buộc gọi `write_deferred_results_sequential` để ghi khóa tuần tự có backup vào Excel.
   - `deferred_tracking_writer.py` tích hợp `resolve_tracking_slot` tự động dò tìm slot trống nếu file JSON bị thiếu `tracking_row`/`tik` hoặc dòng mong muốn bị drift.
