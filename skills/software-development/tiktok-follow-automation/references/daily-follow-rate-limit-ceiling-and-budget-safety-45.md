# Daily Follow Rate-Limit Ceiling (Bức Tường 50 Follow) & Ngưỡng Budget An Toàn 40–45

## 1. Bản chất Bức Tường 50 Follow/Ngày của TikTok
- TikTok áp dụng cơ chế Rolling Window Rate-Limit cứng quanh mốc **50 follow/ngày** đối với các tài khoản nuôi trên farm Android.
- Bằng chứng thực nghiệm (ngày 2026-09-06 trên M26, M46, M72):
  + Cả 3 máy đều chạy 3 phiên trong ca: Phiên 1 đạt 18–20 (`OK`), Phiên 2 đạt 18–20 (`OK`). Tổng 2 phiên tích lũy 36–40 lượt hoàn toàn trơn tru.
  + Sang Phiên 3: Máy tiếp tục follow được 10–13 lượt thì chạm **đúng mốc 49–50 follow**.
  + Ngay tại lượt thứ 50: TikTok lập tức chặn action (`TikTok không nhận follow sau reload — dừng session`).
  + Hậu quả: Dù là các nick khỏe nhất farm, chúng đều bị gán `status: FOLLOW_FAILED`, `fail_streak` tăng lên 1 và dính daily cooldown.

## 2. Đối Soát Chu Kỳ T ➔ T+1 (Sau 48h)
- **Hoàn toàn KHÔNG có hiện tượng phạt nhả Turn 0 do follow nhiều ở chu kỳ trước:**
  + Dữ liệu đối soát trên M45, M51, M58, M62, M20, M23, M24... cho thấy các nick đạt 45–50 follow ở chu kỳ T không hề bị phạt nhả ở Turn 0 tại chu kỳ T+1. 
  + Sau 48h nghỉ ngơi theo lịch Chẵn/Lẻ, rolling rate-limit của TikTok đã được reset mới hoàn toàn.
  + Các nick bị nhả Turn 0 thực chất là các nick vốn có trust score yếu từ trước, proxy bẩn hoặc dính anchor lỗi.

## 3. So Sánh Ngưỡng Ngân Sách: 50–60 vs 40–45
- **Ngưỡng 50–60 (Mặc định cũ: 15–20/phiên x 3 phiên = trần 60):**
  + Ép các nick khỏe phải "húc đầu vào bức tường rate-limit 50" của TikTok ở Phiên 3.
  + Bị TikTok cưỡng chế dừng lại bằng action-block (`FOLLOW_FAILED`), làm tăng `fail_streak` và bào mòn trust score nếu lặp lại liên tục qua nhiều ngày.
- **Ngưỡng 40–45 (Khuyến nghị an toàn: 12–15/phiên x 3 phiên = 36–45/ngày):**
  + Giúp nick dừng chủ động trước khi chạm bức tường 50.
  + Toàn bộ 3 phiên đều kết thúc sạch sẽ (`status: OK`), giữ `fail_streak = 0`.
  + Sản lượng chỉ giảm ~10–15% nhưng bảo vệ nick an toàn tuyệt đối, loại bỏ hoàn toàn các ca fail giả do chạm trần trong nhóm nick khỏe.

## 4. Tham Số Cấu Hình Tối Ưu trong `config.py` (tiktok-follow)
- `budget_per_day`: `45` (thay vì 60)
- `budget_per_session_min`: `12` (thay vì 15)
- `budget_per_session_max`: `15` (thay vì 20)
