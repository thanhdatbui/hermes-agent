# Sổ Bệnh Án Multi-Cycle Cohort Comparison & IP Circuit Breaker Invariant

## 1. Đối Soát Chu Kỳ 4 Ngày Trên Dashboard Sổ Bệnh Án (:1905)
Khi người vận hành (Operator) yêu cầu đánh giá, so sánh chất lượng follow toàn farm theo chu kỳ 4 ngày (Parity 96h):
- **Bắt buộc hiển thị tối thiểu 3–4 chu kỳ liên tiếp** (ví dụ: `19-20/10 Hiện tại`, `15-16/10 Kỳ trước`, `11-12/10 Kỳ cũ`, `07-08/10 Kỳ xưa`) thay vì chỉ so sánh với 1 kỳ trước.
- **Bóc tách 2 nhóm tài khoản**:
  1. *Tù nặng / Rookie non bị nhả ngay phát đầu (`fl == 0`)*: Đa số là nick non hoặc tài khoản đang bị TikTok siết tương tác / Action Block cá nhân. Tách riêng nhóm này để không làm nhiễu bức tranh vận hành.
  2. *Nick thực chiến (`eligible_accounts`, `fl >= 1`)*: Là các nick thực sự bấm follow thành công từ 1 lượt trở lên. Tỉ lệ chạy SẠCH 100% và Tỉ lệ Ăn nhả đuôi (chạm trần) BẮT BUỘC chỉ tính trên tập thực chiến này:
     $$\text{clean\_pct} = \frac{\text{clean\_accounts}}{\text{eligible\_accounts}} \times 100$$
     $$\text{drop\_pct} = \frac{\text{drop\_after\_fl}}{\text{eligible\_accounts}} \times 100$$
- **Bóc tách theo từng nhóm Cohort (Cohort Breakdown)**:
  Bắt buộc hiển thị bảng con hoặc mục mở rộng cho 3 nhóm:
  * 🟢 **Cựu binh (Veteran)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.
  * 🟡 **Trung cấp (Mid)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.
  * 🔴 **Tân binh (Rookie)**: Thực chiến | Sạch % | Nhả đuôi % | Follows.

## 2. Cạm Bẫy Tính Toán Drop Lịch Sử Sau Khi Giải Cứu Tài Khoản
- **Cạm bẫy**: Nếu tính `has_drop = is_in_cooldown and (drop_day in c_dates)`, khi chạy script giải cứu (`reconcile_unfair_streaks.py`) xóa cờ `is_in_cooldown` và `cooldown_until_date` của các nick bị giam oan, hệ thống sẽ tính nhầm là chu kỳ quá khứ có 0% nhả đuôi (sai lệch hoàn toàn với thực tế).
- **Chuẩn hóa**: Tính drop lịch sử phải độc lập với cờ cooldown hiện tại của tài khoản:
  ```python
  has_drop = (a.get("last_failed_date") in c_dates) or (a.get("drop_day") in c_dates)
  ```
  Đảm bảo sau khi giải cứu tài khoản, số liệu đối soát chu kỳ lịch sử trên Dashboard vẫn bảo toàn chính xác 100%.

## 3. Phân Định Rạch Ròi: Ăn Nhả Đuôi (Account Ceiling) vs Cháy Proxy (IP Circuit Breaker 48h)
- **Ăn nhả đuôi (`used > 0`)**:
  * Nick đã follow thành công 5–15 người liên tục chứng minh **100% IP proxy hoàn toàn sạch và thông suốt**.
  * Việc bị nhả ở lượt cuối là do **tài khoản chạm trần bảo vệ phiên (Account-level Rate Limit)** của riêng nick đó trên TikTok.
  * Hiện tượng này **CÔ LẬP 100%** trên chính tài khoản đó: các nick khác ở slot khác trên cùng máy hoặc máy partner cùng IP vẫn chạy mượt mà (thực tế ngày 19/10 M21 R1 bị nhả đuôi, M21 R3 vẫn nã 33 follow sạch; máy partner M59 vẫn chạy bình thường).
  * **Hành động**: Giữ nguyên `fail_streak`, chỉ cách ly nick đó 1 ngày xả cache, ghi nhớ `last_failed_ceiling`. **TUYỆT ĐỐI CẤM giật sập cầu dao IP proxy 48h**!
- **Cháy proxy / IP bẩn thật sự**:
  * Nick bị chặn ngay từ phát bấm đầu tiên (`fl == 0`) và các nick khác trên cùng proxy đều bị chặn đồng loạt.
  * Cầu dao IP Breaker (`trip_ip_breaker()`) CHỈ được kích hoạt trong trường hợp này.
- **Bài học lịch sử tê liệt máy Partner**:
  * Ngày 10/10, M18 follow mượt 12 lượt rồi ăn nhả đuôi ➔ Hệ thống cũ tự ngắt IP breaker 48h ➔ Máy partner M56 (nick cựu binh #3 toàn farm `@tuantuannguyen56`) bị treo giò 48h oan uổng, đứt chuỗi nuôi ấm.
  * Ngày 15/10, M17 chạy được 5 lượt rồi nhả ➔ Ngắt proxy 48h ➔ Cựu binh M55 (`anh.le0052`) bị mất ca chạy 2 ngày liên tiếp.
