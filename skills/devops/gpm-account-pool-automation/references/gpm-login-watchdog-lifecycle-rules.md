# GPM Login Watchdog & Profile Lifecycle Rules

## 1. Tự Động Quản Lý Vòng Đời Profile GPM (Self-Contained Lifecycle)
Mỗi khi script login watchdog (`post_evening_gpm_login_watchdog.py`) chạy, nó **bắt buộc phải tự kiểm tra** danh sách Gmail LIVE/DIE trong Master Excel và đồng bộ Profile GPM ngay đầu chu kỳ:
- **Dọn dẹp DIE**: Profile GPM nào gắn với email có status `DIE / BAN / SUSPENDED` phải lập tức xóa bỏ khỏi GPM qua API mode 2 hoặc direct DB.
- **Tạo mới LIVE**: Email nào `LIVE` chưa có profile GPM phải tự động sinh profile mới kèm proxy 4G tương ứng.
- **CẤM đòi hỏi thiết bị S7 online ADB khi tạo profile**: Tạo profile GPM chỉ cần thông tin `email + LIVE + proxy port`. Tuyệt đối không được ràng buộc điều kiện thiết bị S7 phải đang cắm ADB online, tránh block toàn bộ việc tạo profile khi điện thoại đang sleep hoặc offline.

## 2. Anti-Pattern: Chặn Oan Proxy Do Tăng Counter Ảo (Ghost Proxy Counter Bug)
- **Cơ chế lỗi**: Đếm số lần sử dụng proxy (`proxy_count[port] += 1`) ngay trong vòng lặp lọc ứng viên (`get_candidates()`) trước khi thực thi login. Khi ghi state file, watchdog sau đó đọc lại và hiểu nhầm tất cả các port đều đã chạm ngưỡng `2/port/ngày`, làm đóng băng toàn bộ pool tài khoản suốt nhiều ngày dù không hề chạy login thực tế.
- **Quy tắc bất biến**: `proxy_count` **CHỈ ĐƯỢC PHÉP TĂNG** khi tác vụ `run_login()` thực sự được kích hoạt cho candidate đó. Tuyệt đối không tăng counter trong giai đoạn candidate filtering / candidate preview.
