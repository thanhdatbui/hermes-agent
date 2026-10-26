# Quy Chuẩn Báo Cáo Nuôi Gmail GPM Chu Kỳ 12 Giờ & Fallback Tính Trần An Toàn

## 1. Bối Cảnh & Vấn Đề
- **Lệch chu kỳ báo cáo:** Báo cáo nuôi Gmail GPM trước đây cố định cửa sổ 6 giờ (`WINDOW_HOURS = 6`), trong khi lịch cronjob thực tế được cấu hình chu kỳ 12 giờ một lần (`0 */12 * * *`).
- **Lỗi đếm trần nuôi an toàn:** Script báo cáo đọc biến `_daily_stats` từ file state (`gpm_gmail_nurture_state.json`). Khi biến này rỗng hoặc không đồng bộ giữa các tiến trình runner, báo cáo hiển thị sai lệch `0/30 profile` dù thực tế trong ngày đã nuôi đủ `30/30 profile`.

## 2. Giải Pháp Triển Khai Chuẩn
1. **Mở rộng cửa sổ thống kê linh hoạt:**
   - Đặt biến môi trường `GPM_NURTURE_WINDOW_HOURS` với mặc định là 12 thay vì cố định 6.
   - Hàm `build_report_lines(state, total_g10, group10_emails, now_ts, window_hours=None)` hỗ trợ truyền tường minh hoặc tự động lấy theo cấu hình môi trường.
2. **Fallback đếm trực tiếp từ timestamp `last_nurtured`:**
   - Xây dựng hàm `count_nurtured_today(state, now_ts)` duyệt qua toàn bộ dictionary profile (bỏ qua metadata `_`), so sánh ngày của `last_nurtured` với ngày hiện tại (`datetime.fromtimestamp(last_n).date() == today`).
   - Chỉ dùng `_daily_stats` khi có dữ liệu ngày khớp và `count > 0`, ngược lại luôn fallback về hàm tính trực tiếp để phản ánh 100% số lượng profile đã nuôi thực tế.
3. **Phát hiện và báo cáo đích danh tài khoản văng session:**
   - Quét mảng profile có `status == 'NEEDS_LOGIN'` trong cửa sổ `window_hours` để cảnh báo kịp thời danh sách email cần đăng nhập lại.
