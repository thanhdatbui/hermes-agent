---
name: google-account-trust-and-subscription-audit
description: "Kỷ luật đối soát gói Google One / Gemini Pro thực tế và phân định cấp độ Trust Score giữa Gmail Farm Batch vs Gmail Ngoại Cổ (Aged 5-6 năm)."
---
# Google Account Trust & Subscription Audit

## 1. Cạm Bẫy Kiểm Tra Gói Google One / Gemini Pro (Anti-False Assumption)
* **Bẫy sai sót:** Chỉ truy vấn bảng `provider_connections` với điều kiện `provider = 'gemini-web'` trong CSDL OmniRoute (`storage.sqlite`) rồi vội vàng kết luận tài khoản "chưa có gói Pro".
* **Bản chất thực tế:**
  - Các tài khoản được kích hoạt gói **Google AI Pro (5 TB / 2 TB)** trong farm còn được dùng làm nguồn tài nguyên cho nhánh `antigravity` (Google Cloud Code / Vertex AI OAuth) hoặc `codex`.
  - Có những tài khoản đã nhận thư "Chào mừng đến với Google AI Pro" từ Google One nhưng chưa được cấu hình vào OmniRoute.
* **Quy chuẩn kiểm tra Ground Truth:**
  - Tuyệt đối không suy diễn từ bảng cấu hình proxy/gateway.
  - **Cách 1 (Trực tiếp qua CDP/Browser):** Mở `https://one.google.com/storage`. Xác nhận bằng chứng dung lượng thực tế:
    - `0 GB/5 GB` hoặc `0 GB/15 GB` kèm nút mời chào nâng cấp (`Nâng cấp lên 30 GB...`) -> **100% Sạch gói (Free)**.
    - Huy hiệu `Pro`, dung lượng `2 TB` hoặc `5 TB` -> **Đã có gói Pro**.
  - **Cách 2 (Offline qua CSDL History của GPM Profile):** Quét file SQLite `Default/History` của profile trong thư mục GPM:
    - Nếu có bản ghi `one.google.com/activate-plan` hoặc `one.google.com/celebration` -> **Đã từng kích hoạt gói Pro**.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
