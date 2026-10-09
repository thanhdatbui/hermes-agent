# TikTok Profile Tab Resolution & PROFILE_ROOT_NOT_CONFIRMED Recovery

## Bối cảnh & Hiện tượng (2026-09-13)
- Hàng loạt máy (28/78 máy Ca 3 Row 5) dính lỗi `PROFILE_ROOT_NOT_CONFIRMED` khi chạy TikTok workflow.
- Nguyên nhân: 
  1. `profile_tab` resource-id cũ `com.ss.android.ugc.trill:id/profile_tab` đã đổi trên các build TikTok mới thành `com.ss.android.ugc.trill:id/oly`.
  2. Khi fallback sang text `'Hồ sơ'`, `_find_ui_element` lấy node đầu tiên match substring một cách mù quáng, dẫn đến việc nhặt nhầm avatar creator ở giữa feed video (ví dụ text/content-desc: `'Hồ sơ BEN EAGLE'`) tại toạ độ cao trên màn hình thay vì nút tab Hồ sơ dưới cùng bên phải.

## Yêu cầu lọc Bottom-Nav bắt buộc cho `tap_profile`
Mọi nhánh match tab Profile (resource-id `oly`, text `'Hồ sơ'`, content-desc) **BẮT BUỘC** lọc theo toạ độ bottom navigation:
1. **Toạ độ Y**: `center_y >= 0.8 * screen_height` (với màn 1080x1920 thì `y >= 1536`).
2. **Toạ độ X**: `center_x >= 0.75 * screen_width` (vùng tab góc phải cùng, `x >= 810` với màn 1080).
3. **Thuộc tính UI**: `visible-to-user=true`, `enabled=true`.
4. **Duyệt danh sách node**: CẤM lấy node đầu tiên mà không kiểm tra. Nếu node đầu tiên không thoả mãn bottom-nav, tiếp tục duyệt các node kế tiếp.

## Chuẩn hoá Content-Desc
- **CẤM** match partial substring kiểu `'hồ sơ'` trong content-desc vì sẽ dính `'hồ sơ BEN EAGLE'`.
- **CHỈ CHẤP NHẬN** exact match sau khi strip và lowercase:
  `content_desc.strip().lower() in ("hồ sơ", "profile")`

## Selector Resource-ID
- Cập nhật `ui_profile.py`:
  `resource_id="com.ss.android.ugc.trill:id/oly"`
- Trong adapter / fallback chain: thử resource-id `com.ss.android.ugc.trill:id/oly` trước, sau đó fallback sang `com.ss.android.ugc.trill:id/profile_tab` cũ nếu cần tương thích ngược.
