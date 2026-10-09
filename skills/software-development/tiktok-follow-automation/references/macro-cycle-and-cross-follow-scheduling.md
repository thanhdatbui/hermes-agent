# Quy Chuẩn Lịch Điều Phối Macro & Follow Chéo Nội Bộ (Farm Lifecycle)

## 1. Định Luật Bảo Toàn Follow Chéo Nội Bộ (Zero-Sum Graph Law)
- **Bản chất toán học:** Dù farm có 30 máy hay 160 máy (1.280 nick), tổng số lượt follow phát ra bằng tổng số lượt follow nhận về trong mạng lưới khép kín.
- **Tốc độ thực tế của 1 nick đơn lẻ:**
  - 1 nick chỉ gửi đi an toàn khoảng 250 - 350 follow/tháng (10-15 follow/phiên, 2 phiên/ngày chạy).
  - Để 1 nick nhận đủ 1.000 follower từ các nick khác trong dàn, bắt buộc cần:
    $$\frac{1.000 \text{ follow cần nhận}}{250-350 \text{ follow/tháng}} \approx \mathbf{3 \text{ đến } 4 \text{ THÁNG}}.$$
  - **Lưu ý sống còn:** Số lượng máy nhiều chỉ giải quyết bài toán **quy mô mẻ (batch concurrency)** — tức là sau 3-4 tháng thu hoạch 1 mẻ hàng trăm/hàng nghìn nick cùng lúc. Không có cách nào "đốt cháy giai đoạn" cho 1 nick đơn lẻ nếu chỉ dùng follow chéo nội bộ.

## 2. Chu Kỳ Xoay Ca 3 Ngày (4 Slot - 4 Slot - 1 Ngày Nghỉ Trắng)
Thay vì cắm đầu chạy follow mỗi ngày khiến dàn máy bị tích tụ điểm nghi vấn (anomaly score):
- **Ngày 1:** Chạy Slot 1, 2, 3, 4 (2 phiên follow $\times$ 10–15 follow/phiên; kẹp 1 phiên up video).
- **Ngày 2:** Chạy Slot 5, 6, 7, 8 (Tương tự Ngày 1).
- **Ngày 3:** **NGÀY NGHỈ TRẮNG TOÀN FARM (White Day)** — 100% máy chỉ chạy script lướt feed/thả tim giải trí, **TUYỆT ĐỐI 0 FOLLOW**.
- **Ngày 4:** Lặp lại chu kỳ từ Ngày 1.

### Giá trị kỹ thuật của "Ngày nghỉ trắng" (White Day):
- Không phải vì TikTok tự động "reset limit", mà là để **phá vỡ tính đồng điệu (Low Entropy Pattern)** của bot.
- Giảm mật độ action trên toàn bộ hạ tầng (Proxy, IP, Subnet), tránh bị thuật toán cluster detection gom cả dàn vào danh sách đen.
- Giúp từng slot có đủ **48h hồi phục tự nhiên** giữa 2 đợt cày.

## 3. Giai Đoạn Nuôi Móng 10 Video (Foundation Gate)
- Acc mới tạo (0 - 30 ngày): CẤM vội vàng đi follow chéo.
- Bắt buộc ngâm nuôi, lướt feed tự nhiên và đăng đủ $\ge 10$ video (khung giờ vàng 9h, 16h, tối muộn).
- Sau khi acc đã có $\ge 10$ video và trust score vững chắc mới đưa vào chu kỳ follow 3 ngày.

## 4. Cơ Chế Tự Động Bật Lại Khi Hết Hạn Phạt Nhả (Auto-Unblock)
- Hệ thống đã tích hợp sẵn cơ chế kiểm tra `is_account_in_follow_cooldown()` dựa trên timestamp UTC `cooldown_until_at` và `cooldown_until_date`.
- **Khi mãn hạn cooldown:**
  1. `FollowState` tự động reset `follow_failed = False` và dọn sạch các trường timestamp hết hạn.
  2. `feed_swipe_smoke.py` tự động mở lại follow video ở tab Đề xuất (For You) theo tỷ lệ `_deep_follow_rate`.
  3. Popup gợi ý kết nối (`follow_back_suggestion`): Tự động chuyển từ hành vi né phạt (bấm "Không quan tâm") sang hành vi nhận kết nối (bấm "Follow lại").
