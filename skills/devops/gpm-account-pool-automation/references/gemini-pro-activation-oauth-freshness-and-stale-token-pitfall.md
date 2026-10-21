# Gemini Pro Activation: OAuth Freshness & Stale Token Pitfall Runbook

## 1. Hiện Tượng: Ảo Giác "Full Quota 100%" Nhưng Request Bị Chặn 403
- **Trên Dashboard UI (OmniRoute / 9Router)**:
  - Account hiển thị chấm xanh (Green), nhãn `Antigravity • Pro`.
  - Quota báo **`100% left`** trên tất cả model (Gemini 3.1 Flash Lite, Claude Opus, Claude Sonnet).
  - Countdown hiển thị `"Token expires in 0h 53m"`.
- **Thực tế khi gọi API**:
  - Request lập tức fail với `403 Antigravity upstream error (403)` hoặc `project_route_error`.
  - Caller nhận lỗi: `insufficient_quota` / `Error code: 403`.
  - AGY CLI dispatch báo lỗi `RESOURCE_EXHAUSTED (code 429)`.

## 2. Nguyên Nhân Kỹ Thuật (Cạm Bẫy Tái Sử Dụng Row Cũ Trong DB)
1. **Thanh Quota 100% Là Số Đo Cục Bộ**:
   - OmniRoute/9Router tính phần trăm còn lại dựa trên lượng token đã ghi nhận trong bảng `call_logs`. Account mới add vào combo chưa gọi thành công request nào nên hiển thị 100%, không phải số liệu query trực tiếp từ upstream Google.
2. **Cạm Bẫy Nạp Token Trong `setup_agy_profile_creds.py`**:
   - Sau khi sniper mua và kích hoạt link Google One AI Pro 18M trên GPM (`one.google.com`), tài khoản Gmail đã có gói Pro.
   - Tuy nhiên, script cấu hình pool chỉ chạy:
     ```sql
     SELECT access_token, refresh_token FROM provider_connections WHERE email = ?
     ```
   - Row trong `provider_connections` vốn đã tồn tại từ các đợt OAuth của chu kỳ trước (có thể từ nhiều tuần trước).
   - Refresh token này đã bị Google thu hồi (`invalid_grant`).
   - Việc copy token chết sang `.gemini/oauth_creds.json` của AGY profile và gán connection vào combo Pro làm cả 2 pool dính token hỏng.
3. **Phản Hồi Upstream Của Google**:
   - Google Cloud Code từ chối access token với `401 Unauthenticated`.
   - OmniRoute tự động gọi `https://oauth2.googleapis.com/token` với `grant_type=refresh_token`.
   - Google trả về `HTTP 400 Bad Request: {"error": "invalid_grant"}`.
   - Không có token mới, request rớt vào `403 Antigravity upstream error (403)`.

## 3. Quy Tắc Bắt Buộc Khi Onboard Nick Nâng Cấp Pro
1. **Kiểm Tra Ngày Tạo Token Cũ**:
   - Đối soát `created_at` / `updated_at` trong `provider_connections`. Nếu không phải token vừa cấp trong phiên kích hoạt thì tuyệt đối KHÔNG tái sử dụng.
2. **Bắt Buộc Chạy OAuth Mới Sau Khi Kích Hoạt Link Pro**:
   - Kích hoạt gói Google One xong -> BẮT BUỘC mở luồng OAuth Antigravity trên profile GPM để lấy refresh token mới tinh.
3. **Probe Kiểm Thử Trước Khi Đưa Vào Combo**:
   - Chạy thử 1 request test refresh qua proxy port chính chủ. Chỉ khi trả về `200 OK` mới update token vào OmniRoute DB và AGY profile.
