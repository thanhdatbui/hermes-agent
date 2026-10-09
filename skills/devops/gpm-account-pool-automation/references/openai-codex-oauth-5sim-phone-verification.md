# OpenAI Codex OAuth & 5sim Phone Verification Playbook

## 1. Cơ chế Xác minh Số Điện thoại Codex CLI (`auth.openai.com/add-phone`)
Khi cấp quyền OAuth cho Codex CLI (`scope=openid profile email offline_access`), OpenAI áp policy bắt buộc xác minh số điện thoại 1 lần.
Khác với Google, OpenAI áp dụng bộ lọc prefix chặt chẽ:
- **Bẫy WhatsApp (The WhatsApp Fallback Trap):**
  - Form có 2 radio button: `Tin nhắn văn bản` (SMS) và `WhatsApp`.
  - Nếu số điện thoại thuộc dải VoIP ảo hoặc prefix bị blacklist (ví dụ: DITO Philippines `0991 206...`), OpenAI tự động chuyển sang:
    `"Chúng tôi không thể gửi tin nhắn SMS đến số điện thoại này nên đã chuyển sang WhatsApp."`
  - Lúc này, React component của OpenAI gán cứng `disabled=""` cho radio SMS và đặt hidden input `channel="whatsapp"`.
  - **LỖI CHÍ MẠNG CẦN TRÁNH:** Nếu chỉ xóa số cũ điền số mới trên form dirty này, mọi lần submit tiếp theo đều mang `channel=whatsapp` -> OpenAI tiếp tục báo lỗi WhatsApp và KHÔNG BAO GIỜ gửi SMS!
- **QUY TẮC BẮT BUỘC KHI ĐIỀN FORM:**
  1. Mỗi lần đổi số PHẢI mở từ một URL OAuth sạch (`start-callback-server`) hoặc reload sạch trang để xóa trạng thái dirty.
  2. Đồng bộ mã quốc gia: Cần đổi value trên thẻ `<select>` ngầm (ví dụ `sel.value = "PH"; sel.dispatchEvent(new Event("change", {bubbles: true}))`).
  3. BẮT BUỘC click tường minh vào `label:has-text("Tin nhắn văn bản")`.
  4. Assert cứng: `input[name="channel"].value === "sms"` và `label[Tin nhắn văn bản].getAttribute("data-state") === "on"`. Nếu dính `whatsapp` -> CẤM BẤM SUBMIT.

## 2. Chiến lược Chọn Nước & Nhà Mạng 5sim Cho OpenAI (Budget <= $0.16)
- **Philippines (`philippines` / `virtual58` - $0.1077 ~ 2.700đ):**
  - Lựa chọn tối ưu chi phí số 1.
  - Các đầu số thuộc mạng Smart/TNT (`0928...`, `0970...`, `0907...`) nhận SMS cực nhanh (~10s).
  - Nếu gặp đầu số DITO (`0991 206...`), OpenAI có thể ép đẩy qua WhatsApp -> cancel ngay trong 2s để hoàn tiền.
- **Hy Lạp (`greece` / `virtual66` - $0.1491 ~ 3.700đ):**
  - Dự phòng châu Âu kho lớn (>200k số), rate ~15%, ít dính VoIP filter.
- **CÁC NƯỚC CẦN TRÁNH:**
  - Argentina ($0.05), Anh virtual51/59 ($0.06), Brazil ($0.07): Toàn bộ là số ảo rẻ tiền, gateway SMS của OpenAI chặn 100%, không nhận được SMS.
- **Quy tắc An toàn Vốn:**
  - Polling SMS trong tối đa 120s.
  - Nếu không có SMS hoặc OpenAI từ chối số -> gọi ngay `GET https://5sim.net/v1/user/cancel/{order_id}` để nhận lại 100% tiền hoàn về ví 5sim.

## 3. Khác biệt Mô Hình: Codex (Terra) vs ChatGPT Web (Sol)
- **Codex OAuth CLI (`provider: codex`):**
  - Đi qua endpoint `https://chatgpt.com/backend-api/codex/responses`.
  - **CHỈ HỖ TRỢ model `gpt-5.6-terra`** (và các biến thể `terra-high`, `terra-max`, `terra-ultra`).
  - Gọi `codex/gpt-5.6-sol` sẽ bị OpenAI chặn với lỗi `HTTP 400`:
    `"The 'gpt-5.6-sol' model is not supported when using Codex with a ChatGPT account."`
- **ChatGPT Web Session Cookies (`provider: chatgpt-web`):**
  - Đi qua web session thông thường, hỗ trợ **`gpt-5.6-sol-high`** (Sol).
- **Điều phối OmniRoute Combo:**
  - Gom các tài khoản Codex OAuth đã verify vào combo **`codex-terra-pool`** (chiến lược `p2c`, load-balancing model `codex/gpt-5.6-terra`).
  - Khi cần code/reasoning nặng: gọi combo `codex-terra-pool`.
  - Khi cần chat tổng hợp/search: gọi combo `chatgpt-web-pool`.

## 4. Visual Evidence Checkpoint Invariant
Tuân thủ Hard Invariant §VH (Max blind steps = 1):
- **Checkpoint 1 (Pre-Submit):** Chụp ảnh toàn màn hình sau khi chọn quốc gia, click SMS, điền số. Xác nhận bằng mắt chữ "Tin nhắn văn bản" được active.
- **Checkpoint 2 (Post-Submit):** Chụp ảnh ngay phản hồi. Nếu chuyển sang "Kiểm tra điện thoại - Vui lòng nhập mã xác minh..." thì mới bắt đầu chờ OTP. Nếu hiện cảnh báo WhatsApp thì hủy số đổi số khác ngay lập tức.
- **Checkpoint 3 (OTP Filled):** Chụp ảnh mã OTP đã nằm trong form trước khi bấm hoàn tất.
