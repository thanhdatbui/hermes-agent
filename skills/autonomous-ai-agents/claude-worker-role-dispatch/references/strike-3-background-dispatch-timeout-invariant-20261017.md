# Strike 3 Background Dispatch & Timeout Invariant (2026-10-17)

## 1. Bối cảnh & Cạm bẫy Foreground Timeout
Khi quy trình Closeout Gate trượt 3 lần (Strike 3) và phát tín hiệu `REVIEWER_HANDOFF_TRIGGERED`, Coordinator bắt buộc phải giao quyền can thiệp cho Reviewer (`claude_worker.py --role worker`).

### Sự cố thường gặp:
- Coordinator cố gắng chạy `claude_worker.py` ở chế độ foreground với timeout 55s-60s.
- Hậu quả: Lệnh bị chặn ngay bởi `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` (nếu timeout > 60s) hoặc bị ngắt ngang với `Exit 124: the command hit its timeout` sau 60s. Claude CLI cần tối thiểu 120s - 250s để đọc ngữ cảnh dự án, chạy test suite, suy luận diff, gọi tool patch và kiểm chứng cú pháp.

---

## 2. Kỷ luật Bắt buộc khi Dispatch Claude Worker ở Strike 3 Hand-off

1. **BẮT BUỘC DÙNG TIẾN TRÌNH NỀN (Background Execution):**
   ```python
   terminal(
       command='python D:/Taadaa/tools/claude_worker.py --role worker --workdir "<repo>" --max-turns 10 --timeout 250 "Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files. Sửa các test và telemetry trong <files> theo findings: <findings>..."',
       background=True,
       notify_on_complete=True,
       timeout=300,
       workdir="<repo>"
   )
   ```
2. **Event-Driven Wakeup (Không Polling, Không Ngồi Chờ):**
   Sau khi gọi `terminal(background=True, notify_on_complete=True)`, Coordinator BẮT BUỘC phải nhả lượt trả lời (kết thúc response thông báo cho user).
   Harness sẽ tự động đánh thức Coordinator khi worker hoàn tất (nhận thông báo tiến trình kết thúc kèm exit code).
3. **Bảo vệ Trạng thái Test Pass & Direct Auto-Push:**
   Khi worker thức dậy, chạy lại bộ kiểm tra cơ học (`py_compile`, `pytest`) để nghiệm thu, sau đó tiến hành commit và auto-push bằng `safe_push.py` mà không quay lại Sol High cày điểm.
