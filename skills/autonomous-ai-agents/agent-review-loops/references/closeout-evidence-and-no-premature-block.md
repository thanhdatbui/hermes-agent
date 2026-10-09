# Closeout Evidence, Staged Scope Isolation, and Quota Failover

## Bối cảnh & Quy tắc ứng xử thực tế
- Khi user báo `Làm lại cho tao` hoặc bức xúc vì agent báo cáo dài dòng, dừng hỏi lựa chọn, hoặc báo `BLOCKED` dù còn đường tự sửa:
  1. Nhận trách nhiệm ngắn gọn rồi làm ngay; không thanh minh dài.
  2. Không báo DONE/an toàn khi Reviewer chưa APPROVED (>=85/100).
  3. Không dùng clarify để đẩy việc lại khi Closeout Gate còn đường remediation cụ thể.

## Cô lập Staged Scope trước Closeout Gate
- `closeout_gate.py` fail-closed khi `staged files != --files targets`.
- Nếu có file staged từ phiên trước: `git reset HEAD`, sau đó `git add <exact_target_files>`, rồi kiểm tra `git diff --cached --name-only` trước khi chạy Gate.
- Scope truyền vào `--files`, staged names và tested tree phải giống hệt; xử lý cả trạng thái `MM` (staged khác working tree).

## Failover khi Claude CLI hết quota
- Với `429/quota exhausted`, không dừng chờ user. Chuyển sang Antigravity hoặc worker subagent qua `delegate_task`, với Patch Contract O(1), OLD_STRING -> NEW_STRING và focused test.
- Sau worker phải chạy lại pytest thật, kiểm tra diff/scope, rồi mới gọi Closeout Gate.

## Reviewer score dưới ngưỡng
- Điểm <85 là remediation item, không phải kết thúc phiên. Đọc findings, bổ sung bằng chứng offline/mock cho đúng nhánh nguy hiểm, re-stage đúng scope và rerun Gate.
- Không mở rộng production code chỉ để làm điểm đẹp; ưu tiên test trực tiếp cho telemetry schema/write failure, equal-mtime conflict/backup, atomic-copy cleanup, GPM/API failure, ADB offline, device-lock contention, dry-run non-deletion.
