# Kỷ luật chống Polling tiến trình nền (Event-driven Wakeup & Zero Context Bloat) — 24/09/2026

## 1. Bối cảnh & Vấn đề (Anti-pattern của LLM)
- Khi thực thi các tác vụ nền kéo dài (>30s như batch render video, download proxy, upload TikTok, migration DB, test suite...), LLM tự nhiên hay viết vòng lặp polling: `sleep 10 && ps`, `while kill -0 $PID; do sleep 5; done` hoặc liên tục gọi lệnh check trạng thái.
- **Hậu quả**: Mỗi lần polling là một turn LLM mới, harness phải gửi lại toàn bộ context/prompt cache lên API. Điều này gây lãng phí 30-50% chi phí token và dẫn đến **Context Bloat** (nguyên nhân gây lag session nghiêm trọng).

## 2. Kỹ thuật của Can Bölük (@_can1357 - Tác giả OMP Harness)
- Harness hiện đại đã hỗ trợ async / background event:
  - `terminal(background=True, notify_on_complete=True, timeout=...)`
  - `delegate_task(...)`
- Directive chuẩn hóa:
  *"NEVER poll a backgrounded job (sleep / ps / pgrep / top) - do other work or end your reply and you will be woken with its output."*
- Giúp giảm ~30% token overhead cho autonomous multi-step tasks.

## 3. Thẩm định độc lập từ Claude Opus 4.8 / 5 (Điểm: 79/100 -> Vá đạt 90+/100)
Claude Opus chỉ ra 4 lỗ hổng tinh vi cần bịt kín khi triển khai:
1. **Polling trá hình qua Self-wakeup**: Model không dùng `sleep` nhưng tự đặt cron/wakeup mỗi 60s để "ngó" job mà harness vốn đã theo dõi notify. → *CẤM tường minh: "Tác vụ đã notify_on_complete thì CẤM tự đặt wakeup ngắn hạn để check".*
2. **Kẽ hở ngữ từ "liên tục"**: Model tự bào chữa *"tôi chỉ check 1 lần"*. → *Sửa thành: "CẤM tự gọi lại lệnh check — dù chỉ 1 lần".*
3. **Heuristic chọn timeout**: Nếu để trống `timeout=...`, model dễ đặt quá ngắn làm kill nhầm job hoặc đặt quá dài. → *Quy định: `timeout ≥ ước lượng × 2`, tối thiểu 60s.*
4. **Lối thoát hợp lệ khi buộc phải chờ ngoại vi**: Khi chờ thiết bị Android boot/online mà harness không notify được, cần chỉ định dùng 1 lệnh blocking có timeout (`adb wait-for-device`) thay vì mò mẫm.
5. **Silent Crash (Gate 6)**: Khi nhận wake-up, CẤM suy diễn thành công chỉ qua exit code (đặc biệt là lệnh ADB hay trả về 0 dù app văng). Bắt buộc verify bằng log và screenshot / OCR thực tế.

## 4. Contract chuẩn hóa đã áp dụng toàn bộ 30 repo và config.yaml
```markdown
## Kỷ luật chống Polling tiến trình nền (Event-driven Wakeup & Zero Context Bloat)
- CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN: Cấm tự viết vòng lặp `sleep`, `ps`, `pgrep`, `top` hoặc tự gọi lại lệnh check trạng thái — dù chỉ 1 lần — thay cho việc chờ notify. CẤM đặt wakeup/cron ngắn hạn để "canh" job đã có harness theo dõi.
- MỌI TÁC VỤ CHẠY LÂU (>30s hoặc không chắc thời lượng): BẮT BUỘC chạy ngầm qua `terminal(background=True, notify_on_complete=True, timeout=...)` với `timeout ≥ ước lượng × 2` (tối thiểu 60s) hoặc dispatch qua `delegate_task`.
- KHI ĐÃ BACKGROUND/DISPATCH: Dispatch hết toàn bộ các việc độc lập rồi kết thúc lượt trả lời để nhường event loop; harness sẽ tự động inject output đánh thức khi hoàn tất. Trường hợp bắt buộc chờ ngoại vi ngoài band: CHỈ dùng 1 lệnh blocking có timeout (như `adb wait-for-device`).
- PHÒNG NGỪA SILENT CRASH (GATE 6): Khi harness đánh thức sau tác vụ nền, TUYỆT ĐỐI CẤM suy diễn thành công chỉ qua exit code (đặc biệt là lệnh ADB). BẮT BUỘC kiểm tra log và screenshot bằng chứng thực tế trước khi kết luận.
```
