# MSYS Git Diff External Bypassing & Multi-Commit Closeout Gate Discipline

## 1. Lỗi 'error: cannot spawn: No such file or directory' khi chạy git diff
### Triệu chứng
Trên môi trường Windows với git-bash / MSYS, khi chạy:
```bash
git diff <file>
```
Lệnh có thể gặp lỗi crash:
```
error: cannot spawn : No such file or directory
fatal: external diff died, stopping at <file>
```

### Nguyên nhân
Git configuration hoặc biến môi trường `GIT_EXTERNAL_DIFF` đang trỏ vào một trình diff ngoài không tồn tại hoặc đường dẫn rỗng (ví dụ cấu hình diff tool bên thứ ba bị gỡ hoặc sai path MSYS vs Windows native).

### Giải pháp chuẩn hóa
Luôn truyền cờ `--no-ext-diff` khi chạy lệnh diff kiểm tra:
```bash
git --no-pager diff --no-ext-diff <file>
```
Cờ `--no-ext-diff` buộc git sử dụng engine diff nội bộ tích hợp sẵn của git, bỏ qua mọi cấu hình `diff.external` bên ngoài.

---

## 2. Kỷ Luật Đối Soát Base Commit Trước Khi Chạy Closeout Gate
### Triệu chứng & Rủi ro
Khi session trải qua nhiều bước sửa (ví dụ commit sửa code `cdb0836` rồi sau đó commit thêm test `1e53bde`), nhánh làm việc đang đi trước `origin/master` nhiều hơn 1 commit (`ahead of 'origin/master' by 2 commits`).
Nếu chạy:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo <path> --base HEAD~1 ...
```
Thì `closeout_gate.py` chỉ trích xuất diff giữa `HEAD~1..HEAD` (tức chỉ có file test), bỏ sót toàn bộ code logic của commit trước đó. Sol Reviewer sẽ đánh giá thiếu bối cảnh hoặc chấm điểm sai lệch do không thấy code thực thi.

### Quy trình chuẩn hóa
1. **Kiểm tra số lượng commit ahead:**
   ```bash
   git status
   # Hoặc: git rev-list --count origin/master..HEAD
   ```
2. **Hợp nhất thành 1 commit duy nhất (Squash / Soft Reset):**
   Nếu có $\ge 2$ commits thuộc cùng một task phiên làm việc:
   ```bash
   git reset --soft origin/master
   git add <các file đã sửa và test>
   git commit -m "fix(<scope>): <nội dung tổng quát kèm test suite>"
   ```
3. **Hoặc trỏ base chính xác:**
   Dùng `--base origin/master` thay vì `--base HEAD~1` để bảo đảm toàn bộ diff của phiên được reviewer thẩm định đầy đủ:
   ```bash
   python D:/Taadaa/tools/closeout_gate.py --repo <path> --base origin/master --json-output --push
   ```

---

## 3. Khởi Chạy Closeout Gate Bằng Background Process (Chống Foreground Timeout)
### Bối cảnh
`closeout_gate.py` thực hiện chuỗi hành động:
1. Sanitization & git diff extraction.
2. Chạy full bộ focused pytest trong repo.
3. Gửi payload sang Sol Reviewer qua OmniRoute `:20129` và đợi streaming/phân tích.
4. Auto-push via `safe_push.py` khi verdict APPROVED $\ge 85$.

Tổng thời gian thực thi thường dao động từ 45s đến 180s. Nếu chạy foreground trong terminal có timeout chặt (<60s), lệnh sẽ bị ngắt giữa chừng.

### Mẫu lệnh bắt buộc
Coordinator bắt buộc khởi chạy ở background với `notify_on_complete=True` và timeout tối thiểu 300s:
```python
terminal(
    command='python D:/Taadaa/tools/closeout_gate.py --repo "<path>" --base HEAD~1 --json-output --push',
    background=True,
    notify_on_complete=True,
    timeout=300,
    workdir="<path>"
)
```
Sau đó báo cáo ngắn gọn trạng thái commit và mã tiến trình nền cho User, kết thúc lượt để harness tự đánh thức khi reviewer hoàn tất.
