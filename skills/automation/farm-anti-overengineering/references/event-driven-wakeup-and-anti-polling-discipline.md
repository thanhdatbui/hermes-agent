# Kỷ luật Chống Polling Tiến trình Nền (Event-Driven Wakeup & Zero Context Bloat)

*Ngày ghi nhận: 24/09/2026*  
*Nguồn gốc: Kỹ thuật OMP Harness của Can Bölük (@_can1357), tư vấn kiến trúc từ Claude CLI và thẩm định chuyên sâu từ Claude Opus.*

---

## 1. Bản chất Vấn đề & Anti-Pattern Cần Triệt Tiêu
- **Thói quen xấu của LLM:** Khi chạy các tác vụ tốn thời gian (batch render video, upload TikTok hàng loạt, batch reg mail, DB sync, test suite), agent thường tự động sinh vòng lặp polling: `sleep 10 && ps`, `while kill -0 $PID; do sleep 5; done` hoặc liên tục gọi lệnh check trạng thái.
- **Hậu quả nghiêm trọng:** Mặc dù `sleep` không tốn CPU máy chủ, nhưng **mỗi lần polling là một LLM turn mới**. Toàn bộ context history (20k - 100k+ tokens) phải gửi lại lên API. Dù có prompt cache, chi phí token tích lũy, độ trễ và nguy cơ gây nghẽn slot vẫn tăng vọt, dẫn đến **Context Bloat** (nguyên nhân hàng đầu gây lag, chậm session).
- **Cơ chế Event-Driven của Harness:** Harness hiện đại (như Hermes Agent) vốn có cơ chế thông báo nền:
  1. `terminal(background=True, notify_on_complete=True, timeout=...)`: Chạy ngầm và tự động inject kết quả vào chat để đánh thức (wake-up) agent khi hoàn thành.
  2. `delegate_task(...)`: Dispatch worker subagent chạy background độc lập, tự động trả báo cáo khi kết thúc mà không cần polling.

---

## 2. Bốn Kẽ Hở & Cạm Bẫy Lớn (Audit từ Claude Opus)

Khi triển khai quy tắc cấm polling, Claude Opus thẩm định và chỉ ra 4 lỗ hổng tinh vi cần phòng vệ:

1. **Polling trá hình qua Self-Wakeup / Cron ngắn hạn:**
   - *Lỗ hổng:* Model không dùng `sleep` nhưng tự đặt lệnh `ScheduleWakeup` hoặc cron 60s để "ngó" tiến trình mà harness vốn đã theo dõi bằng `notify_on_complete`.
   - *Biện pháp:* Cấm tuyệt đối đặt self-wakeup / cron ngắn hạn cho bất kỳ tác vụ nào đã có harness theo dõi.
2. **Kẽ hở ngữ từ "liên tục" (Continuous check):**
   - *Lỗ hổng:* Nếu viết "cấm liên tục gọi lệnh check", model sẽ tự bào chữa là *"tôi chỉ check một lần duy nhất"*.
   - *Biện pháp:* Quy định rõ: *"CẤM tự gọi lại lệnh check trạng thái — dù chỉ một lần — thay cho việc chờ notify."*
3. **Thiếu Heuristic chọn Timeout (Nguy cơ Hang / Kill sớm):**
   - *Lỗ hổng:* Nếu để model tự điền `timeout=...` mà không có công thức, model dễ đặt quá ngắn (kill nhầm job) hoặc quên đặt (khiến job hang vĩnh viễn khi gặp lỗi phần cứng).
   - *Biện pháp:* Bắt buộc áp dụng heuristic: `timeout ≥ thời gian ước lượng × 2` (tối thiểu 60s).
4. **Lối thoát hợp lệ khi chờ ngoại vi ngoài band (ADB / Device State):**
   - *Lỗ hổng:* Khi chờ thiết bị Android boot hoặc online mà harness không gắn watcher notify được, nếu cấm tuyệt đối thì model bị kẹt hoặc vi phạm.
   - *Biện pháp:* Cho phép duy nhất 1 lệnh blocking có timeout ở tầng OS/driver (ví dụ: `adb wait-for-device`).

---

## 3. Bất biến Phòng Ngừa Silent Crash (GATE 6)
- **Quy tắc vàng:** Khi nhận tín hiệu wake-up từ harness, **TUYỆT ĐỐI CẤM** suy diễn tiến trình thành công chỉ qua exit code 0.
- **Đặc biệt với ADB:** Lệnh ADB thường xuyên trả về exit code 0 ngay cả khi thiết bị offline, app bị crash văng màn hình hoặc activity không launch được.
- **Hành động bắt buộc:** Phải kiểm tra log thực tế, kiểm tra file output sinh ra và chụp screenshot / OCR thẩm định (GATE 6 Visual Evidence) trước khi kết luận.

---

## 4. Chuẩn hóa Cấu hình Toàn Cục & Cập nhật Fleet
1. **Hermes Coordinator (`config.yaml` - `agent.system_prompt`):**
   Đã bổ sung mục 4 vào System Prompt:
   ```yaml
   4. CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN (EVENT-DRIVEN WAKEUP): CẤM tự viết vòng
   lặp sleep, ps, pgrep, check status chờ tiến trình nền. Tác vụ lâu (>30s) bắt
   buộc dùng terminal(background=True, notify_on_complete=True, timeout=...) hoặc
   delegate_task rồi kết thúc lượt trả lời để harness tự đánh thức. Khi được đánh
   thức, CẤM suy diễn thành công chỉ qua exit code mà phải kiểm tra bằng chứng thực tế (GATE 6).
   ```
2. **Hệ thống 30 repo tại `D:/Taadaa`:**
   Đã append vào cuối 30 file `AGENTS.md` và `PROJECT_RULES.md` theo quy trình bảo toàn EOL byte-exact của skill `rule-file-append`.
3. **Môi trường Claude Code CLI (v2.1.281):**
   - Đã cấu hình model mặc định sang **Claude Opus 5.5** (`claude-opus-5-5`, phát hành 21/09/2026, 1M context, mandatory deep reasoning) trong `~/.claude/settings.json`.
