# UI XML Substring Collision & Sound Detail Recovery Guards (2026-08-21)

## Context & Incident (Máy 45, TikTok Feed Session)
Trong quá trình chạy feed session trên máy 45, thiết bị bất ngờ nhảy sang màn hình chi tiết bài hát/âm thanh ("Closer", kèm các nút "Sử dụng âm thanh", "Thêm vào Nhật ký", list video mẫu).

## Root Cause Analysis
1. **Lớp nhận diện popup (`detect_contact_follow_suggestion` trong `automation_core.tiktok.benign_popup`):**
   - Quét từ khóa substring quá lỏng (`"đề xuất"`, `"follow"`).
   - Trên Feed TikTok bình thường, header luôn có 2 tab: `"Đã follow"` và `"Đề xuất"`.
   - Kết quả: Flow tưởng nhầm Feed bình thường là popup gợi ý kết bạn (`contact_follow_suggestion`).

2. **Lớp tìm nút đóng (`_find_clickable_text` trong `automation_core.tiktok.benign_popup`):**
   - Danh sách từ khóa tìm nút đóng có `("đóng", "close")`.
   - Hàm so khớp bằng `term.lower() in value.lower()`.
   - Video trên feed phát bài hát "Closer", nút đĩa nhạc ở góc phải dưới (`com.ss.android.ugc.trill:id/p89`, `[918, 1631][1080, 1793]`, center `[999, 1712]`) có thuộc tính: `content-desc="Âm thanh: Closer của hppr & Hollis Lane"`.
   - Do `"close"` nằm trong `"Closer"`, hàm nhận diện nhầm nút đĩa nhạc thành nút đóng và tap trúng tâm node `[999, 1712]` -> bay sang Sound Detail.

## Two-Tier Invariant & Fixes

### Tier 1: Sửa logic trong `automation-core` (Root prevention)
- **Word boundary / Exact match cho từ khóa ngắn:** Các từ như `"close"`, `"đóng"` trong `_find_clickable_text` phải so khớp theo từ độc lập (regex `\bclose\b` hoặc exact match), hoặc loại trừ các resource-id / content-desc của đĩa nhạc (`id/p89`, `"Âm thanh:"`, `"Sound:"`).
- **Ngữ cảnh popup:** `detect_contact_follow_suggestion` không được kích hoạt chỉ bởi các tab header ("Đã follow", "Đề xuất") nếu không có dialog/bottom sheet thực sự.

### Tier 2: Auto-Recovery Handler trong Consumer (`tiktok-luot nuoi acc`)
- Đăng ký `sound_detail_overlay` (priority 78) vào `BENIGN_POPUP_REGISTRY` mặc định tại `benign_popup_registry.py`.
- Detector: Quét markers `"Sử dụng âm thanh"`, `"Use this sound"`, `"Thêm vào Nhật"`, `"Thêm vào Mục ưa thích"`.
- Dismisser: Gửi phím `Back` (hoặc tap nút quay lại) để thoát trang âm thanh và quay trở về video feed ngay lập tức, tránh bị kẹt session.
