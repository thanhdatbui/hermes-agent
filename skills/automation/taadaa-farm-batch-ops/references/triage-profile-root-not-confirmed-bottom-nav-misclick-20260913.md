# Triage & Recovery: PROFILE_ROOT_NOT_CONFIRMED (Tap Profile Tab Misclick in Inbox)

## Hiện tượng & Dấu hiệu nhận biết
- Trong Ca nuôi/đăng video TikTok, hàng loạt máy (ví dụ 28/78 máy Ca 3 Row 5 ngày 13/09/2026) báo lỗi:
  `[ACCOUNT_SWITCHER_FAILED] open_profile_root failed: PROFILE_ROOT_NOT_CONFIRMED: Profile root was not confirmed. Cần MANUAL_REVIEW`
- Trong `execution.log` xuất hiện các dòng:
  `[TAP_PROFILE] Phát hiện Feed video overlay; tap Hộp thư (756, 1857) để chuyển ngữ cảnh trước`
  theo sau bởi:
  `[TAP_PROFILE] Tap profile tab by text 'Hồ sơ': (573, 1587)` hoặc `(595, 322)`
  thay vì tọa độ góc dưới phải `(972, 1857)` hay `(972, 1883)`.
- Sau đó máy rơi vào vòng lặp `Back recovery 1/12, 6/12...` do lạc vào subpage của Inbox/Feed, hết số lần retry dẫn đến crash hoặc gọi soft-reboot thất bại.

## Nguyên nhân cốt lõi
1. **Resource-ID lỗi thời:** Selector `profile_tab` trong `ui_profile.py` trước đây định nghĩa `com.ss.android.ugc.trill:id/profile_tab` — ID này không tồn tại trong các build TikTok mới, khiến nhánh resource-id luôn trượt.
2. **Resource-ID thật:** Container của tab Hồ sơ trên bottom-nav là `com.ss.android.ugc.trill:id/oly` (`[864,1794][1080,1920]`).
3. **Substring Matching mù quáng:** Khi trượt ID, code fallback sang `_find_ui_element(xml_text, text_contains="Hồ sơ")`. Node đầu tiên match lại là các notification hoặc creator avatar trong màn hình Hộp thư (hoặc Feed overlay) nằm ở nửa trên màn hình (y < 1500), dẫn đến tap nhầm vào subpage.
4. **Partial content-desc:** Nhánh `content-desc` cũ kiểm tra `"hồ sơ" in cd` bắt nhầm cả avatar creator `"Hồ sơ BEN EAGLE"`.

## Giải pháp chuẩn hóa (Commit `0eb0a58`)
1. **Cập nhật Selector (`ui_profile.py`):**
   `profile_tab` resource-id đổi thành `com.ss.android.ugc.trill:id/oly`.
2. **Bộ lọc tọa độ Bottom Navigation bắt buộc (`adapter.py`):**
   Mọi nhánh tìm tab Hồ sơ (`oly`, text `"Hồ sơ"`/`"Profile"`, content-desc) BẮT BUỘC phải thỏa mãn:
   - `visible-to-user != "false"` và `enabled != "false"`.
   - Tọa độ tâm: `center_x >= 0.75 * screen_width` (với 1080p là `cx >= 810`).
   - Tọa độ tâm: `center_y >= 0.80 * screen_height` (với 1920p là `cy >= 1536`).
3. **Duyệt toàn bộ node thay vì dừng ở node đầu:** Duyệt qua cây UI, chỉ chấp nhận node nằm trong vùng bottom-nav góc phải.
4. **Content-Desc Exact Matching:** Chỉ so khớp chính xác `cd in ("hồ sơ", "profile")`, cấm dùng substring `in`.
