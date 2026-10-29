# Windows Atomic Workbook Overengineering & Lock Pitfalls (2026-10-29)

## Bối Cảnh & Vấn Đề
Trong các tác vụ ghi dữ liệu tự động của farm (như TikTok Add 2FA batch lưu khóa TOTP vào Master Excel trên ổ `D:`), hệ thống thường xuyên bị treo hoặc văng lỗi giả mạo khiến toàn bộ batch ban đêm bị liệt dù thiết bị vật lý đã hoàn tất công việc.

Qua audit độc lập cùng Claude CLI, phát hiện 5 bẫy over-engineering và lỗi hệ điều hành Windows điển hình:

---

## 1. Bẫy Băm SHA-256 Quá Tay (`WORKBOOK_PROTECTED_PART_DRIFT`)
- **Triệu chứng:** Điện thoại nạp 2FA thành công, nhưng khi lưu vào Excel thì ném ngoại lệ `WorkbookError: WORKBOOK_PROTECTED_PART_DRIFT`.
- **Nguyên nhân:** Hàm `protected_zip_parts()` băm SHA-256 các file bên trong file nén `.xlsx`, bao gồm cả `xl/sharedstrings.xml`. Trong chuẩn OpenXML, khi openpyxl ghi bất kỳ chuỗi text mới nào, file `sharedstrings.xml` bắt buộc phải thay đổi nội dung.
- **Khắc phục:** 
  - Gỡ bỏ `xl/sharedstrings.xml` khỏi hàm `protected_zip_parts()`. Chỉ băm bảo vệ drawings, charts, tables, media và worksheet relationships.
  - Khi ghi text cell đơn thuần, truyền `protected_parts=None` vì bước `verify` sau commit đã kiểm tra trực tiếp giá trị ô cell.

---

## 2. Bẫy Lệch Ổ Đĩa Trên Windows (Cross-Drive `os.replace` Failure)
- **Triệu chứng:** Giao dịch rollback thất bại với `WORKBOOK_VERIFY_ROLLBACK_FAILED` hoặc `OSError: [WinError 17] The system cannot move the file to a different disk drive`.
- **Nguyên nhân:** File rollback hoặc temp file được tạo bằng `tempfile.NamedTemporaryFile()` mặc định nằm trong `%TEMP%` (ổ `C:`), trong khi dữ liệu workbook nằm ở ổ `D:`. Trên Windows, lệnh nguyên tử `os.replace` không thể di chuyển file xuyên volume.
- **Khắc phục:** Bắt buộc truyền `dir=target.parent` khi tạo rollback/temp file để đảm bảo nằm cùng phân vùng ổ đĩa với workbook.

---

## 3. Bẫy Rò Rỉ File Lock Do Windows `SharingViolation`
- **Triệu chứng:** Một process bị crash hoặc restart để lại file lock, các process sau đó bị timeout 120s vĩnh viễn dù process cũ đã chết.
- **Nguyên nhân:** Khi process chủ gọi `unlink()` trên file JSON lock, nếu đúng lúc đó một waiter khác đang mở file để đọc JSON kiểm tra stale owner (`read_text()`), Windows sẽ khóa file và ném `PermissionError / OSError [WinError 32] SharingViolation`. Nếu `unlink()` nuốt lỗi này, file lock sẽ tồn tại vĩnh viễn (leak lock).
- **Khắc phục:** Cài đặt hàm `_unlink_with_retry(path, retries=5, delay=0.05)` để thử lại việc xóa file lock sau khi waiter nhả file handle. Xử lý file lock rỗng/hỏng cũ hơn 30s coi như stale và xóa an toàn.

---

## 4. Vòng Lặp Retry Lồng Nhau Gây Treo Hệ Thống 10 Phút
- **Triệu chứng:** Một máy con ghi Excel bị kẹt làm treo cứng cả tiến trình điều phối (Coordinator), gateway bị ngắt kết nối.
- **Nguyên nhân:** Trong hàm `_write_cell`, code lồng một vòng lặp 5 lần thử lại bên ngoài, mỗi lần lại gọi `single_writer_workbook_update` với timeout 120s bên trong lock. Khi có xung đột lock, thời gian treo nhân lên thành `5 * 120s = 600s` (10 phút).
- **Khắc phục:** Xóa bỏ toàn bộ vòng lặp outer retry và các helper phân loại lỗi transient thừa thãi. Chỉ dùng đúng 1 lần gọi atomic duy nhất với timeout lock hợp lý (60s–120s). Tầng lock acquisition đã có sẵn jitter backoff xử lý tranh chấp.

---

## 5. Bẫy Formula Injection Khi Ghi Mật Khẩu Chứa Dấu `=`
- **Triệu chứng:** Ô PASS hoặc 2FA trong Excel hiển thị lỗi `#NAME?`.
- **Nguyên nhân:** Khi chuỗi bắt đầu bằng dấu `=`, openpyxl tự động gán kiểu dữ liệu là Formula (`f`).
- **Khắc phục:** Đặt rõ ràng `cell.data_type = "s"` trước khi lưu để openpyxl luôn xử lý chuỗi dưới dạng String thuần túy.
