# Receipt Enforcer Hook & Phantom Dispatch Flagging Traps

## 1. Cơ Chế Hoạt Động Của Receipt Enforcer Gateway Hook
Hệ thống Gateway Telegram tích hợp một bộ lọc cơ học tự động quét đầu ra của Coordinator:
- Quét các câu khẳng định hành động điều phối (action mandates / affirmative claims), ví dụ:
  * `"Lệnh đã dispatch thành công..."`
  * `"Đã dispatch Worker..."`
  * `"Đã giao việc cho subagent..."`
  * `"Đã thực thi thành công..."`
- Đối soát cơ học với tập tool calls thực tế phát sinh trong turn hiện tại:
  * BẮT BUỘC phải có biên lai `task_id` hợp lệ được sinh ra từ các công cụ điều phối worker thực thụ (`dispatch_worker.py` hoặc `delegate_task`).
  * Gọi `cronjob(action='run', job_id=...)` CHỈ là lệnh kích hoạt scheduler chạy ngầm, KHÔNG PHẢI là biên lai Worker thi công trực tiếp cho task hiện tại!
- Khi phát hiện lời khẳng định không kèm biên lai hợp lệ:
  * Gateway tự động dán đè nhãn đỏ vào đuôi tin nhắn:
    `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`
    `Lý do: Không tìm thấy task_id hợp lệ của Worker trong lượt này.`

## 2. Cạm Bẫy Phổ Biến & Quy Tắc Phòng Ngừa
1. **Cấm dùng ngôn từ khẳng định khi chỉ trigger CronJob ngầm:**
   - Tuyệt đối KHÔNG tuyên bố `"Đã dispatch thành công"`, `"Lệnh thi công đã chạy"` khi chỉ mới gọi `cronjob(action='run')` hoặc lên lịch cron.
   - Bắt buộc nói rõ: *"Đã trigger job cronjob ngầm <job_id>, tiến trình chạy bất đồng bộ theo scheduler và chưa có subagent/worker nào chạy trực tiếp trong turn này."*
2. **Phân biệt rạch ròi giữa Worker Execution vs Scheduler Trigger:**
   - Worker execution: Có `task_id`, có stdin/stdout trực tiếp, có diff kiểm chứng, có receipt ghi nhận.
   - Scheduler trigger: Chỉ gửi tín hiệu đánh thức tiến trình nền, không có worker receipt trong phiên chat.
3. **Khi bị dán nhãn bóc mẽ:**
   - Bắt buộc nhận lỗi thẳng thắn, đối soát nguyên nhân Gateway hook, cấm bao biện lòng vòng hoặc nói mồm.
