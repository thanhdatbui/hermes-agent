# Triage: Single-Message Session Provider Failure (Antigravity 400 & Resume-Pending-Expired)

## 1. Hiện tượng & Bối cảnh
- User vừa tạo 1 topic mới hoặc vừa gửi đúng **1 tin nhắn đầu tiên** (kèm ảnh hoặc text), nhưng bot lập tức quay `iteration 1/100, receiving stream response` rồi văng lỗi:
  `⚠️ The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- Khi user thử gõ `/compress`, hệ thống báo:
  `Not enough conversation to compress (need at least 4 messages).`
- User thắc mắc: *"Session đó tao mới chat có 1 tin luôn ấy, tại sao bị lỗi?"*.

---

## 2. Bản chất kỹ thuật & Phân tích nguyên nhân gốc rễ (Root Cause)

### A. Cơ chế `resume_pending_expired` tại `gateway/session.py`
Khi một topic/session được tạo hoặc tái kích hoạt sau khi gateway restart:
1. Trong `gateway_routing` (`state.db`), nếu session cũ từng bị ngắt hoặc cờ `resume_pending` quá hạn window (`auto_continue_freshness_window`, mặc định 1h), gateway kích hoạt:
   ```json
   "was_auto_reset": true,
   "auto_reset_reason": "resume_pending_expired",
   "reset_had_activity": true
   ```
2. Session bị reset tự động, nhưng metadata liên kết thread Telegram (`session_key = agent:main:telegram:dm:<chat_id>:<thread_id>`) vẫn giữ con trỏ cũ.

### B. Lỗi HTTP 400 Bad Request từ Upstream Provider (OmniRoute / Antigravity)
Khác với lỗi timeout hay 503 mạng, log runtime ghi nhận chính xác:
```text
agent.conversation_loop: API call failed (attempt 4/4) error_type=APIError 
provider=omni base_url=http://192.168.110.123:20129/v1 model=ag-gemini-pool-3 
summary=antigravity/gemini-3.8-flash-tiered: model — [400]: Antigravity upstream error (400)
```
- Khi user gửi ảnh, hàm `_prepare_inbound_message_text` buffer ảnh để nạp multimodal native qua `build_native_content_parts` (`agent/image_routing.py`).
- Nếu môi trường runtime bị desync (như xung đột giữa repo `D:\Taadaa\Hermes` và venv `C:\Users\Kibe\AppData\Local\hermes\hermes-agent` do `hermes_dev.pth`), payload request đóng gói gửi qua OpenAI-compatible endpoint của OmniRoute bị lỗi schema/format đối với upstream Antigravity/Gemini (`[400]: Antigravity upstream error`).
- Upstream trả về 400 liên tiếp 4 lần retry $\rightarrow$ `_gateway_provider_error_reply` che giấu chi tiết và hiển thị thông báo lỗi retry chung chung ra chat.

---

### 3. Độc lập hạ tầng: Farm & Cấu hình người dùng (User Invariant)
Khi khắc phục và giải trình cho user, BẮT BUỘC ghi nhớ:
1. **Farm vận hành độc lập 100%:**
   - Kịch bản farm (`multi_machine_feed_session.py`, `run_batch_live_2fa.py`, `inspect_machine.py`...) chạy trên Python riêng (`D:\CodexRuntime\tiktok-video\venv-core024`), không dùng Hermes runtime.
   - Sửa Hermes hoàn toàn KHÔNG ảnh hưởng thiết bị Android, ADB hay mạng Farm.
2. **Cấu hình người dùng bất biến (Preserved):**
   - File cấu hình cá nhân nằm ở `%LOCALAPPDATA%\hermes\`: `config.yaml`, `cron/jobs.json`, `memories/MEMORY.md`, `memories/USER.md`, `scripts/` (600+ scripts).
   - Việc gom mã nguồn chỉ diễn ra trên tầng Git repo `D:\Taadaa\Hermes` và thư viện venv `site-packages`, tuyệt đối không đụng vào dữ liệu cá nhân.

---

### 4. Quy trình Triage & Khắc phục chuẩn xác (SOP)
1. **Kiểm tra log thật qua Python (Tránh vi phạm Guard):**
   ```bash
   python -c "
   from pathlib import Path; import os
   p = Path(os.environ['LOCALAPPDATA']) / 'hermes' / 'logs' / 'agent.log'
   if p.exists():
       lines = [l for l in p.read_text('utf-8', 'replace').splitlines() if 'attempt 4/4' in l or 'error_type=APIError' in l]
       for l in lines[-5:]: print(l)
   "
   ```
2. **Khẳng định nguyên nhân minh bạch với User:**
   - Xác nhận ngay lý do session mới tinh 1 tin vẫn lỗi: do upstream provider trả về HTTP 400 (Bad Request payload), không phải do user chat nhiều làm phình context.
   - Trấn an User: Farm và toàn bộ cấu hình riêng (`config.yaml`, `cron`, `memories`) được bảo toàn 100%.
