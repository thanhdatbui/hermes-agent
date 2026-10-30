# Quy Trình OmniRoute Pool Recovery & Lifecycle Gmail → GPM → Antigravity

## 1. Phân Biệt Loại Lỗi Pool Antigravity
- **`invalid_grant: Refresh token rejected`**: Google đã thu hồi token của APP (OAuth Antigravity) — tài khoản Gmail CÓ THỂ vẫn sống. Không tự động kết luận nick die.  
- **Khác biệt "Pool app revoke" vs "Nick die"**: Nick die = `checkmail.live` báo DIE. App revoke = nick sống nhưng cần OAuth lại.

## 2. Thứ Tự Ưu Tiên Khi Pool Antigravity Bị Lỗi
1. Kiểm tra `checkmail.live` xem Gmail còn sống không.
2. Nếu LIVE: Mở GPM profile → Silent OAuth lại (profile đã có session Google sẵn → click "Tiếp tục/Cho phép" là xong).
3. Nếu profile GPM không còn session (bị văng): Cần login lại Gmail lên GPM trước (cần User/Pass + TOTP).
4. Nếu Gmail DIE: Xóa connection OmniRoute, dọn profile GPM, gỡ tài khoản khỏi S7.

## 3. Van An Toàn 7 Ngày Trước Khi OAuth Antigravity
- Profile GPM mới tạo / vừa login lần đầu từ điện thoại S7 lên PC: **BẮT BUỘC ngâm >= 7 ngày**.
- Lý do: Ngay trong Session 1 trên GPM, nếu cấp quyền Developer Cloud API là "New Device + Developer Privilege Escalation" → Risk Engine gắn cờ `Critical Risk` ngay lập tức.
- Kiểm tra trong `cron_chatgpt_web_pool_watchdog.py` qua hàm `is_profile_aged_7_days()` tra `created_time` của GPM profile.
- ChatGPT-Web (session token OpenAI): Lấy ngay sau Login GPM thành công, KHÔNG cần ngâm.

## 4. Cấu Hình Timeout OAuth Qua Proxy 4G MobiFone
- Proxy di động 4G xoay vòng MobiFone cần 40 - 60 giây để phân giải Google OAuth.
- **BẮT BUỘC timeout >= 120 giây** (không để 35s mặc định).
- Trong `perform_antigravity_oauth()`: vòng chờ bắt OAuth code đặt `while time.time() - start_t < 120`.

## 5. Chỉ Xóa Connection OmniRoute Khi Thực Sự Revoked Vĩnh Viễn
- Tình trạng `isActive: False` với `testStatus: active` (probe inconclusive) → Chỉ cần PATCH `isActive: True`, không xóa.
- Tình trạng `HTTP 401 Token invalid or revoked` + nick bị checkmail.live báo DIE → Mới xóa connection.
- CẤM xóa hàng loạt connection mà không kiểm tra `test` từng connection một với `POST /api/providers/{id}/test`.

## 6. Recovery Pool Gmail DIE Trên S7 (Tránh Chết Dây Chuyền)
- Khi 1 tài khoản DIE vẫn còn trong `dumpsys account` trên S7, GMS liên tục hiện "Đã xảy ra lỗi và bạn cần đăng nhập lại" làm ảnh hưởng cả máy.
- Gỡ ngay bằng `sync_gpm_lifecycle.py` hoặc `remove_device_account_fast(serial, email)`.
- Sau đó dọn profile GPM của tài khoản DIE.

## 7. Cơ Chế Phát Hiện "Chết Ngầm" (Silent Failover & Validation Trap Trong Pool OmniRoute)
- **Bẫy Silent Failover:** Trong combo pool (như `ag-gemini-pool-3`), cấu hình `failoverBeforeRetry: true` khiến khi 1 acc dính lỗi `403 VALIDATION_REQUIRED` (Google bắt quét QR/xác minh danh tính), OmniRoute tự động failover sang acc kế tiếp. Request của client vẫn trả `200 OK`, khiến acc chết bị bỏ quên ngầm cho đến khi cạn sạch cả pool.
- **Phương pháp Isolated Probing:** Để phát hiện acc lỗi, bắt buộc probe độc lập từng acc bằng header `x-omniroute-connection: <connection_id>` bắn vào `POST http://127.0.0.1:20129/v1/chat/completions` (hoặc chạy script canonical `D:/Taadaa/GPM auto/scripts/antigravity_rescue/scan_pro_accounts.py --all`).
- **Phân loại kết quả probe:**
  - `BLOCKED`: 403 chứa `VALIDATION_REQUIRED` hoặc `"Verify your account to continue"` $\rightarrow$ Cần đưa vào GPM xử lý xác minh / QR code.
  - `QUOTA_EXHAUSTED`: 429 `RESOURCE_EXHAUSTED` hoặc `model_cooldown` $\rightarrow$ Acc bình thường, chỉ hết hạn ngạch rolling window.
  - `OK`: 200 OK $\rightarrow$ Hoạt động tốt.
- **Hiện tượng ngưng nhận request do thuật toán `least-used`:** Khi combo chạy chiến lược `least-used`, các acc cũ có lượt request cao (vd > 3.500 reqs) sẽ tạm thời ngừng nhận request khi có acc mới nạp vào (mới có 200-1.000 reqs). Đây là điều phối cân bằng tải bình thường, không phải acc die hay bị block.

## 8. Kiểm Toán Ghost Entry Trong Combo Models
- Khi 1 account bị tắt (`is_active = 0`) hoặc bị tụt hạng (từ `g1-pro-tier` về `free-tier`) trong bảng `provider_connections`, OmniRoute **KHÔNG TỰ ĐỘNG GỠ** entry đó khỏi mảng `models` trong bảng `combos`.
- Hậu quả: Entry trở thành "Ghost" trong combo, gây nhiễu thống kê và lãng phí vòng lặp routing thử kết nối hỏng.
- Khi kiểm toán pool, bắt buộc đối soát `combos.models.connectionId` với `provider_connections.is_active` và `provider_specific_data.tier`. Nếu `is_active = 0` hoặc tier không khớp, phải dọn dẹp khỏi combo.
