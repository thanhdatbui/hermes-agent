# Bẫy Số Liệu Lũy Kế Cả Ngày Gây Báo Cáo Ảo Trùng Lặp Giữa Các Ca (GPM Login Shifts)

## 1. Hiện Tượng & Triệu Chứng
- Watchdog chạy theo ca (Sáng - Chiều - Tối) như `post_evening_gpm_login_watchdog.py` báo cáo:
  `[LOGIN GPM TỐI - TỔNG KẾT]`
  `• Kết quả ca: ✓ 0 | ✗ 3 | max_proxy 0/cổng | Hoàn tất ca tối`
- Người dùng hoang mang vì tưởng rằng 3 tài khoản vừa được xử lý hoặc đưa vào cooldown hạ nhiệt hồi sáng lại tiếp tục bị lỗi trong ca tối.
- Thực tế hiện trường: Ca tối hoàn toàn không chạy tài khoản nào (`max_proxy 0/cổng`, `candidates` rỗng hoặc các máy đều bận lịch nuôi TikTok Ca 3 / Avatar).

## 2. Căn Nguyên Kỹ Thuật (Root Cause)
1. **Thiết kế State Tích lũy (Daily Cumulative State) vs Nhãn Báo cáo Ca (Shift Summary):**
   - Script đọc `STATE_FILE` (`post_evening_gpm_login_state.json`) với biến `total_fail = state.get("total_fail", 0)` và `total_success = state.get("total_success", 0)`.
   - Các biến này mang tính lũy kế của cả ngày (daily total).
2. **Kích hoạt hàm in tổng kết ca khi không có lượt chạy mới:**
   - Khi ca tối kết thúc (hết khung giờ `is_late` hoặc không có `ready` candidate), script gọi:
     `print(_format_summary_report(total_success, total_fail, shift_label, shift_desc, ...))`
   - Lúc này, `total_fail` mang giá trị `3` từ ca sáng (các acc `phanthithanhhai`, `luunhu`, `cathoa`), nhưng lại được gán nhãn `[LOGIN GPM TỐI - TỔNG KẾT]`.
   - Kết quả: Báo cáo gây hiểu nhầm nghiêm trọng là trong ca tối đã có 3 tài khoản bị fail.

## 3. Kỷ Luật & Quy Tắc Vận Hành
- **Phân tách rạch ròi Số Liệu Ca vs Số Liệu Ngày:**
  - Trong báo cáo từng ca, chỉ được hiển thị số acc thành công / thất bại phát sinh **trong chính ca đó** (`shift_success`, `shift_fail`).
  - Nếu muốn báo cáo lũy kế cả ngày, phải ghi rõ nhãn: `Lũy kế ngày: ✓ X | ✗ Y`.
- **Cơ chế đối soát hiện trường (Fidelity Check):**
  - Khi thấy báo cáo `✓ 0 | ✗ N` với `max_proxy 0/cổng`, Coordinator BẮT BUỘC kiểm tra `STATE_FILE` và danh sách `processed`:
    - Nếu `processed` và `proxy_count` không tăng thêm so với ca trước -> Khẳng định ngay đây là số liệu lũy kế cũ, không phải lỗi phát sinh mới.
    - Tuyệt đối không hoảng loạn dispatch sửa code hay sửa DB khi chưa xác minh timestamp thực thi của worker.
