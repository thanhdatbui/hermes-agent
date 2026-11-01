# Kỷ Luật Anti-AFK Preflight Cho Reboot Định Kỳ & Trích Xuất Media An Toàn (2026-11-01)

## 1. Cơ Chế Chặn Reboot Khi Có Game / Tác Vụ Đang Chạy (Anti-AFK Guard)
- **Hiện tượng**: Task Scheduler có lịch reboot máy lúc 11:20 - 11:50 sáng (mỗi 5 phút quét một lần) nhưng máy không reboot.
- **Nguyên nhân gốc rễ**: Script `C:\Taadaa_Service\farm_preflight_daily_reset.py` có hàm kiểm tra `is_admin_tft_match_in_progress()`. Nếu phát hiện game TFT (`League of Legends.exe`, `TFTClient...`) hoặc Warcraft (`War3.exe`, `w3l.exe`) đang chạy trên Admin PC, hệ thống **CHỦ ĐỘNG ABORT LỆNH REBOOT** để bảo vệ người dùng không bị AFK / xử thua.
- **Quy chuẩn**: 
  - Khi người dùng hỏi tại sao máy không reboot đúng giờ, Coordinator phải tra cứu `C:\Taadaa_Service\daily_reset.log` trước để đối soát thay vì đoán mò.
  - Tuyệt đối không can thiệp kill game để ép reboot.

## 2. Inbound Vision Hard-Gate & Strict Turn Isolation tại Gateway
- **Cơ chế**: Triển khai tại `D:/Taadaa/Hermes/gateway/run.py` (dòng 11830) trước khi gửi phản hồi:
  - Nhận diện ảnh đầu vào: Quét `event.media_urls` hoặc chuỗi `[Image attached at:` / `[Replied-to image`.
  - Quét `tool_calls` và `tool` message chỉ trong turn hiện tại (`history_offset` trở đi, xóa hoàn toàn fallback toàn bộ messages).
  - Bắt buộc tool vision (`browser_vision`, `vision_analyze`, `ag_cli_vision`) có content > 10 ký tự và không dính từ khóa lỗi (`error`, `failed`, `traceback`).
  - Vi phạm hoặc ngoại lệ: Ghi đè `response` thành `⛔ [GATEWAY BLOCKED - INBOUND VISION GATE]` (Fail-Closed).

## 3. Khóa Chặt cv2.VideoCapture Bằng Subprocess 10s + Windows taskkill
- Không chạy vòng lặp `cv2.VideoCapture` đồng bộ trong terminal chính vì sẽ bị deadlock DirectShow/Media Foundation kéo dài 3600s làm sập Gateway.
- Bắt buộc dùng `safe_extract_video_frame(video_path, timestamp_s, timeout_s=10.0)` trong `anti_hang_guard.py`:
  - Cô lập trong subprocess riêng biệt với `stdin=DEVNULL`.
  - Khi timeout trên Windows: dùng `taskkill /F /T /PID` diệt toàn bộ cây tiến trình con.
