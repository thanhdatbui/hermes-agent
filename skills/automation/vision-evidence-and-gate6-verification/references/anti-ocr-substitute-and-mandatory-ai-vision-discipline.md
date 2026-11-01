# Kỷ Luật Đọc Ảnh Hiện Trường: Cấm OCR Mù & Bắt Buộc Vision Thật (Chống Báo Cáo Đối Phó)

## 1. Bối Cảnh Sự Cố & Cơ Chế Vi Phạm (Session 01/11/2026 - Sự Cố Hộp Thoại War3)
- **Hiện tượng**:
  - Người dùng gửi ảnh màn hình Windows hỏi *"lỗi gì khi chơi war3 v"*.
  - Trên màn hình thực tế có một cửa sổ web dashboard TikTok Farm phía sau, và **nổi bật ngay giữa màn hình là một hộp thoại màu xám mang tiêu đề "War3" với icon X đỏ: "FATAL ERROR! 0xC0000005 ACCESS_VIOLATION"**.
  - Coordinator lại chạy script `WinRT OCR` thô (`run_winrt_ocr.py`). OCR chỉ bắt được các dòng chữ to, tương phản cao trên web dashboard phía sau (`@wy010822`, `BXH Tim`, `Followers`), hoàn toàn bỏ sót hộp thoại lỗi War3 nổi ở giữa.
  - Hậu quả: Coordinator phán *"ảnh không có cửa sổ game hay lỗi War3 nào, chỉ có bảng TikTok Ledger, bạn gửi nhầm ảnh rồi"*.
  - Người dùng chất vấn gắt: *"cái bảng lỗi hiện lên kìa?"* và *"là sao lại dùng OCR mà đéo dùng não của AI đọc ảnh"*.
- **Nguyên nhân gốc rễ (Root Cause)**:
  1. **OCR cơ học là công cụ đọc chữ 1D, hoàn toàn mù về bố cục 2D**: OCR không hiểu khái niệm popup, modal, z-index, không phân biệt được cửa sổ tiền cảnh (foreground) vs nền (background).
  2. **Bệnh lười / đối phó khi hạ tầng Vision gặp trục trặc**: Khi Telegram Gateway rớt vào nhánh lỗi, thay vì kích hoạt kênh LLM Vision đa phương thức (Claude Vision / Multimodal) để soi mắt thật, Agent lại lùi bước dùng OCR đọc text thô cho tiện, dẫn đến mù toàn diện.

---

## 2. Kỷ Luật Thép Khi Tiếp Nhận Mọi Ảnh Giao Diện / Báo Lỗi

1. **CẤM TUYỆT ĐỐI dùng OCR thay thế cho Mắt và Não của AI:**
   - Với mọi câu hỏi của User về ảnh ("lỗi gì", "xem ảnh này", "đây là cái gì", "bị sao thế này"): BẮT BUỘC dùng Não Thị Giác của LLM Multimodal (`browser_vision` hoặc `claude_worker --role reviewer` / Claude CLI Vision) để nhìn toàn diện.
   - OCR CHỈ ĐƯỢC DÙNG làm công cụ phụ trợ để bóc tách tọa độ pixel chính xác cho automation click (bấm nút), TUYỆT ĐỐI KHÔNG DÙNG làm nhận thức thị giác (visual perception).

2. **Quy Trình Kiểm Tra 2 Lớp (Foreground vs Background):**
   - Khi đọc ảnh màn hình phức tạp: Phải phân tách rõ:
     * **Lớp tiền cảnh (Foreground):** Có hộp thoại lỗi (dialog), popup, alert, thông báo treo nào đang che ở giữa hay không?
     * **Lớp hậu cảnh (Background):** Ứng dụng/website nền đang mở là gì?
   - Không được thấy nền web quen thuộc mà vội kết luận là User gửi nhầm ảnh!

3. **Fallback Khi Inbound Vision Bị Lỗi Code Nội Bộ:**
   - Nếu `browser_vision` hoặc luồng nạp ảnh tự động bị lỗi đường dẫn / module, ngay lập tức dùng `claude_worker.py --role reviewer` để đọc trực tiếp file ảnh bằng Multimodal Vision của Claude Sonnet.
   - Thà tốn 1 lượt gọi Vision độc lập để có câu trả lời chuẩn xác 100% còn hơn ném OCR thô ra để chém gió sai sự thật và bị User chửi.
