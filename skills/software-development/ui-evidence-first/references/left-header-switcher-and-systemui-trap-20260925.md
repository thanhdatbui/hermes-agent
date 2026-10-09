# Left-Header Switcher Anchor, SystemUI Status Bar Trap & TikTok v47.x Layout Variants (2026-09-25)

## 1. Hiện tượng & Vấn đề thực tế (Incident Máy 76)

### Sự cố 1: Nhận diện nhầm icon Wifi trên Status Bar (`com.android.systemui:id/wifi_combo`)
* Trong `automation_core.tiktok.account_switcher.find_switcher_anchor()`, khi không có exact identity match, bộ chọn `generic_candidates` quét tìm node header ở dải trên cùng (`center_y <= generic_header_y` và `header_left <= center_x <= header_right`).
* **Bẫy:** Node `com.android.systemui:id/wifi_combo` có bounds `[723, 14][773, 56]` (center `[748, 35]`). Tọa độ này thỏa mãn `300 <= 748 <= 780` và `35 <= 320`.
* Do thiếu điều kiện lọc bỏ package hệ điều hành (`node.attributes.get("package") != "com.android.systemui"`), `find_switcher_anchor` trả về node Wifi icon. Lệnh tap sau đó bấm trúng thanh trạng thái Android thay vì Profile header, khiến bottom sheet Switcher không bao giờ mở được.

### Sự cố 2: Lệch tọa độ trên Layout Left-Header / Right-Avatar (TikTok v47.x)
* Trên TikTok truyền thống, Display Name và Username nằm ở giữa (`center_x` từ 300 đến 780). `_PROFILE_HEADER_X_RATIO = (300 / 1080, 780 / 1080)` ép buộc `header_left <= center_x <= header_right`.
* Trên layout mới của TikTok v47.x (ví dụ Máy 76):
  + Avatar nằm lệch sang bên phải: `bounds=[708,300][1080,636]`.
  + Nút Tên hiển thị (`resource-id="com.ss.android.ugc.trill:id/t7l"`): `bounds=[36,280][329,364]`, `center=(182, 322)`, `clickable="true"`.
  + Nút Username (`resource-id="com.ss.android.ugc.trill:id/t3y"`): `bounds=[36,370][256,415]`, `center=(146, 392)`, `clickable="true"`.
* Điều kiện cứng `header_left <= center_x` (182 >= 300 -> False) khiến toàn bộ các node hợp lệ của profile bị loại bỏ hoàn toàn.

---

## 2. Kỷ luật Bất Biến (Anti-Chế Bậy / Anti-Ad-hoc Bypass)

* **User Invariant:** Hệ thống đã thiết kế canonical `account_switcher` trong `automation-core`. Khi switcher không mở được trên một layout mới, BẮT BUỘC phải sửa và nâng cấp `automation-core` để module nhận diện được layout đó.
* **CẤM TUYỆT ĐỐI** tự chế ra các đường vòng ad-hoc bằng tay (như đề xuất đi vòng qua Menu 3 gạch -> Cài đặt & Quyền riêng tư -> Cuộn đáy -> Chuyển đổi tài khoản) thay vì sửa triệt để bộ nhận diện switcher anchor.

---

## 3. Quy chuẩn Khắc phục Mã Nguồn (Code Contract)

1. **Loại trừ 100% SystemUI:**
   Mọi candidate trong `find_switcher_anchor` (resource, preferred, identity, generic) BẮT BUỘC kiểm tra:
   ```python
   if node.attributes.get("package", "").casefold() == "com.android.systemui":
       continue
   ```

2. **Hỗ trợ Layout Left-Header / Right-Avatar:**
   Khi node khớp resource ID chuẩn (`_SWITCH_ANCHOR_RESOURCE_SUFFIXES`) hoặc khớp identity (`preferred_values` / `identity_values`):
   * Cho phép `center_x <= header_right` (thay vì bắt buộc `header_left <= center_x`).
   * Giữ giới hạn dọc `center_y <= identity_y`.

3. **Bổ sung Resource-ID Suffixes v47.x:**
   Cập nhật `_SWITCH_ANCHOR_RESOURCE_SUFFIXES` với các ID mới:
   `"t7l"`, `"t3y"`, `"sai"`, `"sv6"`, `"s7w"`, `"s8k"`.
