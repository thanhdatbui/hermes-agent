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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
