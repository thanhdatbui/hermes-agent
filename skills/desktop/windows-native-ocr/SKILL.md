---
name: windows-native-ocr
description: "Extract text from screenshots/JPEG/PNG on Windows using built-in WinRT OCR — zero install, no dependencies."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [OCR, Windows, WinRT, Screenshots, Images]
    related_skills: [ocr-and-documents, pdf, docx]
---
# Windows Native OCR (WinRT)

**Windows 10/11 ships WinRT OCR — no pip install needed.** Works on any Windows machine. Best for screenshots, JPEG, PNG, BMP images (NOT PDFs — see `ocr-and-documents` skill for PDF extraction).

## When to Use

- Input is a screenshot, photo, or image file (JPG/PNG/BMP)
- Need quick text extraction on Windows without installing Tesseract/PaddleOCR/marker-pdf
- The image contains UI text, notifications, dialogs, or web UI elements

## Anti-Pattern: T1 Budget Exhaustion & Consultative Over-Engineering
- **CẤM viết script mới liên tục để OCR ảnh tư vấn**: Khi User gửi ảnh chụp màn hình nhờ tư vấn thao tác/lựa chọn (như form Support, Billing, Option), CẤM Coordinator liên tục dùng `write_file` tạo ra nhiều file `.py`, `.ps1` làm cạn kiệt ngân sách T1 (<= 500 dòng cộng dồn cả session) dẫn tới bị Guard chặn `COORDINATOR WRITE DENIED` và làm treo/delay session.
- **Tái sử dụng hoặc tư vấn trực diện**: Nếu màn hình thuộc dạng chuẩn phổ biến (DigitalOcean, Cloudflare Support), ưu tiên hướng dẫn User ngay bằng domain knowledge hoặc tái sử dụng DUY NHẤT một runner có sẵn (`scripts/winrt_ocr.py` hoặc `D:/Taadaa/cleanup.py` / `tools/run_ocr.py`). Tuyệt đối CẤM lách Guard bằng cách dispatch subagent ngầm chỉ để bóc chữ một bức ảnh tư vấn.
- **Triệt tiêu bẫy "Mù ảnh" ở Gateway**: Khi active model có multimodal vision (Gemini / Claude / GPT-4o), cấu hình bắt buộc phải là `agent.image_input_mode = native` trong `config.yaml`. Tránh để sót chế độ `text` khiến Gateway stripped dữ liệu ảnh và biến ảnh thành chuỗi text đường dẫn, buộc bot phải chạy OCR đệm thủ công gây trễ nhịp.
- **Bẫy Ảo Giác Mù Khi Đọc UI WebView (XML Omission Trap)**:
  * *Hiện tượng*: Trên các màn hình Android WebView (Google Sign-in, TikTok Shop, WebView form), cây UI dump của ATX agent / UiAutomator thường xuyên nuốt hoặc làm rơi các node text clickable (như link "Tạo tài khoản", "Đăng ký").
  * *Hậu quả*: Agent dựa vào XML thấy thiếu node sẽ vội vã kết luận sai thực tế rằng "màn hình không có nút", "Google ép Sign-in Only", gây bực bội cho User và làm tắc nghẽn luồng.
  * *Kỷ luật*: Khi màn hình là WebView hoặc nghi ngờ XML bị sót node, BẮT BUỘC chụp screenshot và chạy `winrt_ocr` / `extract_ui(..., mode='webview')` để đọc chữ thật trên pixel. Nếu text xuất hiện trên ảnh nhưng XML mất, dùng ngay tọa độ calibrated từ OCR để tap thay vì throw exception dừng automation.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
