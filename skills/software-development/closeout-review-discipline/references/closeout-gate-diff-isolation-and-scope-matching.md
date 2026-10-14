# Cô Lập Diff & Khớp Scope Tuyệt Đối Cho Closeout Gate (Diff Isolation & Scope Matching)

## 1. Cơ Chế Kiểm Soát Diff Của Closeout Gate
`closeout_gate.py` tích hợp 2 chốt chặn bảo vệ nghiêm ngặt ở Bước 2 (Extract Candidate Diff):
1. **Trần dung lượng Diff O(1) (30,000 bytes):**
   Nếu diff vượt quá 30KB, Gate sẽ kích hoạt Fail-Fast ngay lập tức:
   ```text
   GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (N > 30000 bytes).
   Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
   ```
2. **Khớp Scope Tuyệt Đối (`refusing partial committed scope`):**
   Khi dùng `--files <file1> <file2>...`, Gate kiểm tra:
   ```python
   committed_files = git_diff_name_only(base, "HEAD")
   if set(committed_files) != set(target_files):
       raise GateError("refusing partial committed scope")
   ```
   Nghĩa là mọi file được commit trong khoảng `<base>..HEAD` bắt buộc phải nằm trong `--files` và ngược lại. Không được thừa cũng không được thiếu.

---

## 2. Các Cạm Bẫy Phình Diff Nhân Tạo & Cách Phòng Tránh

### Bẫy 1: Commit File Runtime State / Churn Dày Đặc (`jobs.json`, state JSON)
- **Hiện tượng:** Khi sửa logic cron script, Coordinator tiện tay `git add deploy/.../jobs.json`. Tuy nhiên `jobs.json` lưu trạng thái của 50+ cron jobs trên farm (`completed` counter, `last_run_at`, `next_run_at`). Sau 1-2 ngày không commit, diff của `jobs.json` có thể lên tới 35-40KB thuần túy là đổi số timestamp.
- **Hậu quả:** Kéo sập toàn bộ Gate với lỗi `DIFF_TOO_LARGE (60799 > 30000 bytes)`.
- **Kỷ luật:** Cấu hình cron (`jobs.json`) được runtime và cron-sync đồng bộ sang AppData và OneDrive. TUYỆT ĐỐI KHÔNG commit `jobs.json` vào commit code nghiệp vụ của Closeout Gate. Giữ git diff của `jobs.json` = 0.

### Bẫy 2: Lệch Line Endings CRLF vs LF (Windows vs Git-Bash)
- **Hiện tượng:** Trên môi trường Windows, một số công cụ viết file lưu định dạng `\r\n` (CRLF) trong khi Git repo lưu `\n` (LF). Một chỉnh sửa chỉ 1 dòng `assert` trong file test có thể biến thành diff 368 dòng thay đổi toàn bộ file (thêm ~15KB diff vô ích).
- **Phòng tránh:** Luôn kiểm tra `git diff --stat` trước khi commit. Nếu thấy file test tăng hàng trăm dòng bất thường dù chỉ sửa 1-2 dòng, lập tức normalize lại LF trước khi stage.

---

## 3. Bẫy Cron Auto-Commit Xen Ngang Gây Lệch Scope (`partial committed scope`)
- **Hiện tượng:** Cronjob `sync-hermes-skills-and-brain-to-git` chạy định kỳ mỗi 5 phút tự động `git add` và `git commit` các file `MEMORY.md`, `USER.md`, `SKILL.md` lên nhánh `main`.
- Nếu Coordinator commit code xong nhưng chưa kịp chạy Gate ngay, hoặc Gate đang chạy thì cron auto-commit vừa đẩy thêm 1 commit lên đỉnh `HEAD`:
  Khoảng `<base>..HEAD` bỗng nhiên xuất hiện thêm các file bộ nhớ/kỹ năng, khiến Gate từ chối thẩm định vì:
  `committed <base>..HEAD scope [...] != --files targets [...]; refusing partial committed scope`.
- **Quy trình chuẩn hóa khi chốt phiên:**
  1. Tạm dừng cron auto-commit trước khi chốt: `cronjob(action='pause', job_id='7e576815788f')`.
  2. Tạo commit code tinh gọn, chỉ chứa đúng các file code/test mục tiêu.
  3. Chạy `closeout_gate.py` với `--base HEAD~1 --files <đúng_các_file_trong_commit> --push --json-output`.
  4. Sau khi Gate hoàn tất và push xong, resume lại cron: `cronjob(action='resume', job_id='7e576815788f')`.
