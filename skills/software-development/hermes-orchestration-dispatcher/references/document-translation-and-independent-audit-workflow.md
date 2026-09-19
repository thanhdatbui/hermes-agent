# Document Translation and Independent Review Workflow (Gemini Vision + Claude Audit + ReportLab PDF)

## 1. Bối cảnh & Mục tiêu (Context & Goal)
Khi người dùng yêu cầu dịch một tài liệu kỹ thuật dài, dạng PDF scanned (ảnh catalogue, không có text layer), chứa nhiều bảng biểu, thông số kỹ thuật, ký hiệu chuẩn và sơ đồ (ví dụ: Catalogue PCCC, thiết bị công nghiệp):
- Cần dịch chính xác thuật ngữ kỹ thuật, không làm sai lệch thông số kỹ thuật, mã hiệu sản phẩm (SKU).
- Tránh tràn context, treo phiên hoặc mất mát dữ liệu do context window lớn.
- Phối hợp đa mô hình: **Vision Model chuyên dịch trích xuất (Gemini Flash Vision)** + **Auditor chuyên kiểm định kỹ thuật (Claude CLI / Opus)** + **Render xuất bản tài liệu chuẩn (ReportLab PDF / Markdown)**.

---

## 2. Quy trình 4 bước chuẩn hóa (Standard 4-Step Pipeline)

### Bước 1: Render hình ảnh & Chia Batch tuần tự (Bounded Batching)
- Tuyệt đối không ném toàn bộ 20-50 trang PDF scan cùng lúc vào một prompt (dễ nghẽn, timeout hoặc sót trang).
- Dùng `pymupdf` (fitz) render từng trang ra ảnh PNG ở độ phân giải vừa đủ rõ nét (ví dụ: 150 DPI).
- Chia thành các batch nhỏ (3-5 trang đôi / batch).
- Gọi Multimodal Vision Model (ví dụ: `antigravity/gemini-3.8-flash-tiered` qua OmniRoute `:20129`) với prompt yêu cầu:
  * Giữ nguyên 100% mã hiệu sản phẩm (SKU, Model Code).
  * Chuẩn hóa bảng thông số kỹ thuật thành Markdown Table.
  * Bám sát thuật ngữ kỹ thuật chuyên ngành và tiêu chuẩn hiện hành (TCVN, GB, ISO, ANSI).
- Lưu kết quả dịch từng batch độc lập ra đĩa (`batch_1_p01_p05.md`, `batch_2_p06_p10.md`, ...).

### Bước 2: Đối soát chéo độc lập bằng Claude CLI (Second-Opinion Audit)
- Không tự kết luận bản dịch là hoàn hảo. Gọi Claude CLI với prompt audit chuyên sâu:
  ```bash
  claude -p "Hãy kiểm tra file C:/path/to/batch_X.md... đối soát tính chuẩn xác của các bảng thông số kỹ thuật (Model, tiêu chuẩn, kích thước, áp lực, nhiệt độ), thuật ngữ chuyên ngành và mã SKU..." > review_batch_X.txt 2>&1
  ```
- Chạy nền (`background=True, notify_on_complete=True`) hoặc redirect file để tránh bị cắt cụt output.
- Báo cáo audit từ Claude CLI sẽ bóc tách các lỗi:
  * Lỗi quy đổi đơn vị (ví dụ: K-factor metric vs US gpm).
  * Ký hiệu ren sai tiêu chuẩn (ví dụ: ren trụ G vs ren côn R, Rp).
  * Thuật ngữ chưa nhất quán (ví dụ: "cạnh tường" vs "vách tường - sidewall").
  * Lỗi chính tả thuật ngữ kỹ thuật.

### Bước 3: Chuẩn hóa & Hợp nhất tài liệu (Consolidation & Cleansing)
- Viết script Python tự động làm sạch và áp dụng toàn bộ các khuyến nghị chỉnh sửa từ báo cáo audit vào từng batch.
- Hợp nhất các batch đã làm sạch thành một file Markdown tổng thể duy nhất (`Catalog_Full.md`).

### Bước 4: Xuất bản PDF chuyên nghiệp với ReportLab
- Để tài liệu hiển thị được tiếng Việt và ký tự đặc biệt, bắt buộc đăng ký font TrueType hệ thống:
  ```python
  from reportlab.pdfbase import pdfmetrics
  from reportlab.pdfbase.ttfonts import TTFont
  pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
  pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
  ```
- **Các cạm bẫy ReportLab cần tránh (Critical Pitfalls):**
  1. **Thẻ HTML không hợp lệ:** ReportLab `paraparser` rất nghiêm ngặt. Thẻ `<br>` phải viết thành `<br/>`. Thẻ không được lồng chéo (ví dụ: `<b><i>text</b></i>` sẽ gây `Parse error: saw </b> instead of expected </i>`).
  2. **Escape ký tự đặc biệt:** Mọi nội dung text trước khi nhồi vào `Paragraph` phải qua `html.escape()`, sau đó mới chuyển đổi các tag markdown `**` -> `<b>`, `*` -> `<i>`.
  3. **Độ rộng cột bảng (Table Column Widths):** Tính toán `col_w = printable_width / num_cols` và bọc nội dung ô vào `Paragraph` để tự động xuống dòng, tránh tràn mép trang.
- Báo cáo rõ ràng đường dẫn tuyệt đối các file trên máy local cho người dùng.
