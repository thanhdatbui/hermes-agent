# Bẫy Chạy Dồn P1-P2 (2-Hour Window Decay) & Cơ Chế Follow Động (Cohort Sweet Spot)

## 1. Hiện tượng & Bản chất bẫy P1-P2 (Cách nhau 2 tiếng)

### Hiện tượng thực tế
- Tại Phiên 1 (06:00): Các nick đang trong diện hồi phục (`probation_tier1`, `probation_tier2`) chạy thành công 100%, không bị nhả (đạt 2–8 follow sạch).
- Tại Phiên 2 (08:00 - cách P1 đúng 2 tiếng): Hầu hết các nick hồi phục (M4, M14, M21, M28, M41, M52, M57) bấm được đúng **1 nick**, đến nick thứ 2 là bị TikTok nhả nút đỏ/xám ngay lập tức (`FOLLOW_FAILED: TikTok không nhận follow (profile vẫn chưa follow)`).
- Riêng các nick nòng cốt có trust cao (M37, M36, M39, M20, M16, M2): Nuốt trọn cả P1 và P2 (M37 đạt 13 follow, M36 đạt 7 follow, M39 đạt 7 follow sạch 100%).

### Bản chất kỹ thuật
1. **Thuật toán Leaky Bucket / Hourly Decay của TikTok:**
   - TikTok kiểm soát hạn mức hành động theo block thời gian trượt (cửa sổ 1–2 giờ) và theo ngày.
   - Nick đang hồi phục có trần trust trong ngày thấp (5–8 lượt/ngày). Ở P1, nick đã cắn 4–7 lượt, vắt kiệt gần hết hạn mức.
   - P2 diễn ra chỉ sau 2 tiếng: Cửa sổ trượt chưa kịp hồi phục (chỉ nhả nhẹ đúng 1 slot quota cuối cùng).
2. **Bẫy Optimistic UI của TikTok & Phản xạ Path B Verify:**
   - Khi bot bấm lượt 1 ở P2: Nút nhận, Path B verify profile xác nhận server TikTok có nhận.
   - Khi bot bấm lượt 2 ở P2: Giao diện danh sách vẫn hiện "Đang follow" (do Optimistic UI của app giả lập), nhưng khi bot click vào trang Profile cá nhân của target để kiểm tra thật thì nút trên Profile đã bị server trả về màu đỏ (`not_followed`).
   - Bot kích hoạt fail-safe dừng session để bảo vệ nick.

---

## 2. Chiến lược điều phối: Không cào bằng cắt bỏ P2

### Cấm cào bằng
- Tuyệt đối KHÔNG cắt bỏ hoàn toàn Phiên 2 của toàn bộ dàn máy: Làm vậy sẽ bóp nghẹt sản lượng follow của dàn máy khỏe (như M37, M36, M39 vốn có thể cắn 13-15 follow/ngày an toàn).

### Phân tầng xử lý (Tiered P1-P2 Distribution)
1. **Máy nòng cốt / Đã tốt nghiệp (`healthy_full`):**
   - Chạy đủ 2 phiên P1 và P2 bình thường (mỗi phiên 6–10 lượt, tổng ngày 12–20 lượt).
2. **Máy đang hồi phục (`probation_tier1`, `probation_tier2`):**
   - **Cách 1 (Chia nhỏ hạn mức phiên):** Thay vì P1 cắn 4–8 lượt làm cạn quota ngày, chia nhỏ: P1 ăn 2–3 lượt, P2 ăn 2–3 lượt. Giữa 2 phiên có thời gian lướt feed đệm để xả tải.
   - **Cách 2 (Cầu dao tỷ lệ nhả toàn Row):** Nếu ở P1 tỷ lệ nhả của Row vượt quá 20%, hệ thống tự động khóa follow ở P2 của Row đó, chuyển hẳn sang lướt feed dưỡng sinh.

---

## 3. Kiến trúc Cohort Analytics & Sweet Spot Động (`follow_health_helper.py`)

### Module tính toán động sẵn có
- File: `D:/Taadaa/tools/follow_health_helper.py`
- Tự động phân tích lịch sử chạy toàn farm theo 4 nhóm cohort:
  - `newbie`: Tân binh mới khởi động (khuyến nghị 3-5 lượt/ca).
  - `recovery_t1`: Phục hồi nhanh sau cooldown (1 ngày sạch, khuyến nghị 5 lượt/ca).
  - `recovery_t2`: Hồi phục chuẩn (2 ngày sạch, khuyến nghị 8-9 lượt/ca).
  - `core`: Nòng cốt khỏe mạnh (an toàn 100%, khuyến nghị 14-16 lượt/ca).
  - `canary`: Đội dò trần (+10% quota).
- Bảng phân bổ `trust_thresholds`: Tính tỷ lệ an toàn (`safe_pct`) và tỷ lệ nhả (`drop_pct`) trên các dải quota (1–4, 5–9, 10–14, 15+).

### Kênh quan sát cho Operator (Web Dashboard Port 1905)
- Không bắt người dùng phải nhớ để chat hỏi số liệu:
- Dashboard chạy ngầm tại: `http://localhost:1905` (hoặc `http://192.168.110.123:1905`).
- Endpoint dữ liệu live: `http://localhost:1905/api/follow-health` và `http://localhost:1905/api/data`.
- Hiển thị ma trận 1.266 tài khoản, phân bổ cooldown streak, tỷ lệ nhả theo bucket và khuyến nghị Sweet Spot cập nhật theo ngày.
