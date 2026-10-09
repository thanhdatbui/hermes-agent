# OmniRoute Antigravity OAuth: 1:1 Proxy Assignment, Model Sync & Account Trust Architecture

## 1. Tự Động Hóa Gán Proxy 1:1 & Model Sync Sau Khi Add OAuth

Khi nạp tài khoản Gmail từ Profile GPM vào OmniRoute (port 20129) làm kết nối Antigravity OAuth (`/api/oauth/antigravity/exchange`):
Mặc định OmniRoute chỉ lưu trữ OAuth refresh token và gán connection vào pool chung, **chưa tự động gán proxy**. Nếu connection gọi API qua IP mạng nhà hoặc IP khác với IP đăng nhập ban đầu, Google sẽ kích hoạt `403 VALIDATION_REQUIRED` hoặc checkpoint thiết bị.

### Chu trình 3 bước bắt buộc sau khi exchange code thành công:
1. **Lấy `connection_id`:** Từ payload phản hồi của `POST /api/oauth/antigravity/exchange` (`res["connection"]["id"]`).
2. **Gán Proxy 1:1 theo Port:**
   - Tra cứu `proxyId` từ endpoint `GET http://127.0.0.1:20129/api/settings/proxies` theo cổng của profile (ví dụ Port `5112`, `5124`, `10001`...).
   - Gọi API gán proxy với scope `account`:
     ```http
     PUT http://127.0.0.1:20129/api/settings/proxies/assignments
     Content-Type: application/json

     {
       "scope": "account",
       "scopeId": "<connection_id>",
       "proxyId": "<proxy_id>"
     }
     ```
   - *Lưu ý:* `scope` BẮT BUỘC là `"account"` (không dùng `"connection"` hay `"provider"`).
3. **Kích hoạt Models:**
   - Gọi `POST http://127.0.0.1:20129/api/providers/<connection_id>/sync-models` để đồng bộ danh mục model (12 models) và thiết lập `token_expires_at` trong `storage.sqlite`, tránh lỗi `ALL_TARGETS_SKIPPED`.

---

## 2. Kiến Trúc Trust: Tại Sao Dùng Antigravity Tăng Độ Bền Cho Gmail Cổ & Mới

| Yếu Tố | Hành Vi Thông Thường (Lướt web / Nuôi gửi thư) | Tương Tác Qua Antigravity / Google Cloud OAuth |
|---|---|---|
| **Phân loại tài khoản** | Người dùng phổ thông (Consumer Tier) | Nhà phát triển / Điện toán đám mây (Developer / Cloud Tier) |
| **Bảo vệ hệ thống** | Dễ bị quét mass-registration nếu idle lâu | Được ưu tiên duy trì phiên, ít bị checkpoint vô cớ |
| **Bản chất Traffic** | Thường bị nghi ngờ botnet nếu script lặp | 100% Request HTTPS sạch có chữ ký số OAuth tới Google API |
| **Tác dụng với Acc Mới** | Dễ chết sau vài ngày nếu không có hoạt động | Tạo ngay lịch sử sử dụng hợp pháp trên Google Cloud Console |
| **Điều kiện tiên quyết** | Đổi IP ngẫu nhiên thường gây văng | **BẮT BUỘC IP CONSISTENCY 1:1**: Request gọi AI phải đi qua đúng port proxy đã login |

---

## 3. Quy Trình Sao Lưu GPM Profile Định Kỳ (D:\OneDrive\backup\GPM\)

Để đảm bảo không mất session cookie quý giá khi GPM lỗi database hoặc xung đột phiên:
1. **Database Snapshot:**
   - Sao chép `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db` sang `D:\OneDrive\backup\GPM\profile_data_backup_YYYYMMDD.db`.
2. **Gói Nén Session Tinh Gọn (Selective Compression):**
   - Chỉ nén các profile đang hoạt động (`GroupId = 1`).
   - Loại trừ thư mục rác để tối ưu tốc độ và dung lượng (<150MB thay vì hàng chục GB):
     - Bỏ qua: `Cache`, `Code Cache`, `Crashpad`, `Service Worker/CacheStorage`.
     - Giữ lại 100%: `Default/Network/Cookies`, `Default/Preferences`, `Default/Login Data`, `Default/GPMSoft`, `Local State`.
   - File nén lưu tại: `D:\OneDrive\backup\GPM\gpm_active_profiles_YYYYMMDD.zip`.
   - Kiểm tra bằng `zipfile.testzip()` đảm bảo 0 lỗi trước khi bàn giao.
