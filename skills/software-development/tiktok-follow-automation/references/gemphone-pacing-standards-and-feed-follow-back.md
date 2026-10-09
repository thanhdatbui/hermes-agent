# Tiêu chuẩn Nhịp độ GemPhone & Phân nhánh Nuôi Acc TikTok (Case 165 / 166)

Tài liệu đúc kết từ quá trình mổ xẻ trực tiếp 3 file workflow GemPhoneFarm gốc của ông Khoa (`TIKTOK-Nuoi-Tai-Khoan-Goc`, `TIKTOK-FLOW-TÌM-KIẾM`, `TIKTIK-ĐĂNG-VIDEO`) và dữ liệu thực tế 170/176 nick farm bị phạt nhả follow (14/09/2026).

---

## 1. Dữ liệu Thực tế: Đăng Video đều có tự gỡ cờ Nhả Follow không?
- **Khảo sát thực tế**: 170 / 176 tài khoản đang dính án phạt nhả follow (`fail_streak >= 1`) đều đã đăng trên 5 video (trung bình 10.9 video/nick, nhiều nick đăng 20-23 video).
- **Kết luận**: Lý thuyết *"chỉ cần đăng video đều là tự follow được"* hoặc *"ngâm 7 ngày tự hết"* là **không chính xác**. Nếu môi trường thiết bị (8 nick/máy, cùng proxy) và nhịp follow vẫn quá vội vàng cơ học, hệ thống Risk Control của TikTok sẽ silent rollback ngay khi hết hạn cooldown.

---

## 2. Tiêu chuẩn Nhịp độ (Pacing Standards) học từ GemPhone của ông Khoa

### A. Thời gian ngâm Profile trước khi bấm Follow (Dwell Time)
- **Node GemPhone**: Delay `5812, 12549 ms`.
- **Chuẩn hóa script Python**: Khi mở Profile mục tiêu, BẮT BUỘC ngâm từ **6.0s – 12.0s ngẫu nhiên** (`time.sleep(random.uniform(6.0, 12.0))`) trước khi tap nút Follow.
- **Mục đích**: Người thật phải mất vài giây đọc thông tin/xem bài ghim, bot rẻ tiền tap ngay trong 1-2s sau khi activity mở.

### B. Thời gian chờ sau khi Tap Follow
- **Node GemPhone**: Delay `1814, 5654 ms`.
- **Chuẩn hóa script Python**: Chờ từ **2.5s – 5.0s ngẫu nhiên** để server đối soát và UI cập nhật nút.

### C. Khoảng cách giữa 2 lần Follow liên tiếp
- **Node GemPhone (`rf10473`)**: Delay `5142, 29521 ms`.
- **Chuẩn hóa script Python**: Kéo giãn khoảng cách giữa các lần follow thành **8.0s – 25.0s ngẫu nhiên** (cả Mode 1 Search Follow và Mode 2 Following list) thay vì nhịp cũ 1s – 5s.

---

## 3. Phân nhánh Thẻ Đề xuất Feed (`follow_back_suggestion`) - Case 165
- **Vị trí**: `feed_swipe_smoke.py` (`_gem_blind_action`).
- **Logic chuẩn**:
  - `is_account_in_follow_cooldown(ctx) == True` (Nick đang trong án phạt): Tìm và tap nút **"Không quan tâm"** để đóng thẻ, tuyệt đối không tap follow để tránh gia hạn án phạt.
  - `is_account_in_follow_cooldown(ctx) == False` (Nick sạch): Tap thẳng vào nút **"Follow lại"** / **"Theo dõi lại"** (tọa độ detector) để tăng tương tác chéo tự nhiên.

---

## 4. Ngẫu nhiên hóa Tỷ lệ Thả tim Feed (GemPhone Style) - Case 166
- **Vị trí**: `feed_swipe_smoke.py` (`_feed_like_rates`).
- **Nguyên lý Anti-Fraud**: TikTok nhận diện bot qua sự đồng điệu hành vi bất thường (Behavior Fingerprint Similarity). Tránh set tỷ lệ like cố định cứng.
- **Phân bổ theo phiên**:
  - Tab `following`: random dải [30%, 60%] mỗi phiên.
  - Tab `friends`: random dải [50%, 80%] mỗi phiên.
  - Tab `for_you`: giữ dải tự nhiên 8%.
  - Luôn ưu tiên cấu hình ghi đè tường minh (`ctx.config.get("_like_rate")`) nếu có.

---

## 5. Hành vi "Lưu" (Bookmark/Favorite) Video trên Feed
- Trọng số uy tín (Trust Weight) của hành vi "Lưu bài viết" cao gấp 3-5 lần một lượt Like.
- **Quy tắc phối hợp tự nhiên**: Chỉ kích hoạt sau khi đã thả tim thành công (video hay mới like, like rồi mới có xác suất 15-30% bấm Lưu).
