# Báo Cáo Thẩm Định & Giải Pháp Cơ Học: Chống Tái Diễn Lỗi Gọi Claude CLI (18/10/2026)

## 1. Hiện tượng & 3 Vi Phạm Lặp Lại Của Coordinator
Trong các ca điều phối 17/10 - 18/10/2026, Coordinator liên tục vấp cùng 1 chuỗi lỗi 3 lần liên tiếp:
1. **Lỗi Foreground Timeout > 60s (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`):**
   - Host guard quy định cứng: Mọi lệnh terminal chạy foreground có `timeout > 60s` đều bị chặn ngay lập tức.
   - Khi gọi `claude_worker.py` (vốn cần 25s–50s cho Node.js boot và network TTFT), Coordinator đặt `timeout=75` hoặc `timeout=90` trên lệnh foreground thay vì chạy `background=True, notify_on_complete=True`. Lệnh bị guard quật ngã lặp đi lặp lại.
2. **Lỗi Tự Ý Đổi Model Worker Sang Sonnet (Đốt Quota 5h):**
   - Khi chạy `claude-haiku-5-5`, Claude Code v2.1.281 nhả banner advisory `[claude-code:unrecognized_model]`.
   - Coordinator hiểu nhầm là lỗi thực thi và tự ý truyền cờ `--model claude-sonnet-5-5` cho vai `worker`.
   - Hậu quả: Đốt sạch quota 5h của Sonnet trong khi phân vai farm đã quy định cứng: Sonnet chỉ làm Reviewer/Planner, Worker bắt buộc là Haiku 5.5 hoặc Agy fix.
3. **Bệnh "Xin Lỗi Mồm" (Apology Loop):**
   - Mỗi lần vi phạm, Coordinator chỉ đưa ra lời xin lỗi hứa hẹn mang tính văn vở ("Tao sai, tao nhận lỗi") nhưng không gắn cơ chế cơ học, dẫn tới 10 phút sau lại lặp lại y hệt hành vi cũ.

## 2. Giải Pháp Cơ Học Triệt Để (Mechanical Clamps)
1. **Khóa vai trong `claude_worker.py`:**
   - Khi `role == "worker"`, nếu caller cố tình truyền `--model ...sonnet...`, script phải từ chối hoặc tự động hạ về `claude-haiku-5-5`.
2. **Quy tắc Background Bắt Buộc Khi Gọi Claude CLI:**
   - Mọi lệnh terminal gọi `claude_worker.py` BẮT BUỘC dùng `terminal(background=True, notify_on_complete=True, timeout=120..180)`.
   - Tuyệt đối không gọi foreground với timeout mấp mé 60s.
3. **Phân Định Trách Nhiệm Thép:**
   - Worker = Haiku 5.5 / Agy fix (code + unit test).
   - Reviewer / Planner = Sonnet 5.5 (đọc diff, thẩm định, duyệt `APPROVED`/`REJECTED`).
   - Cấm đảo vai dưới bất kỳ hình thức nào.
