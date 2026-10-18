# Cron LLM-Agent Loop & Telegram Gateway Message Queue Starvation Guard

## 1. Bản chất sự cố (The Incident & Root Cause)
- **Hiện tượng:** Tất cả các session Telegram bị đơ, không phản hồi trong suốt 1h30 (từ 11:00 đến 12:29), sau đó đồng loạt xả tin nhắn dồn dập lúc 12:25 - 12:29.
- **Nguyên nhân gốc rễ:**
  - Hai cronjob (`cron-auto-feed-chatgpt-pool` và `chatgpt-account-lifecycle-healer`) được tạo với lịch dày (`*/15 * * * *`) nhưng **QUÊN cờ `no_agent: True`** (mặc định của Hermes là `no_agent: False`).
  - Khi tick lúc 12:14:55, Hermes spawn một full AI Agent độc lập. Thay vì chạy script 1 giây rồi thoát, Agent này đọc stdout, tự động suy luận và rơi vào vòng lặp agentic reasoning kéo dài tận **86 turns / messages**.
  - Toàn bộ kết nối LLM tới provider và hàng đợi tin nhắn của Gateway bị chiếm dụng 100%. Các tin nhắn của Operator gửi vào Telegram bị dồn ứ trong queue chờ đợi.

## 2. Quy tắc bất biến (Invariants)
1. **100% Cronjob Tự Động Phải Là `no_agent: True`:**
   - Watchdog, crawler, cleaner, sync, status reporter bắt buộc chạy script Python thuần (`no_agent: True`), 0 token LLM, trả stdout trực tiếp.
2. **Cấm Cronjob LLM Chạy Tần Suất Cao:**
   - Bất kỳ cronjob nào có `no_agent: False` (dùng AI Agent) bắt buộc phải có tần suất $\ge 6$ giờ (cấm `*/5`, `*/15`, `*/30`).
   - Bắt buộc hard-cap `max_turns <= 5` và `timeout <= 120s`.
3. **Cơ Chế Phòng Thủ 2 Lớp (Defense-in-Depth):**
   - **Lớp 1 (PreToolUse Hook):** Hook chặn lệnh `cronjob(action='create'|'update')` nếu thiếu `no_agent: True` hoặc thiếu script hợp lệ.
   - **Lớp 2 (Reconciler Scanner):** Script quét `jobs.json` định kỳ mỗi 5 phút, tự động auto-pause mọi job vi phạm schema / thiếu `no_agent: True`.
