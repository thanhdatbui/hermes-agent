# Strike 3 Reviewer Hand-off qua Claude CLI

## 1. Cơ Chế Kích Hoạt Signal
- **Điều kiện:** Khi `closeout_gate.py` chạy qua 3 lần rejection liên tiếp trên cùng `scope_hash` (`count_consecutive_rejections >= 3`).
- **Tín hiệu:** Cổng in thông báo ra stderr:
  `[REVIEWER_HANDOFF_TRIGGERED: N consecutive rejections reached for scope_hash=... Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Claude CLI) to self-remediate, strictly scoped to: <files>]`
- **Mã thoát (Exit Code):** Vẫn là `1` (đây là tín hiệu điều phối, không phải trạng thái thành công).

## 2. Kỷ Luật Điều Phối Của Coordinator
1. **DỪNG TẤT CẢ các nỗ lực patch mò mẫm:** CẢ Coordinator, Worker (Luna/Haiku), và `sol_repair.py` ĐỀU BỊ CẤM tạo patch proposal lần thứ 4.
2. **Kích hoạt Reviewer-with-write-access:** Coordinator gọi trực tiếp Claude CLI với quyền chỉnh sửa hạn chế trong đúng allowlist được freeze tại `audit_binding.scope`.
3. **Lệnh thực thi chuẩn:**
   ```bash
   claude -p "<task spec: finding history + exact allowlist + acceptance command>" \
     --allowedTools "Read,Edit,Write,Bash" \
     --dangerously-skip-permissions \
     --max-turns 15
   ```
   *Lưu ý an toàn:* Cờ `--dangerously-skip-permissions` ĐỘC QUYỀN chỉ được cấp cho luồng hand-off này và trên đúng danh sách file trong allowlist đã chốt.

## 3. Nội Dung Task Spec Cho Claude CLI
- **Lịch sử Finding của Reviewer:** Nêu rõ các điểm trừ cụ thể mà Reviewer vừa chấm (ví dụ: code duplication giữa script gốc và bản cron, noise blank lines, test numbering nhảy cóc, test logic query window khi end=None, thiếu thread-safety / auto_reset test).
- **Phạm vi Allowlist đông kết:** Liệt kê chính xác các file được phép sửa (thường là file source + bản copy cron + file test).
- **Trần kích thước diff:** Nhắc Claude CLI giữ tổng `git diff` so với base `< 28,000 bytes` (dưới trần 30,000 bytes của closeout gate).
- **Lệnh nghiệm thu (Acceptance command):** Ví dụ `python -m pytest tests/test_feed_session_watchdog.py -q`.

## 4. Hành Vi Của Claude CLI & Chốt Phiên
- Claude CLI tự đọc source code, test contract và finding history.
- Tự chỉnh sửa code/test theo chuẩn của chính Reviewer (self-converge nhanh nhất).
- Tự chạy acceptance command kiểm chứng.
- Khi hoàn tất, Coordinator chạy lại `closeout_gate.py --push` để thẩm định và tự động push remote khi verdict `APPROVED (Score >= 85)`.
