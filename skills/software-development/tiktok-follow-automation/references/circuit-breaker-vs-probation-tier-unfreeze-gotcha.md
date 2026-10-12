# Phân Biệt Giữa IP Circuit Breaker Tripped vs Nick Bị Nhả Follow (Account-Tier Cooldown)

## 1. Bản Chất Sự Cố
- **`ip_circuit_breaker` KHÔNG phản ánh toàn bộ các ca dính nhả (`FOLLOW_FAILED`):**
  - Trong logic lõi của `follow_runner/core/follow_state.py` (hàm `set_follow_failed`):
    - **CHỈ KHI nick cấp khỏe / đã tốt nghiệp (`was_graduated is True`) bị nhả:** Cầu dao IP mới được kích hoạt (`trip_ip_breaker(machine)`), khóa proxy tương ứng 48h và ghi vào bảng `ip_circuit_breaker`.
    - **KHI nick non / thử việc / chưa tốt nghiệp (`was_graduated is False`, ví dụ Row 4):** Hệ thống chỉ phạt cooldown tài khoản (`cooldown_until_date`), **KHÔNG HỀ TRIP IP CIRCUIT BREAKER**.
- **CẠM BẪY NGHIÊM TRỌNG:**
  - Nếu Coordinator chỉ kiểm tra bảng `ip_circuit_breaker` thấy `0` proxy bị ngắt mới mà vội vã kết luận *"hôm nay sạch sẽ, không có máy nào dính nhả"* là **SAI HOÀN TOÀN** và bị coi là báo cáo láo/ẩu.
  - Thực tế có thể có hàng chục nick non (Row 4) bị nhả follow hàng loạt (ví dụ ngày 12/10/2026 có tới 48 nick non dính nhả), nhưng proxy vẫn mở khiến các nick non tiếp theo vào ca bị nhả dắt dây.

## 2. Quy Tắc Đối Soát Số Liệu Follow Trong Ngày
1. **Tổng follow thực tế:**
   - Bảng `daily_account_actions` có thể ghi nhận tích lũy hoặc trùng lặp giữa các phiên (ví dụ 40 lượt).
   - Con số chính xác thực tế phải đối soát từ các file `runs/state/follow_state_*_row_*.json` xem các timestamp `followed` trong ngày (ví dụ 35-36 lượt thực).
2. **Kiểm tra tỷ lệ nhả follow:**
   - Không được chỉ nhìn bảng `ip_circuit_breaker`.
   - BẮT BUỘC kiểm tra các file state xem có bao nhiêu tài khoản có `last_failed_date == today` hoặc `reason` chứa `bị nhả sau vuốt / FOLLOW_FAILED`.
   - Báo cáo rõ: bao nhiêu lượt follow thành công, bao nhiêu nick tốt nghiệp bị nhả (có ngắt IP), và bao nhiêu nick non bị nhả (chỉ phạt nick, không ngắt IP).
