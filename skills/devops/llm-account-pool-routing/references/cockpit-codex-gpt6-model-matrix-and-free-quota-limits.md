# Cockpit Tools (:60818) & OpenAI Codex Model Matrix (2026)

## 1. Bản Đồ Model Thực Tế Trong Binary Cockpit (`cockpit-cliproxy.exe`)
- **Hoàn toàn không có phiên bản "6.1"** (như `sol 6.1` hay `gpt-6.1`). Mọi chuỗi `6.1` đều là alias tự chế trên 9Router/NextChat hoặc cách gọi gộp phiên bản của người dùng.
- Binary và OpenAI Codex router chính thức chỉ có thế hệ `gpt-6-*` và `gpt-5.6-*`:
  - `gpt-6-luna`: **HỖ TRỢ TRÊN ACC FREE** (200 OK, latency cực nhanh ~8-22s, reasoning tokens động 40-270).
  - `gpt-6-sol`: **CHẶN TRÊN ACC FREE** (HTTP 400: `"The 'gpt-6-sol' model is not supported when using Codex with a ChatGPT account."`).
  - `gpt-6-astra`: **CHẶN TRÊN ACC FREE** (HTTP 400).
  - `gpt-5.6-luna`: **HỖ TRỢ TRÊN ACC FREE** (200 OK, ~15-23s).
  - `gpt-5.6-terra`: **HỖ TRỢ TRÊN ACC FREE** (200 OK, reasoning sâu ~350 tokens, nhưng latency rất cao ~30-45s và dễ timeout/503 khi context lớn). Không có model nào tên `gpt-6-terra` (trả về 404).
  - `gpt-5.6-sol`: **CHẶN TRÊN ACC FREE** (HTTP 503/400).
  - `gpt-5.5` & `codex-auto-review`: **HỖ TRỢ TRÊN ACC FREE** (200 OK).

## 2. Cơ Chế Quota & Lý Do "Chat Hi Mất 4-5% Quota" vs Luna "0%"
- **Context Overhead**: Client gửi request kèm context/system prompt kéo theo ~18.000 – 26.000 input tokens/request.
- **Cost Multiplier**:
  - `gpt-6-luna` / `gpt-5.6-luna`: Cost multiplier cực thấp, gần như không ảnh hưởng rolling window 30 ngày của acc Free.
  - `gpt-6-sol` / `gpt-5.6-sol`: Hệ số quota cao gấp hàng chục lần. Một request 25k tokens lập tức nuốt 4-5% quota tháng. Sau 20-25 request nặng, acc cạn 100% quota hoặc bị OpenAI quét revoke OAuth token (`code: token_revoked`).

## 3. Khác Biệt Giữa 3 Gateway Local
- **Cockpit (:60818)**: Proxy native chứa pool tài khoản Hotmail/Codex OAuth. Trực tiếp gọi OpenAI Codex upstream. Đã có sẵn `gpt-6-luna`.
- **OmniRoute (:20129)**: Executor `codex.ts` có sẵn trong mã nguồn, nhưng nếu chưa cấu hình pool Codex account trong DB thì request sẽ bị forward sang OpenRouter và tạch 402/401 khi hết credit.
- **9Router (:20128)**: Các tên model `gpt-5.6-luna` hiện tại trong config chỉ là alias map về Gemini (`gemini-3.7-flash-tiered`). Muốn dùng `gpt-6-luna` xịn từ acc Free thì phải add Custom OpenAI Provider trỏ về `http://127.0.0.1:60818/v1`.
