# GPM Profile Proxy Safety Invariant & Post-Reboot Resource Sync Protocol

## 1. Cấm Tuyệt Đối Chạy Profile Farm Không Có Proxy (Direct IP Leak Ban)
- **Căn nguyên sự cố:** Khi thực hiện tác vụ tự động hóa hoặc đăng ký dịch vụ (như AWS / Gmail / Hotmail / TikTok), việc tự ý tạo profile GPM mới không gắn proxy (`raw_proxy == ""`) hoặc chọn profile farm nhưng không xác thực proxy làm rò rỉ IP trực tiếp của máy host (Kibe/Admin).
- **Hậu quả:** Khiến toàn bộ dàn tài khoản nuôi bị liên đới (chain ban), cờ bot Google / AWS kích hoạt và làm hỏng tài sản farm.
- **Quy tắc bất biến:**
  1. Mọi profile GPM liên quan đến farm (Gmail, Hotmail, TikTok) BẮT BUỘC phải mang proxy di động (MobiProxy / MikroTik) hợp lệ.
  2. CẤM tạo profile mới ad-hoc/tạm bợ khi farm đã có sẵn pool profile (Gmail, Hotmail, TikTok). Bắt buộc tái sử dụng profile có sẵn.
  3. Trước khi khởi động profile: BẮT BUỘC kiểm tra trường `raw_proxy` qua API `GET /api/v3/profiles/{id}`. Nếu `raw_proxy` rỗng hoặc bị xóa -> DỪNG NGAY (FAIL-CLOSED), cấm mở trình duyệt.
  4. Sau khi khởi động Chromium qua CDP: BẮT BUỘC điều hướng đến `https://api.ipify.org?format=json` để đọc IP thực tế và so khớp với dải IP proxy được giao trước khi điều hướng sang trang đích.

## 2. Đặc Tả Cơ Giới Hóa Mechanical Gate: `guard_gpm_proxy.py` (Claude CLI Unified Spec)
Thay vì chỉ trông chờ vào prompt hay memory (AI vẫn có thể vi phạm), hệ thống bắt buộc triển khai chốt chặn cơ giới hóa 3 lớp fail-closed:

### Lớp 1: Entry Schema Gate (Pre-Tool Hook Chặn Tạo/Sửa Profile)
- Đăng ký vào hook `pre_tool_call` của Hermes (matcher: `terminal|patch|write_file`).
- Quét mọi request/lệnh gọi tới endpoint `/api/v3/profiles/create` và `/api/v3/profiles/update`:
  - Bắt buộc payload JSON phải có key `raw_proxy`.
  - Chặn ngay (`action: block`): `raw_proxy` là rỗng (`""`), `null`/`None`, `direct`, `none`, chứa IP loopback `127.0.0.1`, `localhost`, IP LAN `192.168.x.x` (trừ port proxy hợp lệ của farm), hoặc trùng IP WAN của máy host Kibe.
  - Port proxy bắt buộc nằm trong whitelist dải proxy farm (MobiProxy `5100-5200` hoặc MikroTik `10000-30000`).

### Lớp 2: Pre-Launch Enforcement Gate (Chặn Khởi Động Trình Duyệt Không Proxy)
- Trước khi gọi `/api/v3/profiles/start/{id}`:
  - Gate probe nhanh `GET /api/v3/profiles/{id}` để đọc metadata thật (`fresh=True`).
  - Nếu profile thiếu proxy, `raw_proxy == ""`, hoặc cờ `skip_proxy_check=true` mà không có fallback proxy hợp lệ -> DENY/BLOCK ngay lập tức.
  - Fail-closed: Mọi lỗi kết nối GPM API, timeout, exception hay parse error đều mặc định là **DENY**.

### Lớp 3: Post-Launch Egress Canary & Runtime Quarantine
- Sau khi khởi động trình duyệt và kết nối cổng CDP:
  - Bắt buộc chạy Canary query ngầm đến `https://api.ipify.org?format=json`.
  - Nếu `exit_ip == host_public_ip` (rò rỉ IP nhà Kibe) hoặc không thể xác định exit IP qua proxy:
    - **Lập tức Force-Kill trình duyệt trong <= 3 giây** (`Page.close` và gọi `POST /api/v3/profiles/close/{id}`).
    - Cách ly profile (Quarantine), ghi log alert đỏ và dừng tác vụ.

### Bộ Test Offline Bắt Buộc (Offline Unit Test Matrix):
- Module gate bắt buộc đạt 100% test coverage offline với network bị chặn (mock dependencies `FakeGPM`, `FakeProbe`, `FakeHostIP`):
  1. Deny matrix: `raw_proxy` rỗng, `None`, `"direct"`, host loopback/private, port ngoài range, host IP == exit IP.
  2. Fail-closed matrix: inject exception/timeout vào dependency -> bắt buộc trả về DENY.
  3. Allow matrix: proxy MobiProxy/MikroTik hợp lệ -> trả về ALLOW.

## 3. Xử Lý Hiện Tượng GPM Đòi Cập Nhật Resource Sau Reboot Máy
- **Hiện tượng:** Sau khi máy reboot (như chu kỳ 05:20 sáng), khi gọi API khởi động profile v3, GPM trả về lỗi:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  ```
- **Bản chất kỹ thuật:**
  - File thực thi và DLL trong `gpm_browser_chromium_core_142` trên đĩa vẫn nguyên vẹn 100%.
  - Khi app GPMLogin khởi động mới sau reboot, logic nội bộ yêu cầu đồng bộ trạng thái runtime/manifest với server GPMLogin trước khi Local API v3 cho phép khởi chạy profile. File version trong thư mục core có thể tạm thời hiển thị `1.0` thay vì `1.1`.
- **Quy trình kích hoạt:**
  - Không tự tiện xóa hay ghi đè lung tung vào thư mục core trình duyệt.
  - Khởi chạy app GPM với cửa sổ hiển thị, thực hiện thao tác mở profile trên app hoặc xác nhận cập nhật gói tài nguyên qua giao diện GPM để hệ thống nạp lại manifest hợp lệ.
