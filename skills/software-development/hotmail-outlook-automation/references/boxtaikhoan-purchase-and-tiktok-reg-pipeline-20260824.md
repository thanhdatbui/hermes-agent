# Hotmail BoxTaiKhoan API Purchase & TikTok Direct Registration Flow

## 1. BoxTaiKhoan API Purchase Pattern (ID 60 - OAuth2)
- **Endpoint**: `https://boxtaikhoan.com/ajaxs/client/product.php`
- **Method**: `POST`
- **Headers**:
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest'
  }
  ```
- **Kinh nghiệm mua số lượng lớn**:
  - Khi mua batch (ví dụ 20 accs), gọi `amount=1` theo vòng lặp `for i in range(N)` để nhận trực tiếp data `["mail|pass|refresh_token|client_id"]` trong response JSON trả về.
  - Không cần vào web cào trang lịch sử đơn hàng `/product-order/` (tránh lỗi DOM / 404).

## 2. Pre-Reg Token Verification Gate
- Test `refresh_token` lấy `access_token` qua Microsoft OAuth2:
  ```python
  url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
  data = f"client_id={cid}&grant_type=refresh_token&refresh_token={urllib.parse.quote(token)}&scope=offline_access%20https://graph.microsoft.com/Mail.Read".encode("utf-8")
  ```

## 3. Quy trình nạp nguồn và kích hoạt Reg TikTok tự động
1. Xác định danh sách máy hợp lệ (chưa reg TikTok + Proxy ViChanger hoạt động trả IP sạch).
2. Append các tài khoản đã mua vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (Cột 1: STT, Cột 2: mail, Cột 3: pass, Cột 7: ngày nạp, Cột 9: token, Cột 10: client_id).
3. Chạy `_detect_clean.py` để cập nhật `_clean_targets.json`.
4. Khởi chạy ngay `_run_all_targets.py` (với `TIKTOK_REG_LIMIT_STTS` và `DEVICE_LOCK_ENABLED=1`).
5. Sau khi runner kết thúc: Chạy `scripts/apply_deferred_tracking_results.py` nạp kết quả TikTok ID vào `taikhoan_dat_v2_updated .xlsx`.

## 4. Kỷ Luật Mật Khẩu Đơn Hàng & Quy Trình Truy Vết Mật Khẩu Chuẩn Hoá (User Correction 2026-10-01)
- **Mỗi tài khoản có mật khẩu riêng biệt**: Mỗi tài khoản mua từ BoxTaiKhoan đều có mật khẩu riêng ngẫu nhiên. TUYỆT ĐỐI CẤM Agent tự giả định hoặc hallucinate rằng cả lô dùng chung một mật khẩu duy nhất.
- **Quy trình truy vết mật khẩu chuẩn hoá khi mất cột PASS MAIL trong Excel**:
  1. Quét FTS trong SQLite Hermes (`C:\Users\Kibe\AppData\Local\hermes\state.db`) theo mã giao dịch đơn hàng (ví dụ `821P6a8977522f650`, `buyProduct`), hoặc chuỗi dump `hotmail_input.txt` trong lịch sử tool calls để lấy lại nguyên bản `mail|pass|token|client_id`.
  2. Quét các bản sao lưu workbook lịch sử trong `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\` (`taikhoan_dat_v2_updated _before_batch_deferred_*`) và `D:\OneDrive\TaadaaData\kibe\workbook-backups\` (`gmail_clean_v2_before_*`).
- **CẤM Fallback sang Pass TikTok**: Khi đăng nhập Hotmail web trên GPM hoặc app Outlook, tuyệt đối không được fallback lấy mật khẩu TikTok (cột D / PASS) thay thế khi cột `PASS MAIL` bị trống; phải cách ly trạng thái `BLOCKED: MISSING_MAIL_PASSWORD` để tránh bị Microsoft khóa form do thử sai liên tục.
