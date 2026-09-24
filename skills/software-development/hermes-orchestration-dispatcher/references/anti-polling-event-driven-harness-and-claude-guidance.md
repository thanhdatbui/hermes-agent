# Anti-Polling Event-Driven Harness Architecture & Claude CLI Guidance (2026-09-24)

References:
- Can Bölük (`@_can1357` — tác giả OMP harness): Kỹ thuật tối ưu system prompt loại bỏ vòng lặp polling, tiết kiệm ~30% chi phí token cho autonomous agent runs.
- Claude Code CLI Architectural Review (2026-09-24): Thẩm định chuyên sâu về tính khả thi, 3 cạm bẫy chí mạng và thiết kế guardrails cho kiến trúc Phone Farm Coordinator / Worker.

---

## 1. Vấn đề cốt lõi (The Agent Polling Anti-Pattern)

Khi thực thi các tác vụ nền tảng hoặc tốn thời gian (batch render video, download proxy, upload TikTok, test suites, database migration...):
- **Thói quen xấu của LLM:** Agent thường tự viết vòng lặp polling thủ công: `sleep 10 && ps`, `while kill -0 $PID; do sleep 5; done` hoặc liên tục gọi tool kiểm tra tiến trình.
- **Hệ quả cấu trúc:** Dù lệnh `sleep` trên terminal không tốn CPU, nhưng **mỗi lần polling là một LLM turn mới**. Toàn bộ context history (20k - 100k+ tokens gồm toàn bộ prompt, rules, tools, chat) phải gửi lại API. Dù có prompt cache hit thì chi phí token tích lũy, latency và rủi ro gây tắc nghẽn slot vẫn tăng vọt, gây **Context Bloat** (nguyên nhân gây lag và tràn context session).

---

## 2. Giải pháp 1 dòng Directive của Can Bölük (OMP Harness)

Thay vì để agent polling, harness hiện đại đã hỗ trợ cơ chế Event-driven Wakeup (tự động inject kết quả vào context và đánh thức agent khi tiến trình kết thúc).
Can Bölük bổ sung 1 dòng directive chuẩn vào system prompt:

```text
"Long foreground calls may auto-background by the configured threshold; the result is injected as a follow-up when the job finishes. NEVER poll a backgrounded job (sleep / ps / pgrep / top) - do other work or end your reply and you will be woken with its output."
```
-> Kết quả: Giảm ngay **~30% chi phí token** trong các tác vụ fully-autonomous.

---

## 3. Thẩm định từ Claude Code CLI cho Taadaa Phone Farm

### 3.1. Tính khả thi & Lợi ích
- **Đặc biệt phù hợp:** Hệ thống Taadaa Farm có hàng loạt tác vụ nền nặng (render video ffmpeg 30-120s, download proxy 20w, batch upload TikTok, batch reg...).
- **Tiết kiệm >30%:** Nếu Coordinator điều phối nhiều worker/tiến trình song song, việc loại bỏ polling nhân hệ số tiết kiệm theo số lượng worker/task.

### 3.2. Ba cạm bẫy chí mạng (Critical Pitfalls) & Giải pháp

| Cạm bẫy | Nguy cơ | Giải pháp bắt buộc |
|---|---|---|
| **1. Silent Hang / Mất Timeout** | Tác vụ nền hoặc thiết bị Android bị freeze/kẹt không bao giờ kết thúc. Không có polling $\rightarrow$ không có wakeup $\rightarrow$ Agent bị kẹt im lặng vĩnh viễn. | **BẮT BUỘC gán timeout cứng** cho mọi background task (`terminal(background=True, timeout=...)`). Tuyệt đối cấm chạy nền không giới hạn thời gian. |
| **2. Silent Crash / ADB Exit 0 giả mạo** | Lệnh ADB hoặc script con trả về exit code 0 nhưng app bên trong bị crash, device offline hoặc văng màn hình. Agent nhận wakeup tưởng xong việc $\rightarrow$ suy luận sai. | **CẤM tin tưởng tuyệt đối vào exit code 0**. Bắt buộc tuân thủ **GATE 6 & Visual Evidence**: đọc file output manifest, kiểm tra screenshot thật (`MEDIA:`), chạy OCR verification trước khi kết luận. |
| **3. Wakeup Storm** | 20 worker hoàn thành cùng lúc trong 30s $\rightarrow$ 20 event dồn dập đổ vào Coordinator trong 1 phút làm context bùng nổ. | **Worker Batch Aggregation**: Cho các batch lớn, gom kết quả thành batch report hoặc để subagent tổng hợp xong mới báo cáo 1 lần về Coordinator. |

---

## 4. Chuẩn hóa áp dụng vào Hermes Agent

### 4.1. Directive đưa vào System Prompt / Rules:
```yaml
# Chống Polling gây lãng phí Token & Kẹt Context:
- CẤM TUYỆT ĐỐI POLLING TIẾN TRÌNH NỀN: Cấm tự viết vòng lặp sleep, ps, pgrep, top hoặc check status liên tục.
- MỌI TÁC VỤ DÀI (>30s): Bắt buộc dùng `terminal(background=True, notify_on_complete=True, timeout=...)` hoặc dispatch qua `delegate_task`.
- KHI ĐÃ BACKGROUND/DISPATCH: Kết thúc lượt trả lời ngay hoặc thực hiện việc độc lập khác. Harness sẽ tự động đánh thức (wake-up) khi tác vụ hoàn thành.
- PHÒNG NGỪA SILENT CRASH: Khi nhận tín hiệu wake-up, KHÔNG ĐƯỢC tin tưởng 100% vào exit code; bắt buộc kiểm tra output thực tế / log / screenshot (GATE 6) trước khi kết luận.
```

### 4.2. Nguyên tắc vận hành Coordinator:
1. Khi dispatch `delegate_task`: Gửi Dispatch Receipt ngắn gọn rồi kết thúc lượt, KHÔNG chờ đợi polling.
2. Khi chạy terminal script nền: Bắt buộc kèm `timeout` và `notify_on_complete=True`.
3. Khi nhận wakeup: Verify artifact thật trước khi báo cáo thành công cho User.
