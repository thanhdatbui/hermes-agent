# Hermes Direct Recovery & Per-Nick Follow Cooldown Protocol (19/08/2026)

## 1. Chuyển Đổi Kiến Trúc AI Auto-Recovery (Quy Về 1 Đầu Mối Hermes Session)
- **Vấn đề của kiến trúc cũ (Subprocess `agent.py`)**:
  - `alerts.py` spawn subprocess `agent.py` chạy nền trơ trọi, không có toolset (`read_file`, `patch`, `pytest`, `terminal`), mỗi lần chạy phải gửi lại ảnh qua prompt one-shot và dễ rơi vào fallback bấm phím `BACK` mù quáng làm hỏng hiện trường trước khi xử lý thật.
- **Kiến trúc mới (Hermes Direct Handling)**:
  - Tắt hoàn toàn việc spawn subprocess trong `automation_core/alerts.py`.
  - Khi máy dừng phiên: Script chỉ chụp ảnh đóng dấu Banner Đỏ `[MAY XX] - HH:MM DD/MM` và gửi cảnh báo `🟡 GIỮ HIỆN TRƯỜNG ĐỂ HERMES AGENT XỬ LÝ` về nhóm Telegram `Farm Alerts` (`-5373649734`).
  - **Hermes Agent trong session trực tiếp đảm nhận toàn bộ**:
    1. Đọc ảnh thật (`vision_analyze`) và phân tích UI XML.
    2. Sửa code tận gốc trong repo (`patch`/`read_file`), chạy `pytest` test suite nghiệm thu.
    3. Gửi lệnh tương tác chính xác (tap tọa độ, vuốt an toàn) trực tiếp lên thiết bị.
    4. Báo cáo nghiệm thu và phân tích rõ ràng cho user.

## 2. Quy Tắc Cách Ly Cooldown Nhả Follow Riêng Từng Nick
- **Nguyên tắc**: Hiện tượng nhả follow xảy ra theo từng NICK/Tài khoản TikTok (do trust score hoặc rate-limit của nick), KHÔNG PHẢI do máy/IP.
- **Cơ chế lưu state**:
  - Lưu trạng thái theo từng nick cụ thể: `D:\Taadaa\tiktok-follow\runs\state\follow_state_<machine>_row_<account_row_index>.json`.
  - Khi một nick bị nhả follow sau khi vuốt kiểm tra (`FOLLOW_FAILED`): Ghi nhận `follow_failed = True` và `follow_failed_date = "YYYY-MM-DD"`.
  - **Phạm vi cách ly**: Chỉ dừng follow trong ngày cho **ĐÚNG NICK BỊ DÍNH**. Các nick khác trên cùng máy đó (Row khác) **hoàn toàn KHÔNG BỊ CHẶN**, vẫn chạy lướt Feed và Follow chéo bình thường.
  - Sang ngày mới (00:00), cờ cooldown tự động reset.
- **Phân biệt rạch ròi loại lỗi**:
  - Chỉ áp dụng cooldown cho lỗi nhả follow thật (`bị nhả sau vuốt` / `TikTok không nhận follow`).
  - Lỗi điều hướng (`MANUAL_REVIEW`, `OPEN_TIKTOK_FAILED`, `search navigation fail`) **TUYỆT ĐỐI KHÔNG gán cờ `follow_failed`** để tránh chặn oan tài khoản.

## 3. Workflow Cron Nuôi Nick 4 Bước Khép Kín (Feed ➔ Follow ➔ Upload Phiên Cuối)
1. **Preflight & Prepare**: Check VPN `tun0`, mở TikTok, vào Account Switcher chọn đúng Nick theo Row của ca.
2. **Feed Session Smoke**: Lướt 3 Tab (FYP 85%, Following 8%, Friends 7%) + Phân tầng delay thoát popup (Live 6-14s tap X, Shop 3-7s tap X, Repost 2-4s tap X, CTA vuốt lướt, Thẻ gợi ý bấm Follow lại).
3. **Follow Hook**: Sau khi lướt feed xong, kiểm tra nếu nick chưa bị nhả follow hôm nay thì chạy follow. Nếu bị nhả $\rightarrow$ dừng ngay lập tức và cách ly riêng nick đó trong ngày.
4. **Upload Hook (Phiên Cuối Ca)**:
   - Tự động kích hoạt ở **Phiên cuối cùng của ca (`session_index == 3`)**.
   - Đọc workbook tương ứng (`Tik1.xlsx`, `Tik2.xlsx`, `tik3.xlsx`... theo Row), lấy thư mục video (`folder_video`), kiểm tra file MP4 đã render sẵn (`D:\TIKTOK-videonuoinick\<folder>\<posted_count + 1>.mp4`).
   - Nếu file hợp lệ $\rightarrow$ chạy `tiktok-video` đăng bài; nếu chưa có $\rightarrow$ Safe-skip không nghẽn luồng.
