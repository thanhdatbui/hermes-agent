# Gmail Trust Escalation, OAuth Lifecycle & Lean GPM Profile Backup

## 1. Cơ Chế Tăng Trust Score Qua Antigravity OAuth (OmniRoute)
- **Nâng Cấp Định Danh Thành Developer / Cloud User:**
  - Khi tài khoản Gmail thực hiện ủy quyền Google OAuth (`firstparty/nativeapp`) cho Antigravity (Google Cloud Client), hệ thống Google tự động nâng cấp phân loại tài khoản từ "người dùng thông thường" lên nhóm **Developer / Cloud User**.
  - Đây là nhóm tài khoản có độ ưu tiên bảo mật và độ tin cậy nội bộ (Trust Score) cao nhất của Google.
- **Tạo Traffic Sạch & Đều Đặn Qua API:**
  - Mỗi request gọi model AI qua OmniRoute phát sinh truy vấn HTTPS có chữ ký OAuth hợp lệ gửi đến hạ tầng Google Cloud.
  - Đây là hoạt động tương tác sạch 100%, được Google ghi nhận là người dùng thực chất, có giá trị vượt trội so với các hành vi "nuôi" nhân tạo (lướt web, gửi mail chéo).
- **Lớp Giáp Bảo Vệ Cho Acc Mới Reg Chưa Đăng Ký Dịch Vụ:**
  - Acc mới reg nếu để không (idle) rất dễ bị thuật toán chống bot gắn cờ và ép checkpoint xác minh số điện thoại.
  - Khi được cấp quyền Developer OAuth và phát sinh token refresh / API calls, tài khoản lập tức có lịch sử hoạt động chính thống trên Google Cloud Console, tạo kháng thể chống quét checkpoint vô cớ.
- **Nguyên Tắc Bất Biến: Tính Nhất Quán IP 1:1 (IP Consistency):**
  - Mọi request của tài khoản trên OmniRoute bắt buộc phải đi qua đúng Proxy Port của máy đó.
  - Sau khi exchange OAuth code thành công, bắt buộc gọi ngay API:
    ```http
    PUT /api/settings/proxies/assignments
    Content-Type: application/json

    {
      "scope": "account",
      "scopeId": "<connection_id>",
      "proxyId": "<proxy_registry_id>"
    }
    ```
  - Nếu gửi request AI từ IP nhà hoặc đổi IP đột ngột giữa các cụm, Google sẽ kích hoạt cơ chế `403 VALIDATION_REQUIRED`.

---

## 2. Bản Chất Vòng Đời Gmail & Giải Mã Hiểu Lầm Về "Nuôi Mail"
- **Không Cần Gửi Thư Chéo / Xem Video:**
  - Gmail farm là **Gmail cổ (Aged Account)** có sẵn độ trust từ thời gian tồn tại trong cơ sở dữ liệu Google.
  - Việc dùng tool tự động gửi thư qua lại giữa các acc trong cùng dải mạng dễ kích hoạt bộ lọc phát hiện cụm (Cluster Detection), khiến toàn bộ dàn mail bị gắn cờ spam.
- **Chính Sách Inactive Account (Xóa Tài Khoản Quá 2 Năm):**
  - Google chỉ xét xóa tài khoản nếu hoàn toàn không có đăng nhập / hoạt động trong 2 năm liên tục (bắt đầu áp dụng từ 12/2023).
  - Quá trình quét của Google rất thận trọng và ưu tiên tài khoản rác tạo xong bỏ ngay. Các tài khoản có email khôi phục sống, từng đăng ký dịch vụ hoặc có liên kết thiết bị luôn được xếp cuối hàng đợi hoặc miễn trừ.
  - Khi đăng nhập vào GPM và kích hoạt 2FA TOTP, tài khoản được reset mốc hoạt động 2 năm và được bảo vệ vĩnh viễn.
- **Gỡ Mail Khỏi Bảo Mật TikTok Không Làm Mail Bị Die:**
  - Google và TikTok là 2 nền tảng độc lập. Google không theo dõi hay trừng phạt việc gỡ liên kết khỏi TikTok.
  - Hộp thư sau khi gỡ dịch vụ chỉ trở về trạng thái nghỉ (idle), không phát sinh rủi ro checkpoint.

---

## 3. Kiến Trúc Sao Lưu Tinh Gọn GPM Profiles (Lean Backup)
- **Vấn Đề Với Thư Mục Profile Đầy Đủ:**
  - Mỗi thư mục profile Chromium Core 142 chứa hàng nghìn file cache, code cache, crashpad, dung lượng từ 30-150 MB/profile. Sao lưu toàn bộ 20-40 profile sẽ tốn 2-5 GB và rất chậm khi nén.
- **Giải Pháp Nén Tinh Gọn (Selective Compression):**
  - Để bảo toàn 100% phiên đăng nhập (session, cookies, localStorage, saved logins) và vân tay trình duyệt, chỉ cần lưu trữ các thành phần cốt lõi:
    * `profile_data.db` (metadata toàn bộ profile, proxy, fingerprint keys).
    * `Default/Network/Cookies` (SQLite cookie jar chứa session Google).
    * `Default/Preferences` (cấu hình profile).
    * `Default/Login Data` (mật khẩu đã lưu).
    * `Default/GPMSoft/gpm_pi.dat` (metadata nhận diện profile của GPM).
    * `Local State` (khóa giải mã DPAPI / cookie encryption key).
  - **Loại trừ toàn bộ:** `Cache/`, `Code Cache/`, `Crashpad/`, `Service Worker/CacheStorage/`, `DawnCache/`.
  - Kết quả: File nén của 25+ profile giảm từ ~3.5 GB xuống chỉ còn **~200 MB**, nén trong < 30 giây và tự động đồng bộ tức thì lên OneDrive (`D:\OneDrive\backup\GPM\gpm_active_profiles_YYYYMMDD.zip`).
