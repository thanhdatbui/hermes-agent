---
name: google-account-trust-and-subscription-audit
description: "Kỷ luật đối soát gói Google One / Gemini Pro thực tế và phân định cấp độ Trust Score giữa Gmail Farm Batch vs Gmail Ngoại Cổ (Aged 5-6 năm)."
---
# Google Account Trust & Subscription Audit

## 1. Cạm Bẫy Kiểm Tra Gói Google One / Gemini Pro (Anti-False Assumption)
* **Bẫy sai sót:** Chỉ truy vấn bảng `provider_connections` với điều kiện `provider = 'gemini-web'` trong CSDL OmniRoute (`storage.sqlite`) rồi vội vàng kết luận tài khoản "chưa có gói Pro". Hoặc thấy lỗi `403 TOS_VIOLATION` ở Cloud Code API vội kết luận tài khoản Pro đã bị die.
* **Bản chất thực tế khi dính 403 TOS_VIOLATION:**
  - Gói Google One / Gemini Web Pro (2 TB / 5 TB) vẫn sống 100% trên `gemini-web-argon-pool`.
  - Chỉ cổng Cloud Code API (`cloudcode-pa.googleapis.com`) bị khóa do bot quét chữ ký "Hermes Agent / Nous Research" kết hợp TLS proxy Node.js.
  - Xem quy trình kháng nghị và giải cứu tại `references/cloudcode-tos-403-appeal-and-hermes-signature-hygiene.md`.
* **Phân định 403 TOS_VIOLATION vs 403 VALIDATION_REQUIRED:**
  - `TOS_VIOLATION`: "This service has been disabled for violation of Terms of Service" -> Bị tắt quyền Cloud Code API, cần nộp form appeal (Forms nội bộ Google Cloud Code).
  - `VALIDATION_REQUIRED` (như ca `votuyen`): "Verify your account to continue" -> Hết hạn phiên session/OAuth, cần S7 Offline Security Code 10 số, cấm nhầm lẫn với ToS ban.
* **Cơ chế Prompt Cache vs Context Compression (protect_last_n):**
  - Prompt Cache của Gemini đạt ~97.5% giúp giảm chi phí tính toán phía Google, nhưng KHÔNG giảm dung lượng upload JSON qua mạng.
  - Hạ `protect_last_n: 20` xuống `6` để giữ 3 turns tool gần nhất nguyên vẹn cho reasoning, trong khi rút ruột các log terminal/read cũ thành 1-line summary, tránh phình payload upload gây HTTP 499.
  - Tuyệt đối cấm đặt `protect_last_n: 0` vì sẽ làm mất dữ liệu đầu vào của tool vừa chạy, đẩy agent vào infinite loop hoặc hallucination.
  - Trong Combo Router OmniRoute, giữ `stickyRoundRobinLimit: 10-15` để bảo vệ Prompt Cache xuyên suốt chuỗi tool-call của 1 lượt chat, kết hợp `least-used` để dãn tải xoay vòng khi hết chu kỳ.
* **Quy chuẩn kiểm tra Ground Truth:**
  - Tuyệt đối không suy diễn từ bảng cấu hình proxy/gateway.
  - **Cách 1 (Trực tiếp qua CDP/Browser):** Mở `https://one.google.com/storage`. Xác nhận bằng chứng dung lượng thực tế:
    - `0 GB/5 GB` hoặc `0 GB/15 GB` kèm nút mời chào nâng cấp (`Nâng cấp lên 30 GB...`) -> **100% Sạch gói (Free)**.
    - Huy hiệu `Pro`, dung lượng `2 TB` hoặc `5 TB` -> **Đã có gói Pro**.
  - **Cách 2 (Offline qua CSDL History của GPM Profile):** Quét file SQLite `Default/History` của profile trong thư mục GPM:
    - Nếu có bản ghi `one.google.com/activate-plan` hoặc `one.google.com/celebration` -> **Đã từng kích hoạt gói Pro**.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
