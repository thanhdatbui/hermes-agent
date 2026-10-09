# Audit Pitfalls: Timezone UTC vs GMT+7 & Parity Lane Audit Protocol

## 1. Múi giờ UTC trong State JSON vs Giờ Farm (Asia/Ho_Chi_Minh GMT+7)
- **Hiện tượng & Bẫy Audit:**
  - File trạng thái `follow_state_*.json` lưu timestamp dạng ISO 8601 UTC: `2026-10-02T23:25:00+00:00`.
  - Giờ farm thực tế chạy ca sáng lúc **06:25 sáng ngày 03/10 (Giờ VN - GMT+7)**.
  - **LỖI NGHIÊM TRỌNG:** Nếu dùng code python cắt chuỗi `ts[:10]` trực tiếp, nó sẽ đọc thành ngày `2026-10-02` (ngày chẵn), dẫn đến báo cáo sai lệch rằng "Row 1 (hàng lẻ) chạy vào ngày chẵn".
- **Quy tắc bắt buộc khi audit state farm:**
  - Mọi timestamp từ JSON state (`followed`, `failed`, `last_failed_at`) BẮT BUỘC phải parse qua `datetime.fromisoformat()` và chuyển về `ZoneInfo("Asia/Ho_Chi_Minh")` trước khi group theo ngày:
  ```python
  from datetime import datetime
  from zoneinfo import ZoneInfo
  HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
  dt_local = datetime.fromisoformat(ts).astimezone(HCMC)
  local_date = dt_local.strftime("%Y-%m-%d")
  ```

## 2. Quy tắc luân phiên Parity Lane (Chẵn / Lẻ)
- **Ngày lẻ (01, 03, 05, 07...):** Chỉ chạy các Row lẻ (`Row 1, 3, 5, 7`). Tuyệt đối không có Row chẵn chạy follow.
- **Ngày chẵn (02, 04, 06, 08...):** Chỉ chạy các Row chẵn (`Row 2, 4, 6, 8`). Tuyệt đối không có Row lẻ chạy follow.
- Khi user đối soát lịch chạy, phải kiểm tra theo ngày địa phương HCMC để không vi phạm quy tắc Parity Lane.

## 3. Phân biệt Số Nick Hoạt Động Lũy Kế vs Số Nick Chạy Mỗi Ngày
- **Bẫy báo cáo:** Tổng hợp 61 nick có follow trong 7 ngày không có nghĩa là "mỗi ngày có 60 nick đi follow".
- Thực tế do luân phiên chẵn/lẻ và cooldown:
  - Mỗi ngày lẻ: Chỉ có ~6-8 nick Row 1 đi follow.
  - Mỗi ngày chẵn: Chỉ có ~3-4 nick Row 2 đi follow.
- Khi báo cáo, BẮT BUỘC phân tách rõ số liệu theo từng ngày đơn lẻ, không dùng số lũy kế nhiều ngày để gây hiểu lầm.

## 4. Di chứng của hàm Verify False-Positive (Lịch sử Tháng 9/2026)
- **Nguyên nhân:** Trước commit `c12242d` (02/10), hàm verify đọc nhầm selector số counter header (`id/sdn`, `id/t1i`...) là nút "Đã follow", khiến bot ngỡ là follow thành công và ép nick tiếp tục spam 10-20 follow trong 1 phiên dù server TikTok đã silent-drop.
- **Hậu quả:** Hơn 300 nick bị server TikTok đưa vào danh sách đen (Shadowban/Action block nặng).
- **Hiện tượng sau ra tù:**
  - **93.3% (321 nick):** Vừa ra tù bấm phát đầu tiên bị nhả liền (0 follow).
  - **6.7% (23 nick):** Follow được 1-15 cái ở phiên warm-up rồi bị nhả lại.
  - **0% phục hồi bền vững:** Cooldown 3-5 ngày là chưa đủ để TikTok gỡ cờ đen với các nick từng bị spam. Cần cooldown 7-15 ngày + lướt feed tự nhiên.

## 5. Đặc điểm nhóm nick miễn nhiễm vi phạm (21 nick trâu bò)
- Các nick duy trì `fail_streak = 0` và cày >200-300 following thật trên app TikTok đều thỏa mãn:
  1. Tuổi đời > 215 ngày (> 7 tháng).
  2. Số video đã đăng >= 24 - 29 video.
  3. Có tương tác ngược (Inbound followers > 60 - 280 followers, có view/tim video tự nhiên).
- Đây là ngưỡng Trust an toàn tuyệt đối của TikTok. Các acc dưới 10 video hoặc mới nuôi < 30 ngày rất dễ bị cắm cờ nếu follow quá 3-5 người/ngày.
