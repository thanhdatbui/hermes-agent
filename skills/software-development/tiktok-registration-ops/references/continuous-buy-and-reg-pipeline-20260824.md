# Pipeline Mua Hotmail BoxTaiKhoan & Reg TikTok Tự Động (Continuous Flow)

## 1. Trigger & Bối cảnh
Khi user yêu cầu: *"Mua N hotmail reg các máy chưa reg..."* hoặc *"Mua mail nạp và reg TikTok"*.

## 2. Quy tắc luồng khép kín liên tục (CẤM DỪNG NỬA CHỪNG)
Tuyệt đối không dừng lại ở bước mua tài khoản hay nạp Excel để báo cáo rồi chờ user giục. Phải chạy xuyên suốt qua 5 bước:

### Bước 1: Mua tài khoản qua BoxTaiKhoan API
- Endpoint: `POST https://boxtaikhoan.com/ajaxs/client/product.php`
- Action: `buyProduct`
- Gói: `id = 60` (Hotmail OAuth2 - 393đ).
- Lưu danh sách vào `D:\Taadaa\Hotmail\hotmail_input.txt`.

### Bước 2: Pre-check OAuth2 Refresh Token qua Microsoft Graph API
- Endpoint: `https://login.microsoftonline.com/consumers/oauth2/v2.0/token`
- Header: `Content-Type: application/x-www-form-urlencoded`
- Payload: `client_id={cid}&grant_type=refresh_token&refresh_token={token}&scope=offline_access%20https://graph.microsoft.com/Mail.Read`
- Đảm bảo token trả về `access_token` hợp lệ (phát hiện và loại bỏ token shop bị cắt cụt).

### Bước 3: Ghi vào Kho Mail Nguồn `gmail_clean_v2.xlsx`
- Cột 1: STT máy
- Cột 2: Email Hotmail
- Cột 3: Password
- Cột 7: Ngày nạp (`YYYY-MM-DD`)
- Cột 9: OAuth2 Refresh Token
- Cột 10: Client ID (`9e5f94bc-e8a4-4e73-b8be-63364c29d753`)

### Bước 4: Khởi chạy Batch Reg TikTok ngay lập tức
- Thiết lập biến môi trường:
  ```bash
  export DEVICE_LOCK_ENABLED=1
  export TIKTOK_REG_LIMIT_STTS="<danh sách STT máy mục tiêu>"
  ```
- Khởi chạy nền: `python _run_all_targets.py` (theo dõi tiến độ qua wait/poll, không thoát session).

### Bước 5: Apply Tracking CSDL & Thu dọn Hiện trường
- Chạy apply tracking kết quả hoãn:
  ```bash
  python scripts/apply_deferred_tracking_results.py <list_tracking_result_json>
  ```
- Force stop app TikTok về Home cho toàn bộ máy.
- Mở khóa máy thành công, giữ `FAILED_LOCKED` cho các máy lỗi để kiểm tra theo quy định.
