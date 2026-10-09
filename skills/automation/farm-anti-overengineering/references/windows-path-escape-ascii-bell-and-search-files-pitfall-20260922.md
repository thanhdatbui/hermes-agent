# Pitfall: Windows Path Escape (`\a` -> ASCII Bell `\x07`) & `search_files` MSYS Failure (22/09/2026)

## 1. Triệu chứng & Bẫy thoát chuỗi ký tự Python (`\a`)
- Trong code Python trên Windows, khi định nghĩa đường dẫn không dùng raw string `r"..."` hoặc double backslash `\\`:
  Ví dụ: `"D:\Taadaa\automation-core\src"`
- Ký tự `\a` bị Python parse thành ASCII Bell (byte `\x07`), dẫn tới đường dẫn thực tế bị méo thành `D:\Taadaa\x07utomation-core\src`.
- **Hệ quả khi patch/anchor**:
  - Tìm kiếm string literal `"D:\Taadaa\automation-core\src"` sẽ KHÔNG MATCH vì trong file thực tế là `\x07`.
  - Phải kiểm tra bằng repr/binary (`b'\x07'`) hoặc đọc trực tiếp từng dòng để lấy exact anchor.
  - Chuẩn hoá bắt buộc: Luôn viết `r"D:\Taadaa\automation-core\src"` hoặc forward slashes `D:/Taadaa/automation-core/src`.

## 2. Bẫy `search_files` trên Windows / MSYS path
- Gọi `search_files` với `path: "C:/Users/Kibe/..."` hoặc `path: "D:/Taadaa/..."` có thể văng lỗi:
  `Search failed: rg: /c/Users/...: IO error for operation on /c/Users/...: The system cannot find the path specified. (os error 3)`.
- **Giải pháp**:
  - Dùng `read_file` trực tiếp với đường dẫn Windows backslash: `C:\Users\Kibe\...` hoặc `D:\Taadaa\...`.
  - Không tốn budget chạy `search_files` khi user đã chỉ định rõ tên file và thư mục gốc; hãy truy cập thẳng file bằng `read_file` để kiểm tra anchor.

## 3. Kỷ luật bảo toàn budget tool call (<= 8 calls)
- Không dùng tool recursive search (`os.walk` qua `terminal` trên cả cây thư mục `D:\Taadaa`) vì sẽ timeout (180s) và nuốt trọn số lượt gọi cho phép.
- Trình tự chuẩn:
  1. `read_file` (đọc đúng vùng offset nghi vấn theo dòng).
  2. `patch` (thay thế old_string -> new_string).
  3. `terminal` chạy test kiểm chứng.
