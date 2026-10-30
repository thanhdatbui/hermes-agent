# Triage Auto-Login Recovery Timeout Khi Kẹt Màn "Chào Mừng Bạn Trở Lại" (One-Tap Login) Do Trống Thông Tin Sổ Cái (30/10/2026)

## 1. Hiện Tượng & Câu Hỏi Của Operator
- **Hiện tượng:** Máy dừng tại màn hình One-Tap Login *"Chào mừng bạn trở lại"* (danh sách 1-3 nick cũ còn lưu phiên, nút `+ Thêm tài khoản khác`).
- **Phản ứng của Operator:** *"Là sao tới đây rồi đéo tự đăng nhập bằng script tiktok login đi mà kẹt ở đây?"*
- **Ý nghĩ sai lầm dễ mắc:** Tưởng rằng runner bỏ cuộc ngay khi thấy màn hình login và không chịu kích hoạt script đăng nhập tự động.

## 2. Quy Trình Truy Vết Hiện Trường O(1) Qua `log.jsonl`
Để trả lời chính xác, bắt buộc kiểm tra các step trong `log.jsonl` của máy:
1. **Kiểm tra xem auto-login recovery đã chạy chưa:**
   - Tìm step `feed-session-smoke/auto_login_recovery` với action `start_fast_login`:
     ```json
     {"step": "feed-session-smoke/auto_login_recovery", "action": "start_fast_login", "command": ["...python.exe", "...tiktok_login_v1.py", "<machine>", "--email", "<expected_username>", "--ss", "--allow-parent-lock"]}
     ```
   - Kiểm tra action tiếp theo `fast_login_exception_fallback_reconcile`:
     Nếu văng `timed out after 420.0 seconds` -> Script fast login đã chạy nhưng bị treo chờ.
   - Kiểm tra action `start_reconcile` và `finish_reconcile`:
     Nếu văng `timed out after 600.0 seconds` -> Script reconcile fallback cũng chạy và tiếp tục treo chờ đến trần timeout.
2. **Tổng thời gian treo cứu hộ:** 420s + 600s = **17 phút**. Runner đã kiên trì thực hiện đầy đủ 2 tầng cứu hộ trước khi buộc phải fail-closed teardown về Launcher để tránh giữ thiết bị vĩnh viễn.

## 3. Căn Nguyên Gốc: Tài Khoản Trống Thông Tin Trong Sổ Cái (`Email: None`, `Pass: None`)
- **Cơ chế:**
  - Màn hình *"Chào mừng bạn trở lại"* chỉ cho phép tap 1 chạm vào các nick đang hiển thị trên UI.
  - Khi ca chạy phân bổ vào một Row (ví dụ Row 4) mà nick mục tiêu (`expected_username`) **chưa từng được nạp vào máy**, script bắt buộc phải bấm `+ Thêm tài khoản khác` để điền Email/Pass hoặc lấy mã OTP từ hộp thư.
  - Khi kiểm tra workbook (`taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx`):
    - `Username: <expected_username>`
    - `Email: None` (hoặc rỗng)
    - `Pass: None` (hoặc rỗng)
  - Vì không có Email và không có Password, script login không thể điền form đăng nhập, cũng không có hộp thư Hotmail để nhận mã OTP, dẫn tới việc tiến trình bị block chờ I/O hoặc treo detector đến khi cạn timeout 420s và 600s.

## 4. Kỷ Luật Phản Hồi Operator
1. **Khẳng định ngay:** Hệ thống ĐÃ tự động chạy script login (nêu rõ 2 tầng `tiktok_login_v1.py` và `reconcile_tiktok_accounts.py`).
2. **Nêu bằng chứng thời gian:** Đã cố gắng cứu hộ suốt 17 phút (420s + 600s) nhưng cả 2 script đều bị timeout.
3. **Chỉ rõ căn nguyên dữ liệu:** Trích xuất dòng Excel tương ứng chứng minh tài khoản `Email: None`, `Pass: None`.
4. **Hành động khắc phục:** Bổ sung thông tin Hotmail/Pass vào sổ cái Admin thì các ca chạy sau mới có thể tự động login bổ sung nick vào máy.
