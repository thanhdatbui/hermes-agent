# User Override Push & Sol Reviewer Boundary Scoring (2026-10-15)

## 1. Cơ chế User Override Bypass Pre-Push Hook (`--no-verify`)

### Bối cảnh & Vấn đề
Khi chốt phiên (`session-close-protocol`), repo farm cài đặt hook `.git/hooks/pre-push` (`INC-HERMES-2026-001`) kiểm tra `gate_audit.jsonl`. Nếu chưa có verdict `APPROVED (Score >= 85)`, pre-push hook sẽ exit 1 và chặn mọi lệnh `git push` thông thường:
```
❌ [BLOCKED - PRE-PUSH HOOK]: Gate check FAILED — Không tìm thấy bản ghi Closeout Gate APPROVED >= 85 cho commit hiện tại!
```

### Phương thức Bypass khi User yêu cầu rõ ràng
Khi User phát lệnh rõ ràng cho phép bỏ qua Gate để push ngay ("push luôn đi khỏi qua sol", "cho phép push không cần qua gate"):
- CẤM Agent tự tiện bypass khi chưa có chỉ thị từ User.
- KHI ĐÃ CÓ CHỈ THỊ TRỰC TIẾP CỦA USER: Dùng `safe_push.py` chuyển tiếp cờ `--no-verify` tới git:
  ```bash
  python D:/Taadaa/tools/safe_push.py "<repo_path>" origin <branch> -- --no-verify
  ```
  `safe_push.py` lọc bỏ các biến sandbox (`GIT_ALLOW_PROTOCOL`, `GIT_CONFIG_*`) nhưng chuyển toàn bộ tham số sau `--` vào lệnh `git push`, giúp bỏ qua hook pre-push và hoàn tất commit lên remote repository ngay lập tức.

---

## 2. Sol Reviewer Scoring: Subsecond Capping & Truncation

### Nguyên nhân kẹt điểm (Score 72 - 82):
1. **Truncation do test suite dài:** Khi file test phình to (>300 dòng), `sol_payload_guard` tự động cắt tỉa (~40% test code bị lược). Reviewer Sol lập tức trừ điểm vì "không thể xác minh 100% test do bị truncate".
   - **Giải pháp:** Viết test tập trung, súc tích, tái sử dụng fixture; giữ tổng diff toàn bộ commit < 15,000 bytes.
2. **Thiếu bằng chứng SQLite thực tế:**
   - Đối với các fix liên quan đến định dạng thời gian (`%Y-%m-%d %H:%M:%S`), Sol đòi hỏi bằng chứng toán tử so sánh chuỗi (`WHERE timestamp <= ?`) trên SQLite thật để chứng minh tính đúng đắn.
   - Thêm integration test với SQLite database thật trong `tests/` để tăng điểm Logic & Test Evidence lên mức tối đa.
3. **Telemetry & Observability:**
   - Khi fix edge-case (ví dụ subsecond capping), bắt buộc bổ sung metric tương ứng (`subsecond_capped`) và log rõ ràng để đạt điểm Telemetry >= 13/15.

---

## 3. Quản lý Ngân sách Coordinator T1 (200 dòng)
- Coordinator chỉ có ngân sách T1 sửa trực tiếp <= 200 dòng cộng dồn cả session.
- Khi vượt quá 200 dòng, Guard chặn cứng: `[COORDINATOR WRITE DENIED]`.
- Lúc này, bàn giao toàn bộ việc sửa code/test cho **Claude CLI** (`claude -p "..."`) theo cơ chế **Strike 3 Reviewer Hand-off** hoặc Worker qua `delegate_task`.
