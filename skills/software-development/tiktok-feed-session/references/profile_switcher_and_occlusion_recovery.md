# Profile Switcher, Display Name Anchor, and System Occlusion Recovery

## 1. Samsung FOTA Popup (`com.wssyncmldm`) Occlusion
- **Hiện tượng:** Máy Samsung (đặc biệt cụm S7 Kibe/Admin) hiện popup thông báo cập nhật hệ điều hành FOTA `com.wssyncmldm` (activity `IDMUIDownloadConfirmDialog`), chiếm foreground khiến TikTok bị mất focus và fail pass `device_prepare`.
- **Root cause:** Hàm `recover_systemui_occlusion` trước đây chỉ bắt `com.android.systemui`, bỏ lọt `com.wssyncmldm`.
- **Giải pháp chuẩn:** Trong `python_runner/flows/device_prepare.py`, mở rộng danh sách nhận diện:
  `if focus.get("package") in ("com.android.systemui", "com.wssyncmldm"):`
  và gửi lệnh `input keyevent 4` (phím BACK) để đóng hộp thoại cập nhật hệ thống, trả lại quyền kiểm soát foreground cho ứng dụng mục tiêu (`com.ss.android.ugc.trill`).

## 2. Account Switcher Tap Target / Coordinate Drift
- **Hiện tượng:** Màn hình account switcher sheet hiện đủ 8 tài khoản, selector tìm đúng tài khoản mục tiêu nhưng bấm không ăn (TikTok vẫn giữ nguyên tài khoản cũ).
- **Root cause:** Hàng tài khoản trong sheet có bounds trải dài toàn bộ chiều rộng `[0, y1][1080, y2]`. Khi bấm vào tâm hình học `center[0] = 540`, vị trí tap rơi vào khoảng trống giữa text tên tài khoản và badge số thông báo unread `9+` bên mép phải (`resource-id: p05`), khiến sự kiện click không trúng vùng tương tác hoặc bị RecyclerView bỏ qua.
- **Giải pháp chuẩn:**
  - Trong `automation-core/src/automation_core/tiktok/account_switcher.py` (`select_exact_account`): Khi `node.bounds` có `bounds[0] == 0` và `bounds[2] >= 1000`, ghim tọa độ `tap_x = 350` (hoặc vùng `x <= 350`).
  - Trong `python_runner/flows/feed_swipe_smoke.py`: Tạo `UIElement` tap target giới hạn `bounds = (b[0], b[1], min(b[0] + 600, b[2]), b[3])` trước khi chuyển qua `_tap_ui_element`.

## 3. Display Name Header Top Bound vs Center
- **Hiện tượng:** Tại màn hình Profile root, selector anchor tìm dropdown switcher chọn nhầm nút copy `@username` (`t6f` / `t3y`) thay vì display name (`t_3` / `t7l`).
- **Root cause:** Điều kiện cũ kiểm tra `anchor.center[1] <= 320`. Các node display name có bounds `[36, 280][444, 364]` có tâm `y = 322 > 320`, dẫn đến bị loại oan và fallback xuống username bên dưới.
- **Giải pháp chuẩn:** Kiểm tra theo mép trên của node:
  `anchor.bounds is not None and anchor.bounds[1] <= 320`
  kết hợp ưu tiên `identity.get("display_name_element")` trước `identity.get("display_name_anchor_element")`.

## 4. Popup "Follow bạn bè của bạn" (`follow_friends_suggestion_popup`)
- **Hiện tượng:** Popup gợi ý tìm bạn bè / đồng bộ danh bạ xuất hiện che toàn bộ trang Profile, classifier trả về `unknown 0.0`.
- **Giải pháp chuẩn:** Nối hàm detector có sẵn `detect_follow_friends_suggestion_popup` vào nhánh phân loại `classify_tiktok_screen` của `python_runner/core/classifier.py` để định danh thành `GENERIC_POPUP_SCREEN` (`manual-needed:popup`), cho phép bộ dismisser tự động bấm nút đóng `X`.
