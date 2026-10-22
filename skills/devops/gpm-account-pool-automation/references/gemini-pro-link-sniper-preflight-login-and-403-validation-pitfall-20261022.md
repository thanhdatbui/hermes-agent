# Gemini Pro Link Sniper Preflight Login & Upstream 403 Validation Pitfall (2026-10-22)

## 1. Hiện Trường & Bối Cảnh Thực Tế
Trong phiên vận hành ngày 22/10/2026:
- Tự động săn mua 2 gói Google Gemini Pro 18M (9,000đ/gói) từ SumiStore API với điều khoản: *"Bảo hành trong 5 phút từ khi mua - Link Gemini Pro 18M (Phải dùng ngay)"*.
- **Đơn 1 (`nguyenkhoi14031998@gmail.com` - M40)**: Mua lúc **08:07:10**. Profile GPM M40 chưa từng được đăng nhập Google trước đó. Khi inject link kích hoạt qua CDP, Google redirect sang `accounts.google.com/signin`. Link bị bỏ ngâm quá 5 phút. Khi Agent quay lại đăng nhập Google vào 10:20 và mở lại link, Google One nhận diện token ưu đãi đã quá hạn và chuyển hướng về trang đích 15GB mặc định (`g1_landing_page=5`). Link bị cháy hoàn toàn do lỗi vận hành của Agent.
- **Đơn 2 (`taquynh06011998@gmail.com` - M52)**: Mua lúc **10:07:24**, profile GPM M52 đã có sẵn session Google, mở link kích hoạt ngay lập tức thành công gói Google AI Pro 5TB 18M, hoàn tất OAuth Antigravity và nạp vào cả 2 pool (OmniRoute `ag-gemini-pool-3` + AGY CLI `acc_26`).

---

## 2. Quy Tắc Bất Biến: Preflight Login Bắt Buộc Trước Khi Mua Link Flash
1. **Preflight GPM Session Là Điều Kiện Tiên Quyết (Prerequisite Gate)**:
   - CẤM TUYỆT ĐỐI bật tiến trình sniper hoặc gửi lệnh mua API khi profile GPM của tài khoản đích chưa có session Google cookies sống.
   - Trước khi mua, BẮT BUỘC khởi chạy profile GPM qua Local API `http://127.0.0.1:19995/api/v3/profiles/start/{id}`, kết nối CDP kiểm tra điều hướng đến `https://one.google.com/home` hoặc `https://accounts.google.com`:
     - Nếu trả về URL landing/signin (chưa đăng nhập): BẮT BUỘC thực hiện đăng nhập hoàn chỉnh (mật khẩu, giải TOTP 2FA, vượt qua recovery options/address), chụp ảnh xác minh session sống rồi mới được cấp phép mua link.
     - Kiểm tra tài khoản không bị kẹt nhóm Family (`https://families.google/families/`).
2. **Kỷ Luật Khai Báo Thời Gian Mua Hàng**:
   - Báo cáo thời gian mua hàng BẮT BUỘC lấy chính xác từ trường `checked_at` hoặc `time` trong phản hồi API JSON của shop.
   - CẤM TUYỆT ĐỐI làm tròn, khai gian mốc thời gian mua hàng hoặc đổ lỗi cho shop khi link bị hết hạn do Agent ngâm link.

---

## 3. Cạm Bẫy Upstream 403 `VALIDATION_REQUIRED` & Ảo Giác "Token Live" Do Combo Fallback
1. **Bản Chất Lỗi Upstream 403**:
   - Khi tài khoản bị Google Cloud Code (`daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent`) trả về:
     ```json
     {
       "error": {
         "code": 403,
         "message": "Verify your account to continue.",
         "status": "PERMISSION_DENIED",
         "details": [
           {
             "reason": "VALIDATION_REQUIRED",
             "domain": "cloudcode-pa.googleapis.com",
             "metadata": { "validation_url": "https://accounts.google.com/v3/signin/continue?..." }
           }
         ]
       }
     }
     ```
   - Lỗi này xảy ra khi Google phát hiện thiết bị bất thường và bắt buộc tài khoản phải xác minh phiên.
2. **Cạm Bẫy Ảo Giác Thành Công (False-Positive Live Token)**:
   - Trong OmniRoute, combo pool (`ag-gemini-pool-3`) có cơ chế tự động bắt lỗi 403 upstream và fallback nhảy sang connection sống tiếp theo trong pool (`Model antigravity/gemini-3.8-flash-tiered failed, trying next`).
   - Khi Coordinator gửi prompt test vào model combo hoặc model chung, request trả về **HTTP 200 OK** nhưng thực chất request đã được phục vụ bởi tài khoản khác (`jinrakal`, `taquynh`...).
   - Nếu Coordinator chỉ nhìn thấy kết quả 200 OK mà vội vàng tuyên bố "tài khoản đã hết lỗi, token live 100%" thì đó là **báo cáo sai sự thật nghiêm trọng**.
3. **Quy Trình Kiểm Chứng Sâu Evidence-First (Bắt Buộc)**:
   - CẤM coi việc mở link validation trên browser và bấm "Thử lại" là hoàn tất sửa lỗi.
   - BẮT BUỘC truy vấn trực tiếp cơ sở dữ liệu `storage.sqlite` của OmniRoute trên đúng `connection_id` của tài khoản đó:
     ```sql
     SELECT timestamp, status, model, account, connection_id, error_summary 
     FROM call_logs 
     WHERE connection_id = '<target_connection_id>' 
     ORDER BY timestamp DESC LIMIT 3;
     ```
   - CHỈ ĐƯỢC KẾT LUẬN tài khoản sống khi và chỉ khi:
     - `status == 200`
     - `error_summary IS NULL`
     - Bản ghi thuộc đúng `connection_id` của tài khoản vừa xử lý, không có dấu vết fallback hay retry.
