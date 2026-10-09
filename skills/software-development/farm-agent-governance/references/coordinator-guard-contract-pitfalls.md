# Coordinator Delegate-Task Guard Contract Pitfalls (2026-10-05)

## 1. Bẫy `MULTI_FILE_VIOLATION` do lặp file trong `context`
- **Hiện tượng:** Guard báo `MULTI_FILE_VIOLATION: Phát hiện 3 files trong 1 task. Tối đa <= 2 files (1 file nghiệp vụ + 1 file test).`
- **Nguyên nhân:** Regex của Coordinator Guard quét cả `context` lẫn `goal` để trích xuất danh sách file. Nếu đường dẫn file nghiệp vụ xuất hiện trong `context` và lặp lại trong `FILE:` ở `goal`, Guard sẽ đếm trùng thành 2 file riêng biệt, cộng với `TEST_FILE:` thành 3 files!
- **Khắc phục:** Tuyệt đối không viết đường dẫn file `.py` trong `context`. Chỉ khai báo đường dẫn file duy nhất tại `FILE: <đường_dẫn_tuyệt_đối>` và `TEST_FILE: <đường_dẫn_tuyệt_đối>` trong phần `goal`.

## 2. Bẫy `INVESTIGATE_HAS_EDIT_INTENT` do từ cấm trong prompt
- **Hiện tượng:** Khi chạy `TASK_KIND: INVESTIGATE`, Guard chặn lệnh vì phát hiện động từ sửa code.
- **Nguyên nhân:** Regex quét thô các từ như "sửa", "thay", "patch", "chỉnh". Kể cả khi viết "CẤM sửa code" hay "không được sửa file", regex vẫn bắt trúng từ "sửa".
- **Khắc phục:** Dùng từ ngữ trung tính: "chỉ đọc", "kiểm tra", "read-only", "không thay đổi nội dung".

## 3. Bẫy CRLF Line-Endings làm phình Diff trên Windows
- **Hiện tượng:** Sol Reviewer đánh trượt (điểm 81-84/100) vì diff quá lớn (`+880/-878` thay vì `<= 30 dòng`).
- **Nguyên nhân:** Tool ghi file trên Windows vô tình chuyển đổi `\n` thành `\r\n` (CRLF), khiến Git diff nhận diện toàn bộ file bị thay đổi.
- **Khắc phục:** Bắt buộc chuẩn hóa line-endings về LF (`\n`) bằng Python/dos2unix trước khi chạy `closeout_gate.py` để diff trở về O(1) đúng số dòng sửa thực tế.
