# Cross-Session Reconcile Audit & Dashboard Cache Verification

## 1. Bối Cảnh & Vấn Đề
Khi nhận phản ánh hoặc hình ảnh Sổ Bệnh Án / Dashboard thể hiện tài khoản bị kẹt phạt (ví dụ: Streak 4+, Cooldown dài hạn) hoặc chu kỳ 4 ngày không cập nhật:
- **Nguy cơ phản xạ sai:** Coordinator nhìn ảnh lập tức kết luận database/state trên máy bị sai và chuẩn bị script sửa đổi hàng loạt file state (`runs/state/follow_state_*.json`) trong khi một session khác vừa xử lý xong.
- **Lệch pha giữa UI và Disk State:** Giao diện có thể hiển thị dữ liệu cũ do trình duyệt chưa tải lại (cache / F5) hoặc do frontend/backend hardcode chuỗi ngày tĩnh, trong khi file `.json` trên đĩa đã được xả án sạch sẽ.

## 2. Quy Tắc Đối Soát Ground-Truth Trước Khi Can Thiệp State
Trước khi viết hoặc chạy bất kỳ script sửa đổi hàng loạt file state:
1. **Kiểm tra Lịch sử Session & Mtime gần nhất:**
   - Dùng `session_search` rà soát nhanh các session gần nhất trong ngày xem có session nào vừa chạy script xả án / reconcile tương ứng chưa.
   - Kiểm tra `mtime` của các file state mục tiêu (`runs/state/`) để xác nhận thời điểm ghi nhận gần nhất.
2. **Đối soát Disk State thật vs UI Screenshot:**
   - Đọc trực tiếp nội dung file `.json` của nick mục tiêu trên đĩa (`fail_streak`, `follow_failed`, `cooldown_until_date`).
   - Gọi trực tiếp hàm helper backend (như `get_account_follow_detail(machine, row)`) để xem API trả về dữ liệu gì.
   - Nếu disk state đã sạch mà UI vẫn hiển thị cũ: Bản chất là client cache hoặc hardcode template, TUYỆT ĐỐI CẤM chạy lại script sửa đĩa.
3. **Phân biệt Lỗi Dữ Liệu State vs Lỗi Sliding Window:**
   - Nếu nick đã được xả án trên đĩa nhưng bảng tổng hợp (như "So sánh Chu kỳ 4 ngày") vẫn hiện kỳ cũ: Lỗi nằm ở logic cửa sổ trượt (sliding window) bị hardcode date strings trong code hiển thị (`follow_health_helper.py`, `follow_detail_component.py`), không phải lỗi state của từng nick.
