# Watchdog Shift Label Dynamic Derivation & False Alert Prevention (25/09/2026)

## 1. Hiện Tượng: Báo Cáo 11h26 Ghi "Ca Tối"
- **Sự cố:** Báo cáo tổng kết upload avatar phát lúc 11:26:56 sáng nhưng tiêu đề và trạng thái lại ghi:
  - `• Trạng thái: Hết khung giờ ca tối (sau 23:30)`
  - `• Kết quả ca tối nay: Thành công +2 acc mới | Lỗi 11 máy`
  - `📋 CHI TIẾT CỤM LỖI CA TỐI NAY:`
- **Root Cause:** Khi mở rộng thêm khung giờ chạy cuốn chiếu cho watchdog (ví dụ thêm ca sáng 08:30–11:15), logic điều kiện `is_post_evening_window` / `is_after_evening_window` được mở đúng, nhưng hàm dựng giao diện báo cáo (`format_report_html`) vẫn giữ nguyên các chuỗi text tĩnh bị hardcode ("ca tối", "sau 23:30").

## 2. Kỷ Luật Vá Hàm Render Báo Cáo Định Kỳ
1. **Derive Ca Chạy Theo `now_dt` Thực Tế:**
   - Tuyệt đối CẤM hardcode tên ca trong thân hàm format report.
   - Bắt buộc kiểm tra giờ thực tế:
     - `06:00 <= hour < 14:00` $\rightarrow$ `ca_name = "ca sáng nay"`, `shift_label = "ca sáng"`, `cutoff_desc = "sau 11:15"`.
     - Ngược lại $\rightarrow$ `ca_name = "ca tối nay"`, `shift_label = "ca tối"`, `cutoff_desc = "sau 23:30"`.
2. **Đồng Bộ Cả Báo Cáo Cụm & Báo Cáo Toàn Farm:**
   - Phải cập nhật đồng thời ở nhánh đơn cụm (`stats_by_tik`) và nhánh toàn farm (`stats_by_cluster`), tránh sửa sót 1 trong 2 nhánh.
3. **Regression Test Bắt Buộc:**
   - Khi sửa logic nhãn ca, bắt buộc thêm test case với `now_dt` rơi vào đúng các mốc thời gian đặc thù (như 11:26:56 cho ca sáng và 23:45 cho ca tối) để assert text sinh ra không bị lẫn lộn giữa các ca.
