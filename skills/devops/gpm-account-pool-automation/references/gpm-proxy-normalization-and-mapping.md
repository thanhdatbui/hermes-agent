# Chuẩn hóa Proxy Profile GPM qua Local API v3

## 1. Bối cảnh & Nguyên nhân lỗi Proxy Profile
Khi các profile GPM được tạo hoặc lưu tạm thời qua các công cụ trung gian / bridge cục bộ, `raw_proxy` có thể bị gán sai định dạng dạng:
- `http://192.168.110.2:20069 (test.taadaa.click:5137)`
- `http://192.168.110.2:20072 (mirotik1.taadaa.click:10001)`
- Dạng chứa tiền tố `http://` cục bộ hoặc bao bọc thông tin thật trong dấu ngoặc đơn `(...)`.

Các định dạng này khiến GPM v3/v4 hiểu sai giao thức, trỏ nhầm về IP bridge nội bộ hoặc không thể kết nối Internet trực tiếp khi mở trình duyệt độc lập.

## 2. Nguồn dữ liệu Proxy chuẩn (Source of Truth)
- File mapping chuẩn: `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (Sheet: `Proxy`).
  - Cột 0: Số máy (`mid` - ví dụ `1, 2, ..., 70, 72`).
  - Cột 2: Raw proxy chuẩn (`host:port:user:pass`).
  - Ví dụ chuẩn:
    - `test.taadaa.click:5137:mobi37:TaadaaMobi#2026!`
    - `mirotik1.taadaa.click:10001:admin@1:admin@1`

## 3. Quy trình chuẩn hóa bằng API GPM v3
- **Local API Endpoint:** `http://127.0.0.1:19995/api/v3`
- **Lấy danh sách profiles:**
  - GET `/profiles?page={page}&per_page=50`
  - Đọc `pagination.total_page` để duyệt qua toàn bộ các trang (không dừng ở 50 profile đầu tiên).
- **Phát hiện profile cần chuẩn hóa:**
  - `raw_proxy.startswith("http://")` hoặc `("(" in raw_proxy and ")" in raw_proxy)`.
- **Trích xuất số máy (MID):**
  - Khớp qua regex tên profile: `r"^\s*(\d+)\s*-"` (ví dụ: `70 - dinhgia09062002@gmail.com - 20070` -> `mid=70`).
  - Fallback qua port nếu tên chứa dạng 5 số: `r"200(\d{2})"` -> `mid`.
- **Cập nhật profile qua API:**
  - `POST /api/v3/profiles/update/{profile_id}`
  - Body: `{"raw_proxy": "<standard_proxy_string>"}`
  - Thành công khi HTTP 200 và response `{"success": true}`.

## 4. Script thực thi chuẩn
Đã được chuẩn hóa và lưu tại: `D:\Taadaa\GPM auto\scripts\normalize_gpm_proxies.py`.
Khi phát hiện proxy profile bị sai lệch hoặc sau các đợt import / migrate hàng loạt, chạy lại script này để đưa toàn bộ 100% profiles về proxy chuẩn.
