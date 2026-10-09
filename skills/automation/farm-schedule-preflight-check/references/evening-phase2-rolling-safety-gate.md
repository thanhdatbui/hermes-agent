# Quy Tắc Cuốn Chiếu An Toàn Sau Phiên 2 Ca Tối: Khóa Chặt Khe P1-P2 (2026-09-17)

## 1. Bối Cảnh & Nguy Cơ Tranh Chấp Khe Giữa Phiên (P1-P2 Hazard)
Trong mô hình nuôi farm Samsung S7, Ca tối gồm 2 phiên:
- **Phiên 1 (17:35 - 18:45 / 19:25):** 79/80 máy chạy nuôi feed.
- **Phiên 2 (19:15 - 20:25 / 21:25):** 79/80 máy tiếp tục chạy phiên 2 (Feed + Upload).

**Khoảng cách nghỉ giữa P1 và P2 trên mỗi máy chỉ kéo dài từ 35 đến 60 phút.**
- Nếu mở watchdog cuốn chiếu ngay sau Phiên 1 (từ 18:45):
  1. Tác vụ Up Avatar hoặc Login GPM (vướng OTP/Google Prompt/Dual OAuth) ngốn từ 10-15 phút/acc.
  2. Máy đang chạy GPM/Avatar dở dang thì đến giờ Phiên 2 nuôi TikTok ập tới.
  3. Hậu quả: Xung đột `device-lock`, tranh chấp thiết bị S7, runner nuôi acc bị `SKIPPED_DEVICE_LOCKED` hoặc văng timeout, làm vỡ lịch nuôi chính của Farm.

## 2. Quy Tắc Vàng: CHỈ MỞ CUỐN CHIẾU SAU PHIÊN 2 CA TỐI
- **Khóa tuyệt đối khung giờ P1-P2 (`17:35 - 20:15`):** Tuyệt đối CẤM mọi watchdog tự động (Avatar, GPM) nhảy vào chiếm máy giữa 2 phiên này.
- **Thời điểm mở cửa cuốn chiếu:** Bắt đầu từ **20:15** (thời điểm các máy đầu tiên hoàn tất Phiên 2).
- **Cửa sổ thênh thang:** Từ **20:15 đến 23:45** (~3.5 tiếng rảnh hoàn toàn trước Ca 4 đêm lúc 00:00).

## 3. Kiến Trúc Cuốn Chiếu Nối Tiếp Từng Máy (Per-Machine Pipeline)
Không bắt cả farm phải đợi nhau, nhưng phải tuân thủ thứ tự trên từng máy:
1. **Bước 1 (Up Avatar):** Máy nào xong Phiên 2 (từ 20:15) nhả lock -> máy đó vào chạy Up Avatar nếu acc thiếu avatar.
2. **Bước 2 (Login GPM & Dual OAuth):** Ngay khi máy đó có avatar (hoặc nick đã có avatar sẵn) -> bốc vào Login GPM & lấy OAuth ngay (`is_machine_avatar_ready(mid)`).
3. **Giới hạn an toàn:** Tối đa 2 acc/cổng proxy/ngày, mỗi máy chỉ login 1 lần/ngày, concurrency tối đa 10 workers.

## 4. Cấu Hình Cron Schedule Chuẩn
- `post-evening-avatar-watchdog`: `*/5 20,21,22,23 * * *` (Schedule cứng).
- `post-evening-gpm-login-watchdog`: `*/5 20,21,22,23 * * *` (Schedule cứng).
- Cả 2 script đều dùng logic time gate: `20 * 60 + 15 <= (h * 60 + m) <= 23 * 60 + 45`.
