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
* **Quy chuẩn kiểm tra Ground Truth:**
  - Tuyệt đối không suy diễn từ bảng cấu hình proxy/gateway.
  - **Cách 1 (Trực tiếp qua CDP/Browser):** Mở `https://one.google.com/storage`. Xác nhận bằng chứng dung lượng thực tế:
    - `0 GB/5 GB` hoặc `0 GB/15 GB` kèm nút mời chào nâng cấp (`Nâng cấp lên 30 GB...`) -> **100% Sạch gói (Free)**.
    - Huy hiệu `Pro`, dung lượng `2 TB` hoặc `5 TB` -> **Đã có gói Pro**.
  - **Cách 2 (Offline qua CSDL History của GPM Profile):** Quét file SQLite `Default/History` của profile trong thư mục GPM:
    - Nếu có bản ghi `one.google.com/activate-plan` hoặc `one.google.com/celebration` -> **Đã từng kích hoạt gói Pro**.

## 2. Kỷ Luật Loại Trừ Tam Giác Khi Cấp Gmail Thường (Tri-Layer Clean Account Exclusion)
- **Bẫy cấp nhầm acc Pro cho tác vụ thường:** User yêu cầu "acc Google thường, không Pro, không dính TikTok", nếu Coordinator tra cứu ẩu sẽ bốc nhầm các acc Pro như `dokieu` (`gemini-web-pro`), `votuyen`, `giangkim` (`ag-gemini-pool-3`).
- **Quy tắc cơ học O(1):** Bắt buộc chạy đối soát loại trừ đồng thời 3 lớp:
  1. Loại trừ TikTok: `email NOT IN (SELECT email FROM tiktok_accounts)`.
  2. Loại trừ OmniRoute Pro: `email NOT IN (SELECT email FROM provider_connections WHERE tier LIKE '%pro%' OR provider_specific_data LIKE '%pro%')` VÀ không nằm trong bất kỳ combo Pro nào (`ag-gemini-pool-3`, `gemini-web-pro`).
  3. Khớp nối GPM: Phải có sẵn profile trên GPM API `:19995` kèm mật khẩu trong `mailboxes`.
- Chi tiết tra cứu xem: `references/tri-layer-clean-account-exclusion-discipline.md` và `references/gpm-live-google-session-verification-and-tri-clean-gate.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
