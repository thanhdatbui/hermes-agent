# Báo Cáo Đối Soát Độc Lập Claude Sonnet 5.5 & Kỷ Luật Triệt Tiêu Fail-Open Media Gate

## 1. Bối cảnh & Tình huống thực tế
- Ngày 27/10/2026, khi sửa lỗi Media Gate (`guard_media_vision_gate.py`) để giải quyết vấn đề false-positive `INVALID_MEDIA_FILE` (do receipt SHA-256 cũ đè lên ảnh mới), hệ thống suýt vướng vào hai bẫy kiến trúc đối lập:
  1. **Bẫy Over-Engineering:** Giữ nguyên việc so sánh hash SHA-256 và mtime siêu vi (microsecond) với receipt cổ đại từ nhiều ngày trước, gây kẹt ảnh chụp mới toanh (`admin_screen.png`).
  2. **Bẫy Fail-Open nguy hiểm (`EXEMPTION_MARKERS`):** Để tránh gate bắt nhầm tin nhắn nhận việc hay giải trình, đã có lúc bổ sung danh sách miễn trừ văn bản tự do (`EXEMPTION_MARKERS`). Claude Sonnet 5.5 khi được gọi vào đối soát độc lập đã chỉ ra ngay: **Đây là lỗ hổng bypass nghiêm trọng nhất** — Agent có thể tự chèn cụm từ miễn trừ vào văn bản để vô hiệu hóa toàn bộ Gate 6!

## 2. Ý kiến phản biện từ Claude Sonnet 5.5 (Principal Architect)
- **Cảnh báo về EXEMPTION_MARKERS:**
  > *"Nguy cơ bypass lớn nhất: EXEMPTION_MARKERS. Nếu marker này match trên text do agent tự sinh (output message) thay vì cờ hệ thống/tool_call thật trong transcript, agent có thể tự chèn marker để tắt gate — đây là lỗ hổng nghiêm trọng hơn bug gốc, cùng category với các fail-open đã bị REJECTED trước đây."*
- **Cảnh báo về Exception Path & `None` Return:**
  > *"NO_RECEIPT phải map tuyệt đối về BLOCK — nếu có bất kỳ nhánh exception/default nào rơi về pass-through (do code mới refactor TTL logic), thì đây lại là fail-open class bug."*

## 3. Kiến trúc chuẩn hóa đã chốt thống nhất
1. **Triệt tiêu 100% `EXEMPTION_MARKERS` (Zero Text-based Bypass):**
   - Đã xóa bỏ hoàn toàn biến `EXEMPTION_MARKERS` khỏi mã nguồn `guard_media_vision_gate.py`.
   - Gate 6 chỉ miễn trừ khi `is_ui_turn(tool_calls)` là `False` (dựa trên danh sách công cụ thực thi thực tế trong transcript, không dựa vào lời nói tự do của Agent).
2. **Cơ chế Fail-Closed Tuyệt Đối 2 Bước Cho `MEDIA:<path>`:**
   - **Bước 1 (Vật lý file):** Gọi `_media_file_verdict(path)`. Nếu file không tồn tại, rỗng hoặc không đọc được $\rightarrow$ Trả về `INVALID_MEDIA_FILE` (FAIL-CLOSED ngay lập tức). Nếu file nguyên vẹn $\rightarrow$ Trả về `None` để chuyển sang bước 2.
   - **Bước 2 (Kiểm tra vé soi mắt):** Gọi `check_contradiction(...)`. Nếu không có receipt hợp lệ trong TTL 300s (nghĩa là Agent chưa từng mở ảnh ra soi mắt bằng `browser_vision` hay `run_winrt_ocr`) $\rightarrow$ Trả về `NO_RECEIPT` (`passed: False`) và chặn đứng tin nhắn. Tuyệt đối không có đường lách nào!
3. **Phân biệt Visual vs Text Claims:**
   - Ảnh đồ họa / proposal / canvas / avatar / thiên nhiên bắt buộc phải có `tool_called="browser_vision"` (soi mắt thật). Cấm dùng OCR text thô để bảo lãnh.
4. **Quy trình đăng nhập Claude CLI (Interactive TTY):**
   - Lệnh `claude auth login` là lệnh tương tác trực tiếp (TTY/browser popup). Khi chạy ngầm từ subshell tự động của Agent sẽ bị lỗi timeout OAuth.
   - Khi token hết hạn, Agent phải báo User mở terminal ngoài gõ `claude auth login` để xác thực qua trình duyệt thay vì cố spawn tiến trình ngầm gây kẹt.
