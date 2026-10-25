# Windows CRLF Line Endings, Diff Bloat & Closeout Gate Pitfalls

## 1. Cơ chế phát sinh lỗi (Root Cause)
- Trên Windows, file git có thể được checkout với CRLF (`\r\n`) do cấu hình `core.autocrlf = true`.
- Khi worker hoặc script Python chạy ghi đè file với LF (`\n`) (hoặc môi trường bash/MSYS ghi LF), toàn bộ các dòng trong file đều bị git tính là thay đổi (line terminator change).
- Dẫn đến diff kích thước thực tế chỉ 15-20 dòng code logic nhưng `git diff` lại báo cáo 400-500 dòng thay đổi (toàn bộ file).
- Hệ quả với Closeout Gate:
  `GATE-FAIL(diff-too-large): [Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (39546 > 30000 bytes, không tính test). Vi phạm quy chuẩn phân rã task O(1). Phải thu hẹp diff trước khi gọi Reviewer.`

## 2. Cách chẩn đoán nhanh O(1)
- Chạy kiểm tra numstat với cờ bỏ qua ký tự kết thúc dòng:
  `git diff --ignore-space-at-eol --numstat <files>`
  - Nếu `--ignore-space-at-eol` chỉ ra số dòng thay đổi thực tế nhỏ (ví dụ 14+ / 7-), trong khi `git diff --numstat` thông thường ra hàng trăm dòng (toàn bộ file), chắc chắn 100% là do lệch chuẩn CRLF vs LF.
- Kiểm tra kiểu kết thúc dòng của file trên disk vs HEAD:
  `head -n 5 <file> | file -`

## 3. Quy trình chuẩn hóa khắc phục dứt điểm
- Đọc file dưới dạng nhị phân và chuẩn hóa lại đúng CRLF:
  ```python
  with open(path, "rb") as f:
      data = f.read()
  data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
  with open(path, "wb") as f:
      f.write(data)
  ```
- Sau khi chạy, kiểm tra lại `git diff --numstat <files>`. Diff sẽ co lại chính xác số dòng logic, vượt qua cổng Diff Size của Closeout Gate an toàn.
