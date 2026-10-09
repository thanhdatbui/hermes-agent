# GPM Login Watchdog, Lifecycle Synchronization & Safe Operations

Tài liệu chuẩn hóa kiến trúc vận hành cho watchdog đăng nhập GPM ca tối (`post_evening_gpm_login_watchdog.py`), quản lý vòng đời profile GPM và quy tắc tra cứu an toàn trong repo `D:\Taadaa\GPM auto`.

---

## 1. Đồng Bộ Vòng Đời Profile GPM (Lifecycle Sync) Trước Khi Lọc Candidates

### Vấn đề thường gặp:
Watchdog `post_evening_gpm_login_watchdog.py` sử dụng hàm `get_all_gpm_emails()` để đọc danh sách profile đã có trong SQLite database của GPMLogin (`C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`).
- Nếu tài khoản trong Excel `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`) ở trạng thái `LIVE` nhưng chưa được tạo profile GPM, bộ lọc `if em_l not in gpm_emails: continue` sẽ bỏ qua toàn bộ, dẫn đến danh sách candidates bị rỗng hoặc thiếu hụt (`< 30`).
- Nếu tài khoản mang trạng thái `DIE`, `BAN`, hoặc `SUSPENDED` mà profile GPM vẫn còn tồn tại trong cơ sở dữ liệu, có nguy cơ profile rác bị truy cập hoặc gây lãng phí tài nguyên.

### Giải pháp chuẩn hóa:
Trước khi tiến hành lọc candidates và chạy pipeline login:
1. **Kiểm tra GPMLogin Local API**:
   - Khởi tạo `GPMClient(base_url="http://127.0.0.1:19995/api/v3")`.
   - Gọi `check_health()`. Nếu GPMLogin chưa mở, tự động khởi động tiến trình `GPMLogin.exe` và chờ 3–5 giây.
2. **Đồng bộ profile tự động**:
   - Đối với tài khoản `LIVE`: Nếu chưa có tên profile tương ứng trong SQLite DB hoặc API, tự động gọi `create_profile(name, raw_proxy, group_id=1)` với proxy tương ứng từ cột 10 của Excel.
   - Đối với tài khoản `DIE` / `BAN` / `SUSPENDED`: Nếu profile còn tồn tại, gọi `delete_profile(profile_id, mode=1)` để dọn sạch.

---

## 2. Quy Tắc Proxy Limit & Idempotency Trong Watchdog State

### Ràng buộc nghiệp vụ:
- Mỗi proxy port chỉ được thực hiện tối đa 2 lần login/ngày (`MAX_LOGINS_PER_PROXY = 2`).
- Mỗi máy farm S7 (`mid`) chỉ thực hiện login đúng 1 lần/ngày.

### Pitfall tính toán `proxy_count`:
- **Lỗi nghiêm trọng**: Tuyệt đối KHÔNG pre-increment biến `proxy_count` tích lũy trong hàm lọc candidate `get_candidates()`. Nếu `proxy_count[port] += 1` được áp dụng ngay khi duyệt danh sách candidate và ghi vào state hoặc trả về cho caller, thì qua mỗi chu kỳ tick của watchdog, các port sẽ bị tăng ảo và nhanh chóng vượt ngưỡng `MAX_LOGINS_PER_PROXY`, khiến watchdog từ chối xử lý các tài khoản hợp lệ còn lại.
- **Cách xử lý đúng**:
  - Dùng bản sao tạm thời `current_run_proxy_count = dict(proxy_count)` chỉ để giới hạn các candidate được chọn trong một đợt chạy.
  - Chỉ cập nhật chính thức `proxy_count[port] += 1` vào state thực tế khi worker thực sự hoàn thành một lượt login trong `ThreadPoolExecutor`.

---

## 3. Quy Tắc Tra Cứu (Search/Grep) Trong Repo `D:\Taadaa\GPM auto`

- **Cảnh báo timeout**: Thư mục `D:\Taadaa\GPM auto` chứa các thư mục dữ liệu và cache khổng lồ:
  - `checkmail_browser_data/`, `checkmail_direct_data/`, `checkmail_proxy_data/`
  - `debug_screenshots/`
  - `logs/`
- Tuyệt đối KHÔNG chạy lệnh `grep -rn` hoặc `search_files` đệ quy từ thư mục gốc `D:\Taadaa\GPM auto`. Hành động này sẽ quét qua hàng chục nghìn file hình ảnh và profile cache, gây timeout shell (>180s) và treo agent.
- **Quy chuẩn**: Luôn giới hạn phạm vi tìm kiếm trong các thư mục mã nguồn cụ thể:
  - `D:\Taadaa\GPM auto\src` (chứa `gpm_client.py`, `cdp_auth.py`, `chatgpt_hot_oauth.py`, v.v.)
  - `D:\Taadaa\GPM auto\scripts` (chứa `run_oauth_s7_pipeline.py`, `sync_gpm_lifecycle.py`, v.v.)
