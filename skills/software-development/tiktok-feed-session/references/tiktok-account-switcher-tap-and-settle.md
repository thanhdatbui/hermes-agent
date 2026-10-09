# Pitfall & Quy chuẩn Tap Switch Account Row trong TikTok Account Switcher

## 1. Hiện tượng & Triệu chứng lỗi (Case Study Máy 79, Run 20260907-032253)
- Mở Account Switcher bottom sheet thành công (hiển thị danh sách tài khoản).
- Script log `tap_expected_account` thành công nhưng tài khoản trên màn hình Profile sau đó KHÔNG thay đổi (vẫn giữ tài khoản cũ).
- Sau 2 lần retry switch thất bại, runner báo `profile username still mismatched after switch` và kích hoạt nhầm auto-login recovery.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi tọa độ tap trúng vào inner non-clickable child TextView:**
   - Trong UI XML của TikTok, mỗi row trong danh sách switcher có cấu trúc:
     ```xml
     <node resource-id="com.ss.android.ugc.trill:id/l9b" class="android.widget.Button" 
           content-desc="<username>" clickable="true" bounds="[0, y1][1080, y2]">
       <node resource-id="com.ss.android.ugc.trill:id/mtx" class="android.widget.TextView" 
             text="<username>" clickable="false" bounds="[252, y1_inner][543, y2_inner]" />
     </node>
     ```
   - **Anti-Pattern:** Trong `feed_swipe_smoke.py`, logic `_find_account_switch_option` từng override `best_bounds = inner.bounds` với giả định "tap trực tiếp lên username TextView thay vì khoảng trống bên phải".
   - Kết quả: Lệnh `input tap` rơi vào `(397, y)`, trúng vào TextView có `clickable="false"` khiến TikTok không nhận click listener trên `Button id/l9b`.
2. **Lỗi ngắt quãng animation / settle của Switcher do tap vội Bottom Nav:**
   - Trong `verify_and_switch_profile`, ngay sau khi tap switch row, script gọi `_navigate_profile_for_preflight(...)` dẫn đến tap Profile bottom tab `[972, 1857]`.
   - Nếu bottom sheet chưa kịp settle hoặc đang animate đóng, tap vào `[972, 1857]` rơi trúng vào nút "Thêm tài khoản" (`bounds [0, 1680][1080, 1896]`), hoặc làm dismiss/cancel tiến trình switch tài khoản của TikTok.

## 3. Quy chuẩn sửa đổi & Best Practices
1. **Không override bounds vào child view không clickable:**
   - Đối với account switcher row, target tap BẮT BUỘC là container node có `clickable="true"` (`node.bounds` từ `find_exact_account`, center x=540 hoặc avatar x~120).
   - Tuyệt đối cấm gán `best_bounds = inner.bounds` của TextView con không nhận click.
2. **Chờ Switcher Sheet tự đóng (Settle Timing):**
   - Khi tap chọn tài khoản khác trên Switcher, TikTok sẽ xử lý reload profile và tự đóng bottom sheet.
   - Script phải chờ và poll cho đến khi `is_switcher_open == False` (timeout 4-6s) thay vì vội vàng tap lại navigation bar.
3. **Không tap lại Profile Tab nếu đang ở trên màn hình Profile:**
   - Vì Switcher được mở từ chính Profile screen, sau khi switcher đóng thì thiết bị đã ở Profile tab, không cần tap lại `_profile_target()` gây conflict UI.
