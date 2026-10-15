# Telegram Delegation Noise & Progress Suppression

## Vấn đề thực tế (Hit 2026-10-15)
Khi Coordinator điều phối Worker sửa code thông qua `delegate_task(background=True)` hoặc dispatch subagent chạy nền, mỗi lần một subagent hoàn tất, `tools/process_registry.py` và `gateway/run.py` (`_async_delegation_watcher`) tự động sinh một tin nhắn tổng hợp dạng:
`[ASYNC DELEGATION BATCH COMPLETE — deleg_...]`
kèm toàn bộ prompt, summary, diff và test result bằng tiếng Anh, sau đó đẩy ngược vào luồng chat Telegram của Operator.
Khi có chuỗi 4–6 workers liên tiếp (ví dụ vòng lặp sửa code theo review của Claude CLI), Operator bị dội hàng loạt tin nhắn log kỹ thuật tiếng Anh rác vào Telegram, làm ngập màn hình và trôi mất ngữ cảnh hội thoại.

## Các cơ chế gây ồn trên Telegram và cách khắc phục

### 1. Cơ chế Tool Progress (`display.tool_progress`)
Mặc định Gateway bắn/sửa các tin nhắn tiến trình `Running terminal...`, `Reading file...` khi tool đang chạy.
- **Tắt hoàn toàn:**
  `hermes config set display.platforms.telegram.tool_progress off`
- **Ghi log ngầm (chỉ ghi vào ~/.hermes/logs/tool_calls.log):**
  `hermes config set display.platforms.telegram.tool_progress log`
- **Tự động xóa bong bóng tiến trình sau khi turn kết thúc:**
  `hermes config set display.platforms.telegram.cleanup_progress true`

### 2. Cơ chế Async Delegation Completion (`_async_delegation_watcher`)
Trong `gateway/run.py`, hàm `_async_delegation_watcher()` lấy các completion event từ `completion_queue` và gọi `_inject_watch_notification()` đưa `MessageEvent(internal=True)` vào session.
- **Quy tắc điều phối Coordinator (Anti-Spam Invariant):**
  Khi đang trong phiên trao đổi trực tiếp với Operator trên Telegram, Coordinator **CẤM dispatch hàng loạt subagent ngầm rời rạc** để rồi mỗi worker kết thúc lại bắn một khối `[ASYNC DELEGATION BATCH COMPLETE]` tiếng Anh vào chat.
  Bắt buộc Coordinator phải quản lý tiến trình nội bộ, chờ kết quả hoặc tổng hợp lại thành **DUY NHẤT một thông điệp tiếng Việt súc tích** báo cáo kết quả cuối cùng cho Operator.
- **Cấu hình Gateway / Session:**
  `hermes config set display.platforms.telegram.interim_assistant_messages off` để chặn các thông báo phụ mid-turn.
