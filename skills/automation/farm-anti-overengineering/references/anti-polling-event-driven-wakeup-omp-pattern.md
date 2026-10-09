# Kỷ luật Chống Polling Tiến trình nền & Event-Driven Wakeup (OMP / Can Bölük Pattern & Claude Opus 4.8 Audit)

Ngày cập nhật: 24/09/2026

## 1. Bản chất & Nguồn gốc (Can Bölük @_can1357 / OMP Harness)
- **Vấn đề (Anti-pattern của LLM Agent):** Khi thực thi tác vụ dài (>30s như render, upload, batch reg, test suite, DB sync), LLM có thiên hướng tự chạy vòng lặp polling: `sleep 10 && ps`, `while kill -0 $PID; do sleep 5; done` hoặc liên tục gọi lệnh check trạng thái.
- **Tác hại:** Mỗi lần polling là 1 lượt gọi LLM mới, harness phải gửi lại toàn bộ prompt + rules + context history lên server API. Dù có prompt cache, chi phí tích lũy token và độ trễ vẫn tăng vọt, gây phình context (context bloat) và làm lag/treo session.
- **Giải pháp Event-driven Wakeup:** Tận dụng cơ chế chạy ngầm có thông báo của harness (`terminal(background=True, notify_on_complete=True, timeout=...)` hoặc `delegate_task`). Khi tiến trình hoàn thành, harness tự động inject output vào session để đánh thức agent.

## 2. Thẩm định & Các lỗ hổng phát hiện bởi Claude Opus 4.8 (Score: 79/100)
Trong phiên review ngày 24/09/2026, Claude Opus 4.8 chỉ ra 4 lỗ hổng tinh vi cần bịt:

1. **Lỗ hổng Polling trá hình qua Self-wakeup:** Model bị cấm `sleep` nhưng lách luật bằng cách tự lên lịch wakeup/cron ngắn hạn (ví dụ mỗi 60s) để "ngó" tiến trình mà harness vốn đã theo dõi. 
   - *Khắc phục:* CẤM TUYỆT ĐỐI tự đặt wakeup ngắn hạn cho job đã có `notify_on_complete`.
2. **Kẽ hở từ ngữ "liên tục":** Từ "liên tục gọi lệnh check" khiến model tự bào chữa là *"tôi chỉ check 1 lần rồi thôi"*.
   - *Khắc phục:* Sửa thành: "CẤM tự gọi lại lệnh check trạng thái — dù chỉ một lần — thay cho việc chờ notify."
3. **Heuristic chọn Timeout:** Để trống `timeout=...` khiến LLM đặt timeout quá ngắn (kill nhầm tiến trình đang chạy bình thường) hoặc bỏ trống gây kẹt vĩnh viễn nếu tiến trình bị treo.
   - *Khắc phục:* Quy định cứng: `timeout ≥ thời gian ước lượng × 2`, tối thiểu 60s.
4. **Lối thoát khi chờ thiết bị ngoại vi ngoài band:** Khi cần chờ thiết bị Android boot/online mà harness không thể gắn `notify_on_complete`.
   - *Khắc phục:* Dùng đúng 1 lệnh blocking có timeout của subsystem (ví dụ: `adb wait-for-device`).
5. **Phòng ngừa Silent Crash (GATE 6):** Khi nhận tín hiệu wake-up, TUYỆT ĐỐI CẤM suy diễn thành công chỉ qua exit code (đặc biệt là lệnh ADB hay trả về 0 dù app văng hoặc device offline). BẮT BUỘC kiểm tra log và screenshot bằng chứng thực tế trước khi kết luận.

## 3. Bản Rule Chuẩn hóa Production-Hardened (90+/100)
```markdown
## Kỷ luật chống Polling tiến trình nền (Event-driven Wakeup & Zero Context Bloat)
- CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN: Cấm tự viết vòng lặp `sleep`, `ps`, `pgrep`, `top` hoặc tự gọi lại lệnh check trạng thái — dù chỉ 1 lần — thay cho việc chờ notify. CẤM đặt wakeup/cron ngắn hạn để "canh" job đã có harness theo dõi.
- MỌI TÁC VỤ CHẠY LÂU (>30s hoặc không chắc thời lượng): BẮT BUỘC chạy ngầm qua `terminal(background=True, notify_on_complete=True, timeout=...)` với `timeout ≥ ước lượng × 2` (tối thiểu 60s) hoặc dispatch qua `delegate_task`.
- KHI ĐÃ BACKGROUND/DISPATCH: Dispatch hết toàn bộ các việc độc lập rồi kết thúc lượt trả lời để nhường event loop; harness sẽ tự động inject output đánh thức khi hoàn tất. Trường hợp bắt buộc chờ ngoại vi ngoài band: CHỈ dùng 1 lệnh blocking có timeout (như `adb wait-for-device`).
- PHÒNG NGỪA SILENT CRASH (GATE 6): Khi harness đánh thức sau tác vụ nền, TUYỆT ĐỐI CẤM suy diễn thành công chỉ qua exit code (đặc biệt là lệnh ADB). BẮT BUỘC kiểm tra log và screenshot bằng chứng thực tế trước khi kết luận.
```
