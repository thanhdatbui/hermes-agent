# CRLF/LF Line-Ending Diff Inflation & Committed Scope Exactness Trap (2026-10-21)

## Hiện Tượng & Triệu Chứng
Khi chạy `closeout_gate.py` trên một repo Windows (`core.autocrlf=false` hoặc repo có mixed line endings như `D:/Taadaa/Tiktok_Reg`):
1. **Lỗi 1 (DIFF_TOO_LARGE Fail-Fast):**
   ```text
   ✘  GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (97128 > 30000 bytes, không tính test). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.
   ```
   Dù kỹ sư/agent chỉ sửa đúng khoảng 10-15 dòng code logic trong file `tiktok_login_v1.py`, nhưng `git diff --numstat` lại hiển thị:
   `1058 insertions(+), 1049 deletions(-)` (toàn bộ file 1049 dòng bị xem là viết lại hoàn toàn).
2. **Lỗi 2 (Committed Scope Mismatch Refusal):**
   ```text
   ✘  Failed to extract diff: committed 2d4952e..HEAD scope ['pytest.ini', 'social_reg_v1.py', 'tests/test_tap_add_account_safe_point.py', 'tiktok_login_v1.py'] != --files targets ['social_reg_v1.py', 'tests/test_tap_add_account_safe_point.py', 'tiktok_login_v1.py']; refusing partial committed scope
   ```

---

## Nguyên Nhân Gốc Rễ (Root Cause)

### 1. Bẫy CRLF vs LF Làm Nổ Diff (Line-Ending Inflation):
- File gốc trên Git remote/HEAD được lưu bằng định dạng LF (`\n`).
- Khi agent chỉnh sửa file bằng các công cụ editor/patch trên môi trường Windows hoặc tạo file mới bằng script Python mặc định viết CRLF (`\r\n`), Git trên Windows với `core.autocrlf=false` nhận diện mọi dòng có ký tự `\r` mới là bị thay đổi.
- Kết quả: Diff text bị phình to từ 1.5 KB lên tới 97.1 KB (vượt xa trần cứng `MAX_DIFF_BYTES_GATE = 30_000` của `closeout_gate.py`).

### 2. Bẫy Khớp Tuyệt Đối Committed Scope (`_committed_scope`):
- Khi chạy `closeout_gate.py` với candidate đã commit (`committed_candidate`), hàm trích xuất diff chạy `git diff --name-only base..HEAD` để lấy danh sách toàn bộ file trong commit.
- Hàm sau đó so sánh tập hợp `committed_files` với tập hợp `targets` (từ tham số `--files`).
- Nếu trong commit có bất kỳ file nào (kể cả file phụ như `pytest.ini` hay file cấu hình/test đã lọt vào commit) không được khai báo trong `--files`, Gate sẽ lập tức từ chối trích xuất diff với lỗi `refusing partial committed scope` nhằm ngăn chặn việc review thiếu file hoặc bypass file rủi ro.

---

## Quy Trình Xử Lý & Kỷ Luật Bắt Buộc

### 1. Phát Hiện Sớm Bẫy EOL (Whitespace Diff Check):
Trước khi chạy closeout hoặc commit, luôn chạy đối soát:
```bash
git diff --numstat
git diff -w --numstat
```
- Nếu `git diff -w --numstat` (bỏ qua whitespace/EOL) chỉ có 10–20 dòng, nhưng `git diff --numstat` hiển thị hàng trăm/nghìn dòng: **ĐÂY LÀ 100% BẪY EOL CRLF/LF**.
- **CẤM COMMIT** khi diff bị nổ dòng do EOL.

### 2. Cách Khắc Phục EOL Sạch O(1):
- Nếu file bị biến thành CRLF: Chuyển lại về LF nguyên bản hoặc revert file rồi chỉ áp dụng thay đổi logic:
  - Nếu file chưa commit: `git checkout origin/main -- <file>` (hoặc khôi phục file gốc) rồi patch lại chính xác bằng LF.
  - Kiểm tra lại định dạng: `file <path>` phải hiển thị `ASCII text` hoặc `UTF-8 text`, KHÔNG được có đuôi `with CRLF line terminators` nếu file gốc trên repo là LF.

### 3. Đồng Nhất 100% Committed Scope Với `--files`:
Khi chạy `closeout_gate.py --repo ... --base HEAD~1 --files ...`:
1. Kiểm tra chính xác các file đã commit trong commit range:
   ```bash
   git diff --name-only HEAD~1..HEAD
   ```
2. Toàn bộ các file xuất hiện trong output trên **BẮT BUỘC PHẢI ĐƯỢC LIỆT KÊ TRỌN VẸN** trong tham số `--files`.
   - Ví dụ: nếu commit có 4 files: `pytest.ini`, `social_reg_v1.py`, `tests/test_tap_add_account_safe_point.py`, `tiktok_login_v1.py`.
   - Thì lệnh gate BẮT BUỘC:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/Tiktok_Reg --base HEAD~1 --files pytest.ini social_reg_v1.py tests/test_tap_add_account_safe_point.py tiktok_login_v1.py --json-output
     ```
   - Thiếu dù chỉ 1 file cũng sẽ bị `refusing partial committed scope`.
