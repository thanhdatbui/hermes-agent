# Phân Biệt Cơ Chế Thu Hồi Session: Antigravity Google OAuth vs ChatGPT-Web NextAuth Cookie & Bẫy Phone Checkpoint Trì Hoãn (2026-09-20)

## 1. Bản Chất 2 Cơ Chế Xác Thực Trong Pool OmniRoute
Khi vận hành pool tài khoản LLM kết hợp giữa `antigravity` (Google Cloud Code Assist) và `chatgpt-web` (OpenAI Web Reverse), cần phân biệt rõ cơ chế duy trì phiên để không đưa ra kết luận sai lầm về trạng thái tài khoản:

| Tiêu chí | Provider `antigravity` (OAuth) | Provider `chatgpt-web` (Web Cookie) |
|---|---|---|
| **Cơ chế xác thực** | Google OAuth 2.0 (Refresh Token trao đổi lấy Access Token mỗi ~1h). | NextAuth Session Token (`__Secure-next-auth.session-token`). |
| **Bên cấp & kiểm soát** | Máy chủ danh tính Google (`accounts.google.com`). | Máy chủ OpenAI (`chatgpt.com`). |
| **Khi Gmail bị khóa backend** | **Chết ngay lập tức**: Google OAuth trả về `invalid_grant` (`unrecoverable_refresh_error`), token bị hủy vĩnh viễn. | **Vẫn sống tạm thời**: OpenAI không liên tục verify trạng thái Gmail. Chừng nào cookie phiên chưa hết hạn (nhiều tuần), request chat vẫn 200 OK. |
| **Khả năng tái sinh** | Cần giải quyết checkpoint của Gmail trước khi có thể cấp lại OAuth code. | Không thể đăng nhập lại một khi OpenAI yêu cầu re-authenticate. |

---

## 2. Bẫy Ngộ Nhận: "Tài khoản đang gọi được Gemini nghĩa là còn sống an toàn"
- **Hiện tượng**: Tài khoản vẫn chat / generate code bình thường qua `antigravity/gemini-2.5-flash`, nhưng sau đó đột ngột bị gán nhãn DIE hoặc mất phiên.
- **Nguyên nhân cốt lõi**:
  - Request suy luận Gemini gọi vào endpoint `cloudaicompanion.googleapis.com` chỉ kiểm tra tính hợp lệ của **Access Token** hiện hành, hoàn toàn không chạy thuật toán rà soát danh tính.
  - Sau 30–60 ngày reg tài khoản qua IP mobile proxy/Android farm, Google Risk Engine sẽ kích hoạt cơ chế **Hậu kiểm an ninh** (Delayed Security Checkpoint / `challenge/iap`).
  - Khi OmniRoute gửi Refresh Token để gia hạn, Google từ chối và chuyển hướng tài khoản sang trang bắt buộc nhập Số Điện Thoại xác minh danh tính.
  - Trên các hệ thống check-live chuẩn (`checkmail.live`), tài khoản bị vướng Phone Checkpoint được phân loại chính xác là **DIE/Disabled** vì không thể tự động lấy token hay đăng nhập không cần can thiệp người dùng.

---

## 3. Quy Tắc Vận Hành & Khôi Phục Session Farm
1. **Kiểm tra Checklive trước khi can thiệp**: BẮT BUỘC dùng `run_checkmail_kibe_farm.py` (checkmail.live) qua mobile proxy để phân loại LIVE vs DIE trước khi đưa vào hàng đợi login GPM.
2. **Dọn sạch Profile GPM của tài khoản DIE**: Sử dụng `sync_gpm_lifecycle.py` để xóa bỏ profile DIE trên GPMLogin và gỡ phiên trên máy S7, tránh hao tổn tài nguyên và tránh việc script tự động cố login vào tài khoản chết gây nghẽn proxy.
3. **Tuổi ngâm tài khoản (>= 7 ngày)**: Khi lọc ứng viên login tự động từ Excel, BẮT BUỘC tra cứu ngày tạo gốc từ file nguồn (`gmail_clean_v2.xlsx` cột ngày tạo), KHÔNG đọc cột `Cập Nhật` của master file (vốn là timestamp của lần checklive gần nhất).
4. **Bảo vệ máy farm khi mở rộng khung giờ ban ngày**: Khi mở rộng watchdog login/OAuth chạy vào khung giờ rảnh ban ngày (sáng/trưa), bắt buộc kẹp 2 lớp bảo vệ:
   - `acquire_device_lock`: Bỏ qua nếu có tiến trình khác đang giữ lock.
   - `is_machine_idle`: Đệm an toàn ít nhất 45 phút (`MIN_IDLE_BUFFER_MIN = 45`) so với slot nuôi feed tiếp theo trong `manifests/assignment-v1-*.json`.
