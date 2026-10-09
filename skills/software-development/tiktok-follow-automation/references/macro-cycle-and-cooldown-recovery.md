# Macro Cycle, Day-off & Cooldown Recovery Architecture (Quy tắc vận hành vĩ mô & chu kỳ nghỉ)

## 1. Zero-Sum Internal Graph & Math thời gian
- **Bản chất toán học follow chéo nội bộ:**
  - Tổng số lượt follow nhận về = Tổng số lượt follow gửi đi.
  - Tốc độ phát/nhận của mỗi nick bị chặn cứng ở mức ~250 follow/tháng (với nhịp an toàn 10-15 follow/phiên, 2 phiên/ngày chạy).
  - Để 1 nick đạt 1.000 follower từ nguồn chéo nội bộ: BẮT BUỘC mất tối thiểu **4 tháng chẵn** (1000 / 250 = 4).
  - Cộng thêm giai đoạn nuôi mồi ban đầu ($\ge 10$ video) mất ~30 đến 40 ngày $\rightarrow$ Tổng vòng đời 1 lứa đạt chuẩn là **gần 5 tháng**.
  - CẤM vẽ hươu vẽ vượn về view đề xuất khi tính toán sản lượng cày chéo nội bộ.
- **Rủi ro Graph Reciprocity:**
  - Follower thật chỉ nhận lại 10-20% follow-back. Farm nhận lại 95-100% tạo thành đồ thị vòng kín (Closed Ring Network).
  - Bắt buộc duy trì tỷ lệ 5% organic follow trên Feed Đề xuất (For You) và xen kẽ tài khoản bên ngoài để làm loãng đồ thị.

## 2. Chu kỳ vận hành vĩ mô 3 ngày (4 Slot - 4 Slot - 1 Ngày Nghỉ Trắng)
- **Vấn đề của lịch chạy cũ:**
  - Lịch cũ chạy xoay tua `[Nhóm A] -> [Nhóm B] -> [Nhóm A] -> [Nhóm B]` bào liên tục 365 ngày/năm. Không có lấy một ngày xả hơi, khiến toàn farm phát sinh request follow liên tục và từng nick chỉ được nghỉ ~24h (chưa đủ để xóa cờ nghi vấn TikTok).
- **Chu kỳ chuẩn 3 ngày:**
  - **Ngày 1:** Slot 1, 3, 5, 7 (hoặc 1, 2, 3, 4) chạy 2 phiên follow (10-15 follow/phiên) + kẹp 1 phiên đăng video.
  - **Ngày 2:** Slot 2, 4, 6, 8 (hoặc 5, 6, 7, 8) chạy 2 phiên follow + kẹp 1 phiên đăng video.
  - **Ngày 3 (NGÀY NGHỈ TRẮNG TOÀN FARM):** TOÀN BỘ 8 SLOT NGHỈ FOLLOW 100%. 100% máy chỉ chạy script lướt feed nuôi giải trí (0 follow chéo). Đây là "nút reset" tự nhiên để xả điểm nghi vấn (anomaly score) và xóa cờ phạt nhả.
  - **Ngày 4:** Lặp lại Ngày 1. Từng slot được nghỉ trọn vẹn 48h giữa 2 lần đi follow.
- **Tỷ lệ phiên:**
  - Giữ vững 2 phiên/ngày. Không nâng lên 3 phiên toàn farm vì gây quá nhiệt thiết bị S7 và tạo hành vi máy móc lặp lại quá dày.

## 3. Kiến trúc State Machine & Auto-Sync Expiry (Đã nghiệm thu Sol 9.3/10)
- **Vá lỗi State Inconsistency (Zombie State):**
  - CẤM đọc raw JSON ở tầng caller (`feed_swipe_smoke.py`) mà không dọn dẹp state khi hết hạn.
  - Khi `now_utc >= cooldown_until_at`: Hàm kiểm tra bắt buộc tự động dọn sạch cờ `follow_failed = False`, reset `fail_streak = 0`, xóa các trường timestamp `cooldown_until_*` và ghi đè an toàn qua file tạm (`.json.tmp` -> `os.replace` atomic). Tránh tình trạng JSON giữ cờ lỗi khiến caller khác tưởng nhầm tài khoản bị phạt vĩnh viễn.
- **Chuẩn hóa 100% mốc thời gian sang UTC:**
  - Dùng `datetime.now(timezone.utc)` và `until_dt.astimezone(timezone.utc)` để so sánh. Cấm dùng `datetime.now().strftime("%Y-%m-%d")` local gây lệch ngày giữa máy Windows và server.
- **Cách ly cấp Slot/Row (Row Isolation):**
  - CẤM fallback sang `follow_state_{machine}.json` chung của máy.
  - BẮT BUỘC match chính xác theo cặp `(machine, row)`. Nếu 1 nick bị phạt nhả thì 7 nick còn lại trên máy vẫn hoạt động độc lập bình thường.
