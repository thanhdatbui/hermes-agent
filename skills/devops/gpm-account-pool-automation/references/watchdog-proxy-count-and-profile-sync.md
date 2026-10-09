# Quy tắc Đồng bộ GPM Profile & Chống Bug Proxy Count Ảo

## 1. Chống Bug Proxy Count Ảo trong Watchdog / Cron
- **Triệu chứng**: Toàn bộ các cổng proxy đều chạm trần (`MAX_LOGINS_PER_PROXY`, ví dụ 2 acc/port/ngày) và watchdog báo hoàn tất (`finished: true`), làm cả farm không chạy được suốt nhiều ngày dù thực tế mới xử lý vài tài khoản.
- **Nguyên nhân gốc rễ**: Tăng `proxy_count[port] += 1` ngay trong vòng lặp lọc candidates (`get_candidates()`). Khi candidate bị nghẽn (do máy chưa rảnh hoặc giới hạn batch worker), `proxy_count` vẫn bị ghi nhận vào state file bền vững, tích lũy khống qua từng lần cron tick.
- **Quy tắc bắt buộc**:
  1. `proxy_count` trong state của ngày hôm nay **CHỈ ĐƯỢC TĂNG** khi candidate thực sự được nạp vào worker để chạy (`run_login`).
  2. Trong hàm lọc candidate (`get_candidates`), chỉ dùng biến tạm thời (`planned_proxy_count`) trong phạm vi bộ lọc để tránh pick quá 2 tài khoản cùng port trong 1 đợt batch, không được lưu đè vào persistent state.
  3. Tuyệt đối không set `finished = True` khi còn tài khoản chưa xử lý chỉ vì máy tạm thời bận.

## 2. Quy tắc Đồng bộ GPM Profile (Tạo LIVE + Dọn DIE)
- **Tạo Profile LIVE**:
  - Tự động sinh profile GPM cho các Gmail có trạng thái `LIVE` trong `master_gmail_manager.xlsx` mà chưa có profile trong GPM SQLite DB.
  - Lấy thông tin proxy từ cột `Proxy` của master Excel hoặc file mapping `PROXYgandienthoai.xlsx`.
  - **CẤM đòi hỏi máy S7 phải online ADB**: Profile GPM chạy trên trình duyệt PC qua GPMClient / Local API v3. Việc kết nối máy S7 qua ADB chỉ cần thiết khi tới bước tương tác duyệt Google Prompt / trích xuất Security Code, không được chặn việc tạo profile GPM.
- **Dọn dẹp Profile DIE**:
  - Quét danh sách Gmail có trạng thái `DIE`, `BAN`, `SUSPENDED` từ master Excel.
  - Đối chiếu với profiles trong GPM SQLite DB và gọi API xóa (`GET /api/v3/profiles/delete/{id}?mode=2`) để giải phóng tài nguyên.
