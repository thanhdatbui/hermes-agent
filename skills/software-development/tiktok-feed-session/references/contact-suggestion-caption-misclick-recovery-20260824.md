# Contact Suggestion False Positive and Caption Close Misclick (2026-08-24)

## Triệu chứng & Bối cảnh
- Máy farm (ví dụ Máy 25, nick `thao.phan206`) đang lướt For You feed thì dừng phiên với cảnh báo:
  `🚨 [MÁY 25] DỪNG PHIÊN`
  `• Script: multi-machine-feed-session`
  `• Lý do: manual review required after contact_follow_suggestion dismiss: unknown`
- Ảnh hiện trường: Màn hình tìm kiếm TikTok (`devincaherlyc`) kèm bàn phím ảo bật lên.

## Nguyên nhân gốc rễ (Root Cause)
1. **False positive popup detection:**
   - Detector `detect_contact_follow_suggestion` trong `automation-core` chứa keyword `"đề xuất"`.
   - Khi ở tab For You (`Đề xuất`), classifier bắt nhầm header tab này thành `contact_marker`.
   - Kết hợp với nút `Follow <creator>` bên phải màn hình tạo thành `follow_marker`.
2. **Bắt nhầm caption video thành nút Đóng:**
   - Video có caption: `Chúng ta có thể đóng gói Lamine Yamal không??#Devincaherly #…thêm` (resource-id `id/desc`).
   - Hàm `_element_contains` khi tìm `"đóng"` dùng regex đơn giản hoặc substring, dẫn đến khớp từ `"đóng"` bên trong `"đóng gói"`.
   - Script tap thẳng vào caption video $\rightarrow$ kích hoạt mở trang Tìm kiếm / Hashtag.
   - Sau khi tap, màn hình không còn là popup/feed $\rightarrow$ dừng phiên fail-closed.
3. **Quy tắc xử lý CTA quảng cáo / Feed Ad:**
   - Đối với CTA quảng cáo / Shop CTA in-feed: Ưu tiên vuốt lướt qua thẻ quảng cáo (`swipe`), tuyệt đối không cố tìm và tap nút đóng gây rủi ro bấm nhầm CTA mua hàng hoặc caption.

## Giải pháp kỹ thuật đã áp dụng (`automation-core`)
1. **Siết chặt detector `detect_contact_follow_suggestion`:**
   - Xóa bỏ keyword đơn lẻ `"đề xuất"`, `"gợi ý"`, `"liên hệ"`.
   - Chỉ match các cụm rõ ngữ cảnh gợi ý kết nối: `"tài khoản được đề xuất"`, `"người mà bạn có thể biết"`, `"people you may know"`, `"liên hệ từ danh bạ"`, `"đồng bộ danh bạ"`, `"trong danh bạ"`, `"gợi ý follow"`, `"gợi ý tài khoản"`, `"follow bạn bè của bạn"`.
2. **Loại trừ caption/desc khỏi dismiss targets:**
   - Bỏ qua các element có resource-id kết thúc bằng `:id/desc` (`filtered_elements = [el for el in elements if not (el.resource_id or "").endswith(":id/desc")]`).
3. **Chuẩn hóa word-boundary trong `_element_contains`:**
   - Dùng pattern `r"(?i)(?:\b|(?<=[\s,;.!?]))" + re.escape(term_clean) + r"(?:\b|(?=[\s,;.!?]))"` để đảm bảo `"đóng"` không khớp `"đóng gói"`.
