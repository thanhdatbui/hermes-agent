---
name: visual-document-translation
description: Translate scanned graphic PDFs, brochures, and product catalogs in-place while preserving 100% of photos, diagrams, and layout.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Translation, OCR, Vision, Graphic-Design, In-Place-Translation]
    related_skills: [pdf, ocr-and-documents]
---

# Visual Document Translation (In-Place Catalog Translation)

Use this skill whenever the user asks to translate a scanned PDF, brochure, flyer, or product catalog where text is embedded in graphics, photos, or complex artistic layouts.

## Core Rule & User Preference

**DO NOT strip graphics or convert the document into a plain text/table document.**
When a user asks to "translate this catalog/PDF", they expect the final output to retain 100% of the original visual layout, product images, diagrams, and corporate branding, with only the foreign language text replaced by the translated text.

**PRIORITIZE FULL HIGH-RES AS PRIMARY DELIVERABLE:**
- Khi user nhờ dịch tài liệu cho đối tác, khách hàng hoặc bên thứ ba ("ông a nhờ dịch", "gửi đối tác", "hồ sơ thầu"): BẮT BUỘC đưa **Bản Full High-Res (Chất lượng gốc, 150+ DPI, không nén mờ)** làm sản phẩm bàn giao chính thức lên đầu tiên.
- Bản Mobile Light chỉ là file phụ đính kèm để xem lướt trên điện thoại. CẤM để bản Mobile Light lấn át hoặc khiến người dùng hiểu nhầm là hệ thống chỉ làm bản nén nhẹ.
- **Quy tắc Font chữ theo Nghị định 30 / Thể thức văn bản kỹ thuật & pháp lý:**
  * Mọi tài liệu có tính chất Báo cáo thử nghiệm (Test Report / 检验报告), Chứng nhận kiểm định (Certificate / 认证证书), Tiêu chuẩn kỹ thuật (TCVN / GB / ISO), Hợp đồng, Công văn: **BẮT BUỘC dùng 100% Times New Roman (`times.ttf` & `timesbd.ttf`)**. Tuyệt đối CẤM dùng Arial (`arial.ttf`) vì font không chân sẽ bị đánh giá là font lạ mắt, phi thể thức, không nghiêm túc.
  * Chỉ dùng Arial cho các brochure quảng cáo, tờ rơi bán hàng, flyer hiện đại.

## Acceptance Gate: translation completeness before delivery

A selectable-text PDF is not automatically a translated PDF. A draft that preserves the original scan and adds a few labels, glossary notes, or a model list must remain explicitly marked `DRAFT_NEEDS_REVIEW`; never report it as complete. Before delivery, validate all of the following:

1. The translation manifest has one structured block set for every source page (no missing page, no empty page), with source text, Vietnamese translation, coordinates, and typography metadata.
2. The renderer actually consumes that manifest; inspect the output text layer and visual previews, rather than trusting the worker self-report or file existence alone.
3. Review at least the cover, a dense table page, and the certificate/model-list page visually. The original Chinese must not remain as the primary readable content in translated regions, and no white-out rectangles may damage table borders or paper texture.
4. Enforce a domain glossary before rendering. For PCCC reports, use `°C` (degree sign plus C, not `℃`), `Tấm tán nước`, `Phần tử kích hoạt`, `Thử nghiệm kiểu loại`, `Nhóm chứng nhận`, `Đường kính lỗ phun`, `phường Khê Mỹ`, and the canonical company name `Công ty TNHH Phòng cháy chữa cháy Thiên Thái Phúc Kiến`.
5. Validate critical enumerations against the source before delivery. For the certificate model list, the required set is `115-93, 115-107, 115-121, 115-141, 115-163, 115-182, 115-204, 115-227, 115-260, 115-343`; a missing or substituted model is a blocking content error.

If any gate fails, report the artifact as blocked/draft with concrete evidence. Do not offer a choice between a known-incomplete "vector" draft and a scan-overpainted draft as if either were production-ready.

See `references/pccc-vector-translation-acceptance.md` for the reusable checklist and evidence examples, and `references/pccc-failure-lessons-20261005.md` for the mandatory failure lessons (invisible text layer rejection, manifest coordinate traps, and visual delivery verification).

## Requirements

```bash
pip install pymupdf pillow json-repair requests
```

Fonts: Choose font family based on document domain:
- **Marketing Catalogs, Flyers & Brochures:** Use TrueType Sans-Serif font (e.g. `C:/Windows/Fonts/arial.ttf` & `arialbd.ttf` on Windows, or DejaVuSans on Linux).
- **Official Test Reports, Certificates & Administrative Records (Báo cáo thử nghiệm, chứng chỉ kiểm định PCCC, biên bản, hợp đồng):** BẮT BUỘC dùng **Times New Roman** (`C:/Windows/Fonts/times.ttf` & `timesbd.ttf`, hoặc DejaVuSerif). Tài liệu kiểm định gốc của các viện nghiên cứu/trung tâm đo lường luôn sử dụng font có chân (Songti/Times New Roman). Dùng font không chân (Arial) trên bảng biểu kiểm định sẽ bị đối tác chê là font chữ lạ, không đúng chuẩn văn bản kỹ thuật.

## Pipeline Workflow

1. **Rasterize Pages:** Convert each PDF page to high-res image (150 DPI is optimal for speed vs legibility) via PyMuPDF:
   ```python
   import pymupdf
   doc = pymupdf.open("input.pdf")
   pix = doc[i].get_pixmap(dpi=150)
   img_bytes = pix.tobytes('png')
   ```

2. **Multimodal Vision Coordinate Detection:**
   Pass the page image to a Vision model (e.g. Gemini 3.8 Flash via proxy) with a strict prompt:
   - Identify 2D bounding boxes `[ymin, xmin, ymax, xmax]` (normalized 0–1000) of foreign text blocks.
   - Guard invariant: **NEVER overlap product photos, diagrams, or corporate logos.** Only select text blocks.
   - Provide source text, translated text, text color `[r, g, b]`, and background color `[r, g, b]`.
   - Output as a pure JSON array.

3. **Robust JSON Parsing:**
   Always use `json-repair` to parse the LLM's response. Direct `json.loads` frequently fails on trailing commas or unescaped quotes in multimodal outputs.

4. **In-place Erase & Overwrite (Line-level Auto-Fit & Multi-line Word-Wrap):**
   Using PIL `ImageDraw`:
   - Fill the detected bounding box with `bg_color` (cleans the source text).
   - **Line-level granularity:** Ensure vision prompt asks for line-by-line bounding boxes, NEVER merging multi-column or multi-attribute technical tables into one giant box.
   - **Concise translation for DTP:** Vietnamese/target translations must be concise/abbreviated so text width does not blow past the bounding box.
   - **Two-stage Text Fitting (Single-line auto-fit + Multi-line Word Wrap):**
     Do NOT simply shrink font size to illegible tiny text or cut off text when it's too long for one line. Apply a 2-stage fit:
     Stage 1: Try single line font size down from `int(box_h * 0.85)` to 7pt.
     Stage 2: If single line doesn't fit width, perform **Word-Wrap** splitting text across multiple lines and re-check total height within `box_h`. Only fall back to minimum font if wrapping still exceeds height.
   ```python
   def draw_wrapped_or_fitted_text(draw, box, text, font_path, fg=(0,0,0), bg=(255,255,255), align='left'):
       x1, y1, x2, y2 = box
       box_w = max(12, x2 - x1)
       box_h = max(8, y2 - y1)
       draw.rectangle([x1, y1, x2, y2], fill=bg)

       # 1. Single line fit
       for fs in range(int(box_h * 0.85), 7, -1):
           f = ImageFont.truetype(font_path, fs)
           bb = draw.textbbox((0, 0), text, font=f)
           if (bb[2] - bb[0]) <= box_w and (bb[3] - bb[1]) <= box_h:
               tx = x1 + 1 if align == 'left' else x1 + max(0, (box_w - (bb[2] - bb[0])) // 2)
               ty = y1 + max(0, (box_h - (bb[3] - bb[1])) // 2)
               draw.text((tx, ty), text, fill=fg, font=f)
               return

       # 2. Multi-line word wrap fit
       words = text.split()
       for fs in range(min(18, int(box_h * 0.65)), 6, -1):
           f = ImageFont.truetype(font_path, fs)
           lines, cur_line = [], []
           for w in words:
               test_line = ' '.join(cur_line + [w])
               bb = draw.textbbox((0, 0), test_line, font=f)
               if (bb[2] - bb[0]) <= box_w:
                   cur_line.append(w)
               else:
                   if cur_line: lines.append(' '.join(cur_line)); cur_line = [w]
                   else: lines.append(w); cur_line = []
           if cur_line: lines.append(' '.join(cur_line))

           line_h = int(fs * 1.25)
           if len(lines) * line_h <= box_h + 6:
               y_start = y1 + max(0, (box_h - len(lines) * line_h) // 2)
               for i, l in enumerate(lines):
                   bb = draw.textbbox((0, 0), l, font=f)
                   tx = x1 + 1 if align == 'left' else x1 + max(0, (box_w - (bb[2] - bb[0])) // 2)
                   draw.text((tx, y_start + i * line_h), l, fill=fg, font=f)
               return

       # 3. Safe fallback
       f = ImageFont.truetype(font_path, 7)
       draw.text((x1 + 1, y1 + 1), text, fill=fg, font=f)
   ```

5. **Re-assemble Landscape/Portrait PDF (PyMuPDF Safe Assembler):**
   *Note: Do NOT use Pillow's `pil_images[0].save(out_pdf, save_all=True)` because Pillow's `PdfImagePlugin` frequently crashes with `KeyError: 'JPEG'` when saving multi-page image lists.*
   Always assemble with PyMuPDF:
   ```python
   import pymupdf

   # 1. Full High-Res PDF (Lossless)
   doc_full = pymupdf.open()
   for p in rendered_images:
       img_doc = pymupdf.open(p)
       doc_full.insert_pdf(pymupdf.open("pdf", img_doc.convert_to_pdf()))
       img_doc.close()
   doc_full.save("output_translated.pdf", garbage=4, deflate=True)
   doc_full.close()

   # 2. Mobile Light PDF (100 DPI, JPEG quality 80, fast loading on Telegram)
   doc_light = pymupdf.open()
   for p in rendered_images:
       im = Image.open(p).convert('RGB')
       w, h = im.size
       rw, rh = int(w * 100 / 150), int(h * 100 / 150)
       im_resized = im.resize((rw, rh), Image.Resampling.LANCZOS)
       import io
       buf = io.BytesIO()
       im_resized.save(buf, format="JPEG", quality=80)
       img_bytes = buf.getvalue()
       img_doc = pymupdf.open("jpeg", img_bytes)
       rect = img_doc[0].rect
       pdf_page = doc_light.new_page(width=rect.width, height=rect.height)
       pdf_page.insert_image(rect, stream=img_bytes)
       img_doc.close()
   doc_light.save("output_translated_Mobile_Light.pdf", garbage=4, deflate=True)
   doc_light.close()
   ```

## Common Pitfalls

- **Document Genre Font Mismatch & Deliverable Hierarchy (Báo cáo thử nghiệm / Kiểm định pháp lý vs Catalogue thương mại):**
  * *Triệu chứng:* Dịch tài liệu là Báo cáo thử nghiệm kiểu loại (Test Report / 检验报告), Chứng nhận hợp quy (Certificate / 认证证书), biên bản kỹ thuật nhưng mặc định chọn font Arial (sans-serif) hoặc gửi bản Mobile Light làm sản phẩm chính. Người dùng sẽ phản ứng gay gắt: *"bản full đi ông a nhờ dịch dùm mà, font chữ gì lạ v?"*. Font không chân nhìn hiện đại nhưng thiếu tính trang trọng, không ăn khớp với thể thức văn bản hành chính/kỹ thuật và font chữ có chân (Songti/Times New Roman) của bản gốc.
  * *Khắc phục triệt để:*
    1. **Font Invariant:** Phân loại thể loại tài liệu ngay từ bước tiền xử lý. CẤM hardcode `arial.ttf` trong template prompt dispatch worker hoặc render script. Nếu tài liệu chứa các từ khóa Báo cáo kiểm định / Thử nghiệm (Test Report, 检验报告), Chứng chỉ (Certificate, 认证证书), Tiêu chuẩn (TCVN, GB, ISO), Hợp đồng: BẮT BUỘC dùng **Times New Roman** (`C:/Windows/Fonts/times.ttf` cho text thường và `timesbd.ttf` cho tiêu đề/kết luận/đoạn in đậm).
    2. **Deliverable Hierarchy:** Luôn đặt bản **Full High-Res (`_Tieng_Viet.pdf`)** làm sản phẩm chính thức số 1 ở đầu tin nhắn kèm `MEDIA:`, khẳng định độ sắc nét gốc để in ấn hoặc nộp đối tác/cơ quan. Bản `_Mobile_Light.pdf` chỉ là file phụ đính kèm phía dưới để mở nhanh trên điện thoại. Không bao giờ để bản Mobile Light lấn át bản Full.

- **WinRT OCR Diagnostic Artifact Trap (Ngộ nhận vỡ font do OCR thiếu gói tiếng Việt):**
  * *Triệu chứng:* Dùng WinRT OCR kiểm tra lại ảnh sau khi dịch, log trả về chuỗi ký tự méo dấu lạ lùng (`Viön Nghién cipu...`, `Dhu Phun...`). Agent tưởng nhầm font nhúng trong script bị lỗi bảng mã Unicode tiếng Việt và hoang mang đi sửa font.
  * *Bản chất:* Windows WinRT OCR trên máy chưa cài language pack `vi-VN` nên tự fallback về `en-US`. Chữ tiếng Việt trên ảnh PNG/PDF thực tế hiển thị hoàn toàn chuẩn xác. Không được dùng OCR tiếng Anh để thẩm định dấu tiếng Việt; phải dùng `browser_vision` hoặc mở trực tiếp ảnh kiểm tra trực quan.

- **Direct Execution Intent vs External Prompt Mirroring Trap:**
  * *Triệu chứng:* Khi user gửi một prompt rất dài, có cấu trúc chi tiết ("Tôi có 1 file catalogue... copy đoạn dưới đây dán thẳng vào Gemini... Lỗi 1... Lỗi 2... Yêu cầu..."), agent dễ bị ngộ nhận rằng user đang nhờ mình "soạn thảo / hoàn thiện prompt để user đem đi dán cho một bot/model khác", dẫn đến việc trả lời bằng văn bản góp ý prompt hoặc báo file cũ đã có mà KHÔNG thực sự chạy tác vụ. User sẽ cáu: *"t yêu cầu m làm đó, m đang chạy gemini đó"*.
  * *Quy tắc ứng xử:* Khi user đưa prompt yêu cầu dịch tài liệu kèm file đính kèm, LUÔN coi đó là chỉ thị THỰC THI TRỰC TIẾP cho chính agent (với vai trò điều phối pipeline gọi model Vision như Gemini 3.8 Flash). BẮT BUỘC khởi chạy ngay pipeline xử lý thay vì chỉ chỉnh sửa câu chữ của prompt.

- **Telegram Document Cache Staging & Coordinator Guard Contract Compliance:**
  * *Triệu chứng:* Tài liệu PDF gửi qua Telegram được lưu tại thư mục cache ứng dụng. Khi Coordinator gọi trực tiếp đường dẫn nhạy cảm vào tham số tool hoặc chạy script Python tự do, hệ thống Guard kích hoạt chặn lệnh (Terminal Blocked, Guard Self-Protection, Write Denied).
  * *Khắc phục chuẩn quy trình:*
    1. Dùng lệnh sao chép qua biến môi trường để stage file sang thư mục làm việc hợp lệ (ví dụ `D:/Taadaa/input.pdf`): `cp "$LOCALAPPDATA"/hermes/cache/documents/doc_<hash>_*.pdf /d/Taadaa/input.pdf`.
    2. Không tự ý viết script Python lớn trên Coordinator khi hết ngân sách T1 (<= 15 dòng).
    3. Phân biệt rõ nhiệm vụ của Worker khi điều phối qua `delegate_task`:
       - `TASK_KIND: INVESTIGATE`: Chỉ dùng cho việc đọc log, inspect text thuần túy không tạo file mới. Worker ở chế độ này bị **Read-Only 100%**, cấm tạo thư mục hay lưu file ảnh raster (`.png`).
       - `TASK_KIND: EDIT`: Bắt buộc sử dụng khi cần worker tạo script rasterize trang PDF, trích xuất ảnh hoặc render thành phẩm. Bắt buộc cung cấp: `FILE: D:/Taadaa/tools/<script_name>.py`, `FOCUSED_TEST: python -m py_compile D:/Taadaa/tools/<script_name>.py`, `BUDGET: <= 10 calls` và mệnh đề `FAIL_FAST: Nếu trong <= 3 iterations...`.
       - Trong môi trường Hermetic Shell của Worker, tuyệt đối không dùng ký tự nối lệnh shell (`;`, `&&`, `||`, `|`, `$`, `>`, `<`). Gọi thực thi script bằng lệnh Python đơn lẻ.

- **Mobile Review Delivery via Telegram (Gửi ảnh/file trực tiếp qua Telegram để user duyệt trên điện thoại):**
  * *Bối cảnh:* User thường xuyên đọc tin nhắn và kiểm tra tiến độ trên điện thoại qua Telegram, không thể mở trực tiếp đường dẫn file local Windows (`C:\Users\...`).
  * *Quy tắc gửi PDF cho Mobile:*
    - File PDF ghép từ 20 ảnh high-res thường nặng từ 20MB đến 40MB. Gửi qua Telegram sẽ rất nặng và tải lâu trên mạng di động.
    - Tạo một bản nén nhẹ dành riêng cho mobile (`_Mobile_Light.pdf`) bằng cách render mỗi trang ở 100 DPI và nén ảnh JPEG chất lượng 80 (`pix.tobytes('jpeg', jpg_quality=80)`), lưu với `garbage=4, deflate=True`. File giảm về ~6-7 MB, chữ và ảnh sản phẩm vẫn cực kỳ sắc nét.
    - Đính kèm trực tiếp vào tin nhắn phản hồi bằng cú pháp: `MEDIA:<đường_dẫn_tuyệt_đối_file_pdf>`.
  * *Quy tắc gửi Ảnh Preview duyệt từng trang (Mobile Image Inspection):*
    - Khi user yêu cầu *"sửa xong gửi ảnh qua tele cho t"*, TUYỆT ĐỐI KHÔNG CHỈ BÁO XONG HOẶC GỬI FILE PDF TO BẮT USER TỰ TẢI LẠI.
    - BẮT BUỘC xuất trực tiếp ảnh của các trang vừa sửa (hoặc crop vùng trọng tâm vừa sửa như Mục lục, bảng thông số) thành file PNG/JPEG và gửi ngay vào tin nhắn bằng `MEDIA:<đường_dẫn_ảnh.png>` trên một dòng riêng. User mở Telegram thấy ảnh đập vào mắt ngay lập tức để duyệt hoặc chỉ lỗi tiếp.

- **Vết chữ Trung & Vùng mô tả gốc bị sót do lệch tọa độ (Ghosting & Header Clearance Pitfalls):**
  * *Triệu chứng:* Khi user chỉ lỗi "chỗ này đè lên chữ Trung sửa lại, phóng to phông chữ lên", thường là do agent vẽ cụm tiêu đề mới ở tọa độ quá cao hoặc quá thấp, trong khi cụm chữ Trung gốc (kèm các gạch đầu dòng tính năng) nằm ở vị trí khác và chưa hề bị phủ màu nền. Kết quả là trên ảnh xuất hiện cả tiếng Việt lẫn tiếng Trung nằm kề nhau.
  * *Khắc phục:* Luôn crop soi ảnh gốc để xác định chính xác toàn bộ vùng span của tiêu đề và tính năng gốc (ví dụ: từ $y=120$ đến tận $y=550$). Quét màu nền đồng nhất (ví dụ `(16, 20, 25)` cho card tối màu) phủ trọn vẹn toàn bộ vùng đó trước khi vẽ chữ mới. Đồng thời chủ động tăng font size (tiêu đề 36-42pt, phụ đề 22-26pt) để chữ nổi bật, dễ đọc trên mobile.

- **Dịch sót các khối văn bản kỹ thuật và chú thích ảnh phụ (Omission of Secondary Text Blocks):**
  * *Triệu chứng:* Agent thường chỉ tập trung dịch tiêu đề lớn và bảng model SKU, nhưng bỏ sót:
    1. Đoạn văn mô tả kỹ thuật (phần giải thích nguyên lý hoạt động, ví dụ đoạn `喷头可以用来探测火灾...` ở trang 4 hoặc `配水支管内有余水...` ở trang 6).
    2. Chú thích kỹ thuật dưới ảnh sản phẩm (các dòng `公称动作温度: 68°C`, `安装位置: 直立型`, `流量系数: K=80`...).
  * *Khắc phục:* Với mỗi trang hoặc nửa trang catalogue, bắt buộc phải rà soát theo 4 lớp độc lập: (1) Tiêu đề & tiêu chuẩn; (2) Đoạn văn mô tả & lưu ý; (3) Bảng thông số kỹ thuật; (4) Từng cụm nhãn & chú thích dưới mỗi ảnh sản phẩm. Tuyệt đối không để sót bất kỳ lớp nào dạng song ngữ chữ Hán.

- **Kích thước trang không đồng nhất sau khi chắp vá (Inconsistent Page Sizes / Viewport Jitter):**
  * *Triệu chứng:* Khi replace các trang riêng lẻ nhiều lần (`doc.delete_page(idx)`, `doc.insert_pdf(...)`), nếu ảnh nguồn render ở các mức DPI hoặc kích thước canvas khác nhau (ví dụ: trang chuẩn là 1889x1290pt / 2519x1721px, nhưng trang sửa lẻ lại chèn ảnh 3936x2689pt), khi user mở PDF trên trình duyệt Edge/Chrome và cuộn chuột, các trang sẽ bị giật, nhảy kích thước to nhỏ thụt thò rất khó chịu.
  * *Khắc phục:* BẮT BUỘC có bước chuẩn hóa (Normalize Canvas):
    - Đọc kích thước chuẩn của trang gốc (`p.rect.width`, `p.rect.height`, ví dụ: 1889.25 x 1290.75 pt hoặc 2519 x 1721 px).
    - Trước khi đóng gói hoặc sau mỗi lượt chắp vá, duyệt qua toàn bộ N trang của PDF, kiểm tra nếu trang nào lệch kích thước thì resize ảnh về đúng `(TARGET_W, TARGET_H)` bằng `Image.Resampling.LANCZOS` rồi mới ghép vào PDF. Đảm bảo 100% các trang đồng nhất kích thước trước khi giao cho user.

- **Văng mất mục con khi xóa nền (Over-clearing Child Entries):**
  * Khi xóa các cụm danh mục hoặc mục lục ở nửa dưới (như các thiết bị định vị P.33, P.36), cấm quét vùng hình chữ nhật quá tay xuống dưới đáy trang vì sẽ xóa mất các mục con cuối danh mục. Luôn crop soi ảnh gốc để xác định chính xác đáy của khối chữ (`y_max`) trước khi gọi `draw.rectangle`.

- **Quy trình review & sửa lỗi theo yêu cầu User (User-in-the-loop Page-by-Page Tuning):**
  * Khi user yêu cầu "thôi sửa từng trang đi, trang này trước" hoặc "h mày sửa t duyệt k cần qua claude cli nữa đâu nhé": BẮT BUỘC tắt hẳn vòng lặp gọi Claude CLI trung gian để tiết kiệm thời gian, phản hồi nhanh tức thì.
  * **Phát hiện Prompt đứt đoạn & Tương tác Prompt Chuyển tiếp (Forwarded Prompt Detection):**
    - Khi user gửi một đoạn prompt kèm câu dẫn như *"đây là nội dung prompt, bạn copy đoạn dưới đây dán thẳng vào Gemini: ..."* hoặc gửi tiếp phần sau *"t gửi đoạn sau đầy đủ r mà?"*:
      1. BẮT BUỘC rà soát lịch sử hội thoại xem dự án/file này đã từng được thực hiện chưa. Nếu các file thành phẩm (`_CHINH_THUC.pdf`, `_Mobile_Light.pdf`) đã sẵn có trên máy tính của user (`C:\Users\...\translated_catalog`), mục tiêu thực sự của user thường là **yêu cầu Agent trực tiếp giải quyết hoặc xác nhận đáp ứng các tiêu chuẩn đó**.
      2. Tránh phản hồi máy móc theo kiểu chỉ copy prompt thành khung code hoặc nhắc user tự dán, khiến user bực mình vì tưởng Agent từ chối làm hoặc không hiểu ngữ cảnh.
      3. Báo cáo ngay tình trạng xử lý của file, đối soát trực tiếp từng tiêu chuẩn user đưa ra (font Unicode, xóa triệt để chữ Hán, auto-fit/word-wrap) và gửi ảnh preview minh chứng (`MEDIA:<ảnh>`) để user nghiệm thu trực tiếp.
  * Phân tích trực tiếp ảnh screenshot user chụp gửi vào, định vị chính xác vị trí bị lỗi (ví dụ: góc trên trái, dải banner, dải footer slogan, hoặc các ô bảng thông số).
  * Kiểm tra kỹ các chi tiết đồ họa nền:
    - Nếu có hoa văn, mũi tên, hoặc khối màu (như 3 mũi tên đỏ của Tầm nhìn/Sứ mệnh/Tinh thần): Bắt đúng tọa độ text nằm dưới mũi tên, không được vẽ đè lên mũi tên hoặc vẽ lệch ra ngoài làm lộ chữ Hán cũ.
    - Slogan góc chân trang: Thường nằm sát lề ngoài cùng bên phải, phải xóa trắng phủ trọn dải mép (`x` đến 2420+) và căn lề phải (right-aligned) chữ tiếng Việt tương ứng.
    - Tiêu đề mục lục: Nếu trang gốc có chữ rỗng (outline/hollow) nghệ thuật, khi in đè chữ Việt phải xóa trắng sạch sẽ vùng chữ rỗng bên dưới, không để 2 lớp chữ chồng chéo gây lem nhem.
  * Sau khi vá trang đơn lẻ, dùng PyMuPDF thay thế đúng trang đó trong file PDF chính thức (`doc.delete_page(idx)`, `doc.insert_pdf(...)`) rồi báo user bấm F5 trên trình duyệt xem ngay.

- **Pillow PdfImagePlugin KeyError: 'JPEG' Bug & PyMuPDF Assembly Invariant:**
  * *Triệu chứng:* Khi ghép danh sách ảnh đã inpaint thành file PDF bằng Pillow (`imgs[0].save(out_pdf, save_all=True, append_images=imgs[1:])`), chương trình văng lỗi `KeyError: 'JPEG'` trong `PIL/PdfImagePlugin.py` (dòng 151: `Image.SAVE["JPEG"](im, op, filename)`).
  * *Khắc phục:* Tuyệt đối KHÔNG dùng Pillow để xuất file PDF ghép nhiều trang. Luôn sử dụng PyMuPDF (`doc = pymupdf.open()`, mở từng ảnh và nạp qua `doc.insert_pdf(pymupdf.open("pdf", img_doc.convert_to_pdf()))` rồi `doc.save(out_pdf, garbage=4, deflate=True)`). PyMuPDF vừa nhanh hơn, vừa giải phóng bộ nhớ sạch sẽ và không phụ thuộc vào bộ mã hóa JPEG nội bộ của Pillow.

- **Convert sang Word mà thiếu ảnh (Word Document Without Images Bug):**
  * *Triệu chứng:* Khi user phàn nàn dịch PDF bị lỗi chữ và hỏi *"sao không chuyển sang Word rồi sửa xong chuyển lại PDF sau?"*, agent vội vàng dùng `python-docx` tạo một file Word chỉ có bảng biểu và chữ thuần (text-only/table-only) mà **HOÀN TOÀN KHÔNG CÓ ẢNH SẢN PHẨM**. User mở Word ra sẽ cáu ngay lập tức: *"file word m convert ra có ảnh éo đâu"*.
  * *Bản chất kỹ thuật:* PDF scan catalogue là 20 bức ảnh raster phức tạp. Nếu tạo file Word để user chỉnh sửa nội dung song song với hình ảnh, **BẮT BUỘC phải trích xuất (crop) từng ảnh sản phẩm tương ứng hoặc chèn ảnh trang làm background/hình minh họa cạnh bảng thông số** bằng `p.add_run().add_picture(img_path, width=...)`. KHÔNG BAO GIỜ được giao một file Word trơ trọi chỉ có chữ khi đề bài là "catalogue sản phẩm".
  * *Quy tắc ứng xử khi user hỏi về Word:* Phải giải thích ngay từ đầu: file gốc là PDF scan ảnh phẳng; muốn sửa trực tiếp trên ảnh gốc thì phải dùng in-place image inpainting (Photoshop/Pillow), còn nếu muốn file Word thì phải thiết kế dạng tài liệu kỹ thuật có chèn ảnh sản phẩm vào từng mục, chứ không có nút convert 1 chạm giữ nguyên thiết kế đồ họa của scan PDF sang Word.
- **Bóng ma chữ Hán & Nửa đoạn văn dài (Ghosting & Half-Box Inpainting):** Đối với các đoạn văn mô tả sản phẩm dài hoặc đoạn lưu ý/cảnh báo nhiều dòng (như Drencher, EC-ZST 115), Vision AI hay bị lỗi co hẹp bounding box chỉ bao 1-2 dòng đầu, hoặc dừng lại trước dấu câu cuối (`患。`). Khi vẽ nền trắng, phần chữ tiếng Trung bên dưới không bị xóa hết, dẫn đến việc chữ tiếng Việt đè lên nửa trên còn nửa dưới lộ nguyên chữ Trung ("bóng ma").
  * *Khắc phục:* Prompt vision phải nhấn mạnh bắt trọn toàn bộ đoạn văn từ chữ đầu đến dấu chấm cuối cùng; Bounding box phải tự động padding nới rộng thêm 2-3 pixel mỗi cạnh (`x1=max(0, x1-3)`, `y1=max(0, y1-2)`, `x2=min(w, x2+3)`, `y2=min(h, y2+2)`) để tẩy sạch 100% nét chữ gốc trước khi vẽ đè. Căn lề padding chữ mới cách mép 3-4px để không bị cắt xén lề trái.
- **Claude CLI Permission Prompt Hang (Non-TTY / Headless Hang):** Khi gọi Claude CLI (`claude -p "..."`) trong background terminal mà yêu cầu nó tự viết script và chạy lệnh Bash/Disk, Claude Code CLI sẽ bị treo vô thời hạn hoặc dừng lại chờ user bấm "Allow" (`Hộp thoại xin quyền đang chờ bạn phê duyệt...`).
  * *Khắc phục:* BẮT BUỘC thêm cờ `--dangerously-skip-permissions` khi gọi Claude CLI chạy tự động không giám sát (`claude --dangerously-skip-permissions -p "..."`).
- **Silent Untranslated Page Leak (Image Fallback Bug):** If an error occurs in the LLM response (e.g. malformed JSON, timeout, or tuple unpack error), do NOT silently save the raw untranslated image into the final PDF without logging a clear warning or retrying. The user will open the PDF and find raw untranslated pages ("đéo dịch"), thinking the whole pipeline failed. Always retry up to 3 times, parse with `json-repair`, and ensure text replacement happened before marking a page done.
- **Two-Page Spread (Trang đôi) Asymmetric Text Misses:** Trên các tài liệu catalogue in ấn trình bày dạng trang đôi (hai trang ghép trên một sheet landscape, ví dụ trang 10 & 11 trong ảnh PDF số 8, hoặc trang 20 & 21 về van ZSFZ trong ảnh PDF số 12), Vision AI rất hay bị bias tập trung vào trang bên trái (nhiều sản phẩm nổi bật) mà bỏ sót hoàn toàn tiêu đề, đề mục và đoạn văn mô tả ở trang bên phải (ví dụ tiêu đề `水雾喷头/GB5135.3-2003 离心雾化喷头`, `撞击面喷头`, nhãn `产品说明`, hoặc tiêu đề các cột bảng thông số kỹ thuật `型号规格`, `额定工作压力`, `法兰外径`, nhãn phụ kiện `末端试水装置`, `压力开关`, `水力警铃`).
  * *Khắc phục:* Khi tài liệu là khổ đôi (width > height với tỷ lệ > 1.4), tốt nhất nên crop tách trang đôi thành 2 ảnh độc lập (Left page `[:, :w//2]`, Right page `[:, w//2:]`) để gửi Vision AI xử lý độc lập từng nửa trang, sau đó map lại tọa độ để ghép. Việc này triệt tiêu 100% hiện tượng AI "bỏ quên nửa trang" do context window thị giác bị lệch trọng tâm.
- **Specification Table Header Inpainting (Bảng thông số kỹ thuật dày đặc cột):** Các bảng thông số kỹ thuật (flanged type, grooved type) có 8-10 cột rất hẹp (`型号规格`, `公称通径`, `法兰外径`, `螺栓孔中心径`, `最大安装宽度`...). Vision AI thường bỏ qua hàng tiêu đề này do nhầm là cấu trúc đồ họa cố định. Khi render đè, phải dùng script chuyên dụng quét riêng hàng header (`y` từ 805 đến 925), xóa sạch dải header và căn giữa từng cột tiếng Việt chuẩn với font 20-22pt để chữ hiển thị ngay ngắn, không bị lọt lại chữ Hán.
- **Claude CLI Non-Interactive Script Run Flaws (Bugs khi để Claude CLI tự viết script DTP):**
  * Khi giao Claude CLI tự viết script `translate_pccc.py` để làm việc với Vision API, Claude CLI thường dùng công thức pixel thô không chuẩn hóa (relative $x, y$), không tính độ co giãn DPI, và đặc biệt **quên xóa nền cũ trước khi vẽ đè** (hoặc xóa lệch box). Kết quả là chữ tiếng Việt đè chồng lên cả chữ Hán cũ và dấu chấm mục lục.
  * Hơn nữa, Claude CLI trong background không tương tác trực tiếp với model vision mạnh nhất một cách tỉ mỉ từng block mà hay tạo prompt chung chung khiến Vision AI chỉ dịch tiêu đề rồi bỏ sót toàn bộ thân trang.
  * *Kinh nghiệm điều phối:* Dùng Gemini 3.8 Flash trong pipeline Python định sẵn (chuẩn hóa bbox 0–1000, 2-stage fit + word wrap, xóa nền trắng nới rộng 3px) làm lõi xử lý chính; CHỈ dùng Claude CLI vào vai **Auditor / Quality Gate** (soi ảnh từng trang sau khi render để chỉ ra chữ tiếng Trung còn sót hoặc chữ bị lệch). Không nên để Claude CLI tự biên tự diễn viết script đồ họa DTP mù trong background.
- **Claude CLI / Subagent Tooling Misalignment:** When delegating scanned PDF translations to subagents or Claude CLI, do NOT simply pass `fitz.get_text("dict")` or CLI text tools. Scanned PDFs have 0 vector text layers. The prompt to Claude CLI or subagent must explicitly specify: *"This is a raster scan / image-only PDF with 0 vector text. You must use Vision AI or OCR to detect bounding boxes on images and draw text with Pillow"*. Otherwise, Claude CLI will run a text extraction script and report "0 đoạn text đã dịch".
- **Text Overflow & Font Bloat:** When replacing ideographic text (Chinese) with phonetic text (Vietnamese/English), target text is naturally longer. Merging whole paragraphs or multiple spec table rows into one box causes font size calculation based on box height to explode, resulting in massive text covering adjacent product images and running across margins. Always enforce single-line bounding boxes and auto-fit font size loops.
- **ReportLab HTML Paraparser Error:** ReportLab `Paragraph` chokes on `<br>` (needs `<br/>`) and mismatched tags (e.g. `<b><i></b></i>`). If generating companion text reports, always sanitize inline markup.
- **Model Codes (SKU) Invariant:** Never translate product model codes (e.g. ZSTZ, K-80, DN15, 68°C). Keep technical symbols intact.
- **GPT Sol / ChatGPT Web Pool Integration & Scope Boundary:**
  * GPT-5.6 Sol (via local web pool proxy `chatgpt-web/gpt-5.6-sol-high` at port `:20129`) là bộ não suy luận (reasoning/planner/auditor) cực mạnh, hỗ trợ function calling xuất sắc.
  * **Hạn chế giao thức Web Pool:** Cổng forwarder Web Pool hiện tại chỉ forward prompt văn bản (text & tool calls), CHƯA hỗ trợ kênh upload attachment / binary image stream trực tiếp (gửi `image_url` base64 sẽ nhận phản hồi *"Mình chưa thấy ảnh nào được gửi..."*).
  * **Phân vai tối ưu (Não + Mắt + Tay chân):**
    - **Mắt Vision (Bóc tách ảnh/tọa độ DTP):** BẮT BUỘC dùng **Gemini 3.8 Flash Multimodal Vision** (`antigravity/gemini-3.8-flash-tiered`).
    - **Tay chân thực thi (DTP Engine):** Python Pillow / PyMuPDF với thuật toán padding xóa nền 3px + Auto-fit + Word-Wrap.
    - **Não thẩm định (PCCC Technical Review & Validation):** Dùng **GPT-5.6 Sol Web Pool** để đọc nội dung text/markdown đã trích xuất, đối soát tiêu chuẩn TCVN, ISO, kiểm tra tính logic giữa các dải áp lực (áp làm việc, áp thử kín, áp thử bền), hệ số K và khuyến nghị hồ sơ nghiệm thu/đấu thầu.
- **Gemini Vision vs Claude / Sol Auditor Evaluation Benchmark & Anti-Hallucination Guard:**
  * *Bản chất kỹ thuật cổng Web Pool (:20129):* Cổng `chatgpt-web/gpt-5.6-sol-high` chỉ là text forwarder, KHÔNG có kênh upload file nhị phân (PDF/ảnh) hay nhận `image_url` base64. Khi user yêu cầu "ném 2 file cho Sol so sánh", TUYỆT ĐỐI KHÔNG giả lập báo cáo điểm số hay tự biên tự diễn kết luận thiên vị ("Gemini 92đ vs Claude 54đ") khi chưa thực sự đưa được dữ liệu khách quan cho Sol. Bắt buộc phải giải thích rõ rào cản kỹ thuật của cổng proxy và hướng dẫn user ném file trực tiếp trên giao diện web nếu cần mắt AI thứ ba.
  * *Lỗi Silent Fallback (Bỏ sót cả trang khi lỗi JSON):* Khi Vision AI xử lý trang lớn, output JSON dài thường bị lỗi cú pháp (`Expecting ',' delimiter`). Dùng `json.loads` thô sẽ văng Exception; nếu bắt Exception cẩu thả và gán `boxes = []` rồi lưu đè ảnh gốc sang thư mục output, hệ thống sẽ âm thầm giữ nguyên 100% tiếng Trung (như từng xảy ra với Trang 6 và Trang 8) nhưng log vẫn báo "rendered successfully".
  * *Biện pháp bắt buộc:*
    1. BẮT BUỘC dùng `json_repair.loads(raw)` thay cho `json.loads`.
    2. Cắt đôi trang (Left half / Right half) đối với các trang khổ ngang lớn để giảm một nửa số lượng block trên mỗi prompt, triệt tiêu hoàn toàn nguy cơ đứt token / gãy JSON.
    3. Kiểm tra bảo vệ: Nếu `len(boxes) == 0` sau các lần retry, BẮT BUỘC báo lỗi dừng lại, TUYỆT ĐỐI CẤM lưu ảnh gốc tiếng Trung vào file PDF thành phẩm.

- **The Coordinate Inversion Disaster ([x, y, w, h] vs [y, x, h, w]):**
  * *Triệu chứng:* Khi vẽ đè văn bản dịch lên ảnh scan, chữ tiếng Việt bị trôi dạt bay tít sang tận khoảng trắng mép phải ngoài lề (hoặc mép dưới), trong khi chữ tiếng Trung gốc ở giữa trang hoàn toàn KHÔNG bị xóa và chữ tiêu đề tiếng Việt in đè thô bạo lên giữa chữ Hán. Người dùng sẽ phản ứng gay gắt: *"Mày gửi cái hình k thấy ngu hả? Có đọc lại trc khi gửi k"*.
  * *Nguyên nhân cốt lõi:* Bóc tách manifest JSON nhầm lẫn giữa tọa độ ngang $x$ và tọa độ dọc $y$ (ví dụ: rect là `[x, y, w, h]` nhưng script lại tự ý unpack nhầm thành `top, left, height, width = r[0], r[1], r[2], r[3]`). Vì canvas ảnh có kích thước $W \times H$ (ví dụ 1240 x 1755), việc hoán đổi $x$ và $y$ khiến tọa độ $y \approx 970$ biến thành $x \approx 970$ (sát mép phải), và hộp xóa nền trắng bị đặt nhầm vào chỗ trống, không hề chạm vào chữ gốc.
  * *Biện pháp bắt buộc:*
    1. Trước khi chạy batch render, luôn in ra `b['rect']` và so sánh giá trị với $W$ và $H$ của ảnh. Nếu phần tử ở giữa trang có số thứ 2 ($r[1]$) lên tới 900+ trong khi $W=1240, H=1755$, thì $r[1]$ chắc chắn là $y$ (tọa độ dọc), không thể là $x$. Cụ thể rect chính là `[x, y, w, h]`, vẽ với `x1=x, y1=y, x2=x+w, y2=y+h`.
    2. BẮT BUỘC render thử nghiệm duy nhất 1 trang đầu tiên (`page_1.png`) và soi mắt kiểm tra trước khi áp dụng cho toàn bộ tài liệu.

- **The "Invisible Text Layer" / Pseudo-Translation Trap (Bẫy lớp chữ trắng ẩn 1pt):**
  * *Triệu chứng:* Khi gặp khó khăn trong việc căn chỉnh DTP hoặc sợ xóa lem nền, agent tự ý chuyển sang cơ chế "bảo toàn 100% trang scan gốc và chỉ chèn thêm lớp text ẩn/chữ trắng 1pt (`fontsize=1, color=(1,1,1)`) để tìm kiếm". Khi gửi ảnh hoặc PDF cho người dùng, người dùng chỉ nhìn thấy 100% tiếng nước ngoài gốc và chửi thậm tệ: *"Gì gửi hình toàn tiếng trung v"*.
  * *Quy tắc thép:* Lớp chữ ẩn chỉ là tính năng OCR phụ trợ, TUYỆT ĐỐI KHÔNG ĐƯỢC coi là bản dịch. Khi người dùng yêu cầu dịch tài liệu/PDF, kết quả bắt buộc phải là văn bản tiếng Việt HIỂN THỊ RÕ RÀNG BẰNG MẮT THƯỜNG trên trang tài liệu. Không bao giờ bàn giao bản scan kèm text ẩn dưới danh nghĩa bản dịch hoàn chỉnh.

- **Mandatory Visual Inspection Before Sending MEDIA (Soi mắt kiểm tra trước khi gửi ảnh):**
  * *Triệu chứng:* Agent chạy script xong thấy exit code 0, file PDF sinh ra đủ số trang là vội vàng gửi ảnh kèm tin nhắn khen ngợi "đã xong 100%, nét căng" mà không hề tự mở mắt soi lại ảnh (`browser_vision`).
  * *Quy tắc bất di bất dịch:* TRƯỚC KHI gửi bất kỳ thẻ `MEDIA:<path>` nào cho người dùng, Agent BẮT BUỘC phải dùng `browser_vision` mở trực tiếp file ảnh đó lên, phóng to soi kỹ 4 câu hỏi:
    1. Chữ gốc đã bị xóa sạch hoàn toàn bên dưới chữ dịch chưa? Có bị chữ cũ lòi ra ngoài không?
    2. Chữ dịch mới có nằm đúng vị trí trung tâm/thẳng hàng không, hay bị bay dạt ra ngoài mép?
    3. Con dấu đỏ, mã QR, logo chứng nhận và sơ đồ kỹ thuật có bị hộp xóa màu trắng cắt xén mất góc không?
    4. Có bất kỳ hiện tượng chữ in đè lên chữ cũ (double-print / ghosting) không?
    Nếu có bất kỳ lỗi nào trong 4 điều trên, NGHIÊM CẤM gửi ảnh và NGHIÊM CẤM báo "hoàn thành". Phải sửa script và render lại ngay.

- **The In-Place Table Ruin Pitfall vs Clean Vector Re-typeset (Lẹm viền đứt nét bảng vs Bản dựng lại Vector):**
  * *Triệu chứng:* Khi vẽ đè hộp trắng (bounding box inpainting) lên các báo cáo thử nghiệm hoặc bảng biểu kỹ thuật dày đặc (Test Report), các hình chữ nhật màu trắng xóa lẹm vào đường kẻ viền bảng, làm đứt đoạn, mất khung viền, trông nham nhở như dán đề-can chắp vá. Đồng thời, văn bản tiếng Việt dài hơn chữ Hán khiến thuật toán co chữ ép cỡ chữ xuống 6–7pt dính chùm, cực kỳ khó đọc.
  * *Bẫy phủ hộp tối (Redaction Bar Trap):* Tuyệt đối KHÔNG khắc phục bằng cách vẽ các khối chữ nhật màu tối/bán trong suốt (`fill=(0.04, 0.08, 0.12)`) đè lên nền scan — tài liệu sẽ trông giống hệt văn bản mật bị kiểm duyệt bôi đen (censorship redaction bars), hoàn toàn phản cảm và không thể sử dụng.
  * *Giải pháp tối ưu (Re-typeset Vector via python-docx & Word Engine):* Với các báo cáo thử nghiệm (Test Report) hoặc hồ sơ kiểm định kỹ thuật có nhiều bảng biểu phức tạp:
    1. Dựng lại tài liệu sạch hoàn toàn bằng `python-docx`: khổ A4, căn lề chuẩn 2cm/2.5cm, bảng biểu kẻ viền đen nét căng (0.5pt solid), padding ô rộng rãi, font Times New Roman 10–11pt cho bảng và 12–13pt cho tiêu đề.
    2. Cắt (crop) toàn bộ hình ảnh sản phẩm thực tế, biểu đồ phân bố tia nước, tem mã QR và con dấu đỏ chính thức (CMA, CNAS, CCCF, dấu tròn cơ quan) từ file scan gốc bằng PIL chèn vào đúng vị trí tương ứng.
    3. Chuyển đổi sang file PDF Vector 100% sắc nét thông qua Microsoft Word engine có sẵn trên Windows (`win32com.client.Dispatch('Word.Application')` -> `wb.ExportAsFixedFormat(out_pdf, 17)`). Tài liệu xuất ra vừa có bản `.docx` để khách hàng hiệu đính, vừa có bản `.pdf` vector in ấn nét căng, không một vết lem.

- **PCCC Official Terminology & Symbol Invariants (Bảng chuẩn hóa thuật ngữ kiểm định PCCC & Thể thức):**
  * *Ký hiệu nhiệt độ:* Tuyệt đối CẤM dùng ký tự Unicode đơn lẻ `℃` (U+2103) vì hầu hết font hệ thống và trình đọc PDF sẽ biến nó thành ô vuông lỗi `□` (`T-ZSTZ 80-68□ Q5`). BẮT BUỘC dùng ký hiệu độ chuẩn `°C` (dấu độ `°` + chữ `C`).
  * *Thuật ngữ chuyên ngành theo TCVN 6305:*
    - `溅水盘` (Deflector): BẮT BUỘC dịch là **"Tấm tán nước"**, TUYỆT ĐỐI CẤM dịch thành "tấm định hướng".
    - `动作元件`: **"Phần tử kích hoạt"** (Operating element).
    - `型式试验`: **"Thử nghiệm kiểu loại"** (Type test).
    - `认证单元`: **"Nhóm chứng nhận"** (Certification unit/family).
    - `出水口口径`: **"Đường kính lỗ phun"** (Orifice diameter).
    - `街道` (trong địa chỉ pháp lý Trung Quốc): BẮT BUỘC dịch là **"phường"** (ví dụ: *phường Khê Mỹ, thành phố Nam An, tỉnh Phúc Kiến*), không để phiên âm Hán-Việt thô "nhai đạo Khê Mỹ".
  * *Nhất quán tên pháp nhân & tiêu đề:*
    - Tên công ty: Thống nhất duy nhất: **"Công ty TNHH Phòng cháy chữa cháy Thiên Thái Phúc Kiến"** (Fujian Tiantai Fire-Fighting Co., Ltd.) hoặc viết tắt thống nhất **"Công ty TNHH PCCC Thiên Thái Phúc Kiến"** trên toàn bộ 18 trang, không đảo thành "Phúc Kiến Thiên Thái" và không dùng lộn xộn giữa các trang.
    - Tiêu đề: Thống nhất **"BÁO CÁO THỬ NGHIỆM"** cho toàn bộ báo cáo kiểm định; **"GIẤY CHỨNG NHẬN SẢN PHẨM PHÒNG CHÁY CHỮA CHÁY"** cho chứng chỉ CCCF (loại bỏ triệt để lỗi lặp từ "chứng nhận chứng nhận").
  * *Bẫy địa chỉ theo từng trang (Page-Aware Address Trap):*
    - Trong báo cáo PCCC, địa chỉ liên lạc của doanh nghiệp tại trang 4, 6 (`通讯地址`: *Khu phát triển Thành Công, TP Nam An*) KHÁC VỚI địa chỉ đăng ký trên Giấy chứng nhận tại trang 16–18 (`住所`: *khu Bành Mỹ, phường Khê Mỹ, TP Nam An*).
    - CẤM chạy replace chuỗi địa chỉ toàn cục (global regex) làm ghi đè địa chỉ phường Khê Mỹ lên trang 4 và 6; phải phân định theo số trang `page_number`.
  * *Đối soát danh mục model phụ lục (Appendix Model Audit):* Trên các phụ lục chứng chỉ kiểm định (như Trang 18), danh mục các model được phê duyệt thường bị con dấu đỏ đè mờ (ví dụ model `115-107`). Phải đối soát quang học kỹ lưỡng để không đọc sót hay ghi nhầm model được cấp phép trong hồ sơ thầu.

- **Subagent / Worker Script Generation Invariant (Self-Contained Code Injection):**
  * *Triệu chứng:* Khi giao task subagent tạo script Python lớn (`TASK_KIND: CREATE`, ví dụ `generate_clean_report.py`) để dựng tài liệu Word (`python-docx`), PDF vector (`win32com.client`) và ảnh preview (`pymupdf`), nếu chỉ đưa mô tả mục tiêu mà không cung cấp mã nguồn khung sẵn trong prompt, subagent sẽ tiêu tốn toàn bộ ngân sách tool calls (budget <= 10) để thăm dò file dữ liệu, kiểm tra môi trường, và hết ngân sách trước khi kịp viết file hoàn chỉnh.
  * *Khắc phục:* Khi điều phối task tạo script tự động hóa tài liệu nhiều trang phức tạp (18 trang), Coordinator BẮT BUỘC cung cấp sẵn cấu trúc code mẫu hoặc chia nhỏ thành 2 pha rõ ràng: Pha 1 kiểm tra dữ liệu/asset (INVESTIGATE), Pha 2 ghi file hoàn chỉnh bằng `write_file` ngay turn 1 kèm script tự chạy và tự nghiệm thu.
  * *Khổ giấy và bảng biểu Word (`python-docx`):* A4 (21 x 29.7cm), margins trên/dưới 2cm, trái 2.5cm, phải 2cm. Viền bảng 0.5pt, header shading xám nhạt (`#F2F2F2`), toàn bộ văn bản dùng font Times New Roman, phân trang rõ ràng theo đúng trang tài liệu gốc.

- **Review Loop:** Use Claude CLI or an LLM audit pass on batches to double check technical standards (TCVN, GB, NFPA, thread standards like G vs Rp vs NPT).

- **9Router / Local Proxy SSE Streaming & Multipart JSON Handling:**
  * *Triệu chứng:* Khi gửi request Vision lên proxy cục bộ (ví dụ cổng 20128), gọi `json.loads(resp.read().decode())` có thể văng lỗi `Extra data: line X column Y` do proxy phản hồi dạng Server-Sent Events (SSE) `data: {...}` hoặc nhiều chunk JSON nối tiếp nhau.
  * *Khắc phục:* Luôn hỗ trợ bóc tách kép:
    1. Thử `json.loads(raw)`.
    2. Nếu văng lỗi, tách dòng duyệt các dòng bắt đầu bằng `data: ` (bỏ qua `[DONE]`), parse từng payload để gom `delta["content"]` lại thành chuỗi hoàn chỉnh.
    3. Trích xuất mảng JSON bằng cách tìm index `[` đầu tiên và `]` cuối cùng (`raw[raw.find('['):raw.rfind(']')+1]`), kết hợp `json_repair`.

- **Hermetic Shell & Điều phối Subagent an toàn:**
  * *Cấm chuỗi nhạy cảm trong prompt:* Tuyệt đối không nhét các chuỗi đường dẫn cấu hình nhạy cảm (như thư mục profile hệ thống, file khóa bảo mật, thư mục guard) vào tham số `context`/`goal` của `delegate_task` để tránh kích hoạt cơ chế bảo vệ tự động. Sử dụng hàm nạp API key gián tiếp (`get_ninerouter_api_key()`).
  * *Hermetic Shell Metacharacters:* Terminal của worker subagent bị cấm các ký tự điều khiển shell (toán tử nối lệnh, pipe, redirect file). Lệnh chạy python phải là lệnh đơn trực tiếp không qua shell pipe.
  * *Self-Contained Code Injection:* Khi giao worker tạo script công cụ mới (`TASK_KIND: CREATE`), BẮT BUỘC cung cấp toàn bộ mã nguồn hoàn chỉnh sẵn sàng ghi vào prompt, chỉ thị worker gọi `write_file` ngay ở iteration 1 để tránh việc worker chạy lang thang tìm file cấu hình dẫn đến timeout 180s.
