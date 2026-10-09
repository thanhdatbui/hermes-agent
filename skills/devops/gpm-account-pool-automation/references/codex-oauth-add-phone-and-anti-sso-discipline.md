# Codex OAuth Add-Phone Verification & Direct Email vs Google SSO Discipline

## 1. Bản chất cơ chế OpenAI OAuth cho Codex CLI (`auth.openai.com/oauth/authorize`)
- **OpenAI Checkpoint tại cổng Codex:** Khi một tài khoản được ủy quyền qua client Codex (client_id `app_EMoamEEZ73f0CkXaXp7hrann`), OpenAI luôn áp dụng chính sách kiểm duyệt nghiêm ngặt:
  - Nếu tài khoản chưa từng liên kết số điện thoại: OpenAI **bắt buộc điều hướng về `https://auth.openai.com/add-phone`** để yêu cầu OTP SMS (+1 / quốc tế / WhatsApp).
  - **Không có chuyện ngâm 48h rồi tự biến mất bước ver phone:** Dù tài khoản ngâm 10h, 48h hay 60h, nếu OpenAI yêu cầu số cho client Codex thì vẫn sẽ bật màn hình `Cần có số điện thoại`.
  - **Chiến lược tối ưu:** Không cần đợi ngâm 48h thụ động nếu pipeline đã sẵn sàng cơ chế giải quyết OTP phone (qua API thuê số như `codex_5sim_auto_verify.py`). Reg xong tài khoản có thể đẩy sang OAuth ver số dứt điểm ngay để đưa vào OmniRoute.

## 2. Kỷ luật tuyệt đối: CẤM GOOGLE SSO
- **Quy tắc bất di bất dịch:** `100% Direct Email + OTP (cấm Google SSO)`.
- **Hậu quả khi bấm `Tiếp tục với Google` / `Continue with Google`:**
  - Nếu tài khoản đăng ký theo dạng Email riêng mà lại bấm Google SSO, OpenAI coi đó là liên kết tài khoản chéo / phiên bất thường từ IP proxy.
  - Hệ thống OpenAI sẽ kích hoạt ngay rào chắn chống bot và bắt xác minh số điện thoại hoặc khóa session.
- **Biện pháp kỹ thuật bắt buộc:**
  - Trong các script tự động hóa (`run_codex_oauth_flow.py`, `batch_codex_oauth_5workers.py`, v.v.), luôn ẩn hoặc vô hiệu hóa các nút Google SSO (`button:has-text('Continue with Google')`).
  - Đăng nhập chỉ đi qua:
    1. **Session cookie có sẵn trên Profile GPM** (`choose-an-account` -> chọn thẻ tài khoản).
    2. Hoặc **Direct Email + OTP** (nhập email -> nhận OTP qua mailbox/Graph API -> nhập OTP).

## 3. Quy trình tự động xử lý form `choose-an-account` và `consent`
Khi gọi link OAuth Codex trên profile đã có session ChatGPT:
1. **Màn hình chọn tài khoản (`https://auth.openai.com/choose-an-account`):**
   - Selector chuẩn: `button:has-text('<email>'), [role='button']:has-text('<email>')`.
   - **Tuyệt đối không click thẻ container `div`** vì có thể không kích hoạt event click của button.
2. **Màn hình ủy quyền (`https://auth.openai.com/sign-in-with-chatgpt/codex/consent`):**
   - Click nút `Continue` hoặc `Tiếp tục` / `Authorize` (`button:has-text('Continue')`).
3. **Màn hình `add-phone` (nếu xuất hiện):**
   - Chuyển tiếp cho worker hoặc module thuê sim (`codex_5sim_auto_verify.py`):
     - Thuê số `openai` qua 5sim / dịch vụ OTP sim.
     - Nhập số điện thoại -> chờ nhận SMS -> điền OTP.
     - Hoàn tất callback OAuth và add token vào OmniRoute.
