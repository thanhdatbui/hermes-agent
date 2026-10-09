# Closeout Scope Hygiene and Staged Index Contamination Prevention

## Bối cảnh & Hiện tượng (Pitfall)
Khi chạy `closeout_gate.py` để chốt phiên:
1. `closeout_gate.py` kiểm tra danh sách `--files` (hoặc target candidates) so với **toàn bộ file staged** trong git index:
   ```text
   Failed to extract diff: staged files [...] != --files targets [...]; unstage extras or adjust --files
   ```
2. Nếu các phiên trước hoặc các worker trước vô tình stage dở các file watchdog, file kịch bản hoặc file test khác vào index, Closeout Gate sẽ **từ chối thẩm định** ngay lập tức.
3. Khi bị từ chối, Reviewer không nhận đúng diff, dẫn đến việc đánh giá nhầm hoặc chấm điểm < 85/100 (`REJECTED`).
4. **Sai lầm phổ biến của Coordinator:** Báo `BLOCKED` vội vàng, dừng lại hỏi user hoặc hoảng loạn xin phép unstage, trong khi đây hoàn toàn là vấn đề vệ sinh Git index (index hygiene).

---

## Quy tắc xử lý chuẩn (Standard Remediation Protocol)

### 1. Phân lập Scope rõ ràng trước khi chạy Gate
Trước khi chạy `closeout_gate.py`, bắt buộc kiểm tra xem git index đang chứa những file nào:
```bash
git -C <repo> status --short
```
Hoặc kiểm tra danh sách file staged:
```bash
git -C <repo> diff --cached --name-only
```

### 2. Reset index sạch về HEAD (Unstage All Contaminations)
Khi phát hiện file tồn đọng từ phiên trước hoặc từ các luồng watchdog nền làm ô nhiễm index, thực hiện unstage sạch toàn bộ:
```bash
git -C <repo> reset HEAD
```
Thao tác này hoàn toàn an toàn: nó **không làm mất code** trong working tree (`git status` vẫn giữ nguyên các thay đổi chưa staged).

### 3. Stage chính xác đúng các file thuộc phạm vi phiên hiện tại
Chỉ `git add` đúng các file mà phiên này trực tiếp giải quyết hoặc đã được Sol Plan duyệt:
```bash
git -C <repo> add path/to/target1.py path/to/target2.py
```

### 4. Chạy Closeout Gate với danh sách `--files` trùng khớp 100%
Khi gọi `closeout_gate.py`, truyền đúng danh sách file đã staged:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD --files <target1> <target2> --json-output
```
Đảm bảo invariant:
`set(git diff --cached --name-only) == set(--files targets)`

---

## Kỷ luật ứng xử Coordinator
- **Không được báo BLOCKED giả mạo:** Lỗi lệch staged files là lỗi index cơ học, Coordinator có trách nhiệm tự dùng probe/worker unstage và chuẩn hóa lại index.
- **Không được kết luận "an toàn" hoặc "xong" khi điểm < 85:** Mọi trạng thái Closeout Gate trả về `Verdict: REJECTED` hoặc điểm `< 85` là một active work item, bắt buộc sửa test/code hoặc chuẩn hóa scope cho đến khi đạt `APPROVED` thực sự.
