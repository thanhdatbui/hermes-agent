---
name: inbound-vision-gate-architecture
description: "Kiến trúc Pre-flight Ground Truth Sentinel chống hallucination và KV Cache Bias khi người dùng gửi ảnh vào Gateway."
---
# Inbound Vision Gate: Tri-State Failure Analysis & Mechanical Hard Sentinel

## 1. Hiện Tượng & Cơ Chế Lỗi Gốc (Root Cause)
Khi một phiên trò chuyện (session) kéo dài và thảo luận liên tục về một chủ đề cụ thể (ví dụ: ngách chó cún, avatar thú cưng), mô hình Transformer gặp hiện tượng **Autoregressive KV Cache Bias**:
- Lịch sử token văn bản trước đó chiếm ưu thế áp đảo trong Attention window.
- Khi người dùng gửi một bức ảnh hoàn toàn mới (ví dụ: ảnh 2 người đàn ông trong nhà hàng, ảnh vòi nước Kangen Water) kèm câu thoại cộc lốc hoặc chửi bới, token văn bản không cung cấp neo ngữ nghĩa mới.
- Mô hình chọn con đường tốn ít suy luận nhất: **tiếp tục mạch văn tự sự cũ (sequence continuation)** và bịa đặt nội dung ảnh mới để khớp với ngữ cảnh cũ ("chú cún nằm trọn ở giữa, lông nét căng"), bất chấp ma trận pixel thực tế là người hoặc đồ vật.

---

## 2. Thất Bại Của 3 Thế Hệ Gate Trước Đó (Audit Trail Qua Hơn Chục Session)

| Thế hệ | Cơ chế triển khai | Lý do thất bại |
| :--- | :--- | :--- |
| **Pha 1: Ép gọi Tool** | Viết `INBOUND_VISION_GATE` tại `gateway/run.py` bắt buộc mọi turn có ảnh phải có tool call `browser_vision` / `vision_analyze`. | **False-Blocking 100%:** Mô hình Telegram chạy Native Multimodal Vision (ảnh nhúng trực tiếp base64 vào payload turn). Vì đã nhìn bằng multimodal nên mô hình không phát sinh tool-call $\rightarrow$ Gate chặn oan mọi câu trả lời. |
| **Pha 2: Bypass Native** | Thêm điều kiện: `if _img_mode == "native": _inbound_has_img = False` để chống False-Blocking. | **Cửa sau vô hiệu hóa toàn bộ:** Cờ `_inbound_has_img` bị tắt ngấm với mọi model native vision $\rightarrow$ Gate không kiểm tra gì nữa, mô hình tự do hallucinate lọt ra Telegram. |
| **Pha 3: WinRT OCR thô** | Dùng PowerShell WinRT OCR (`ocr_boxes.ps1`, `run_winrt_ocr.py`) làm bằng chứng cứng. | **Mù tịt trước ảnh không có text:** 1) WinRT StorageFile API crash `null pointer` nếu đường dẫn chứa forward slash `/` (bắt buộc Windows native backslash `\`). 2) Gặp ảnh thuần cảnh/người không có chữ (OCR trả về `OK_EMPTY`) thì hoàn toàn mất tác dụng kiểm tra chéo ngữ nghĩa thị giác. |

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/outbound-attestation-workflow.md`: Hướng dẫn chi tiết quy trình Outbound Attestation Workflow.
> - `references/outbound-manifest-attestation-gate.md`: Cơ chế cơ giới hóa Outbound Manifest Attestation Gate (check_contradiction) chặn đứng lỗi cắt ảnh người mà mồm bốc phét là cún cưng (commit 7df1c2a).
> - `references/ground-truth-video-vs-excel-bias-20261104.md`: Kỷ luật mỏ neo video thật thắng mọi nhãn Excel và quy trình sửa dứt điểm Niche sai lệch.
