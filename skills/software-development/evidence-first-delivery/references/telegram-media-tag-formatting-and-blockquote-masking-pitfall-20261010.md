# Cạm Bẫy Định Dạng Thẻ `MEDIA:` Trong Hermes Gateway & Hiện Tượng Lộ Text Thô Trên Telegram (10/10/2026)

## 1. Hiện Tượng & Phản Ứng Của Người Dùng
- **Hiện tượng**: Agent gọi `browser_vision` / OCR kiểm tra ảnh xong, soạn tin nhắn báo cáo và ghi thẻ:
  ```text
  MEDIA:D:/Taadaa/tmp/m261_profile_proof.png
  ```
  nhưng trên ứng dụng Telegram Desktop của người dùng, ảnh **hoàn toàn không được hiển thị/upload**. Thay vào đó, chuỗi `MEDIA:D:/Taadaa/...` bị in thẳng ra màn hình chat như một dòng chữ thô!
- **Hậu quả**: Người dùng không nhìn thấy hình ảnh thực tế và lập tức bức xúc gay gắt:
  *"Mày gửi hình kiểu l gì vậy ai xem được!"*

---

## 2. Căn Nguyên Kỹ Thuật Trong Mã Nguồn Hermes Gateway (`gateway/platforms/base.py`)
Trong cơ chế trích xuất media của Hermes Gateway:
1. **Bộ lọc vùng bảo vệ (`_mask_protected_spans`)**:
   Trước khi quét tìm các thẻ `MEDIA:<path>` bằng regex, Gateway chạy hàm `_mask_protected_spans` để xóa nội dung trong các khối prose/code ví dụ nhằm tránh gửi nhầm file rác:
   ```python
   # Fenced code blocks: ```...```
   for m in re.finditer(r'```[^\n]*\n.*?```', content, re.DOTALL):
       spans.append((m.start(), m.end()))

   # Inline code: `...`
   for m in re.finditer(r'`[^`\n]+`', content):
       ...

   # Blockquote lines: > at line start
   for m in re.finditer(r'^>.*$', content, re.MULTILINE):
       spans.append((m.start(), m.end()))
   ```
2. **Cơ chế bẫy Blockquote (`^>.*$`)**:
   - Mọi dòng bắt đầu bằng dấu trích dẫn `>` đều bị Gateway thay thế toàn bộ ký tự thành khoảng trắng (` `) trong chuỗi quét `scan_content`!
   - Khi Agent viết nhận xét Vision dạng trích dẫn:
     ```markdown
     > **Xác nhận qua Vision & OCR:**
     > - Profile cá nhân của nick giangkute7973...
     > MEDIA:D:/Taadaa/tmp/m261_profile_proof.png
     ```
     hoặc đặt `MEDIA:` dính sát liền dưới khối trích dẫn khiến parser markdown hiểu chung một block:
     Dòng chứa `MEDIA:` bị biến thành khoảng trắng trong `scan_content`.
   - Kết quả:
     * `extract_media()` tìm không ra thẻ nào -> `media_files = []` -> **Không có file nào được gửi lên Telegram**.
     * Trong tin nhắn văn bản, vì thẻ không nằm trong danh sách media hợp lệ nên Gateway **không xóa chuỗi `MEDIA:...` đi**.
     * Chuỗi `MEDIA:...` bị giữ nguyên và gửi nguyên văn ra chat Telegram như một dòng chữ thô!

3. **Cơ chế bẫy Backslash (`\`) trên Windows**:
   - Nếu đường dẫn file dùng dấu gạch chéo ngược Windows `\`:
     `MEDIA:D:\Taadaa\tmp\screen.png`
     Các cụm ký tự `\t` (trong `\tmp`), `\r` (trong `\runtime`), `\a` (trong `\artifacts`) rất dễ bị trình parser hiểu là escape sequences (`\t` = TAB, `\r` = CR, `\a` = bell).
   - Hậu quả: Đường dẫn bị biến dạng thành file không tồn tại trên đĩa, Gateway âm thầm hủy gửi media.

---

## 3. Quy Tắc Bất Biến Khi Soạn Thẻ `MEDIA:` (Formatting Invariants)

1. **Tuyệt Đối Đặt `MEDIA:` Ngoài Mọi Khối Trích Dẫn (`>`):**
   - CẤM TUYỆT ĐỐI đặt dấu `>` ở đầu dòng chứa `MEDIA:`.
   - CẤM đặt `MEDIA:` dính liền ngay sau dòng trích dẫn `>`. Phải có ít nhất 1 dòng trống phân cách hoàn toàn.
   - Lời bình xác nhận Vision/OCR nên viết bằng văn bản thường hoặc danh sách gạch đầu dòng (`- `), không lạm dụng dấu `>`.

2. **Dòng Độc Lập Riêng Biệt (Standalone Line):**
   - Thẻ `MEDIA:<path>` phải đứng một mình trên một dòng riêng:
     ```text
     Màn hình Hồ sơ cá nhân của nick:
     MEDIA:D:/Taadaa/tmp/m261_profile_proof.png
     ```
   - CẤM bọc trong code fence: ` ```MEDIA:...``` `
   - CẤM bọc trong inline code: ` `MEDIA:...` `
   - CẤM in đậm, in nghiêng: `**MEDIA:...**`

3. **Luôn Luôn Dùng Forward Slash (`/`):**
   - Ngay cả trên hệ điều hành Windows, đường dẫn sau `MEDIA:` bắt buộc phải dùng dấu gạch xuôi:
     - Đúng: `MEDIA:D:/Taadaa/tmp/m261_profile_proof.png`
     - Sai: `MEDIA:D:\Taadaa\tmp\m261_profile_proof.png`
