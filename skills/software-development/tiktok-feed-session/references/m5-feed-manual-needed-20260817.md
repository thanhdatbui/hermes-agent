# Máy 5 feed debugging — 2 root causes "tap nick OK nhưng vẫn manual-needed" (17/08 tối)

Wave-2 canary row 5: máy 5 feed chạy success nhưng trước đó liên tục manual-needed
sau khi tap đúng nick. KHÔNG phải "không chọn được profile" — log đã có
`tap_expected_account` success + XML switcher xác nhận nick trong danh sách.

## Root cause 1 — notification shade từ VPN reconnect (TikTok focus lost)

- Trình tự: `tap_expected_account thachkieu05 → SUCCESS` → 7-18s sau
  `verify_tiktok_focus`/`verify_*_navigation_blocker` thấy
  `focused_package: com.android.systemui` → "TikTok focus lost" → fail-closed.
- Nguyên nhân: đổi account → **Vi Changer VPN reconnect bắn notification
  "VPN Connected" → notification shade mở đè TikTok**. XML verify chứa
  `Thông báo của Vi Changer: VPN Connected` + systemui battery/clock nodes.
- So sánh máy 21/34 (success cùng chuỗi tap): VPN không reconnect vào đúng
  khoảnh khắc → race. Máy 5 dính, họ không dính.
- Chẩn đoán: XML/XSHOT verify có shade systemui (battery/clock/VPN notification
  trong tree) + `focused_package=com.android.systemui` trong observe extra.
- Hướng fix (đã thử): `_dismiss_notification_shade_if_open` chèn đầu
  `_navigate_profile_for_preflight` (feed_swipe_smoke.py) — swipe up/ký BACK khi
  focus là systemui, retry 2 lần; mock context phải try/except (get_focused_activity
  ném trên FakeAdapter). Chưa phải là lần chạy quyết định cuối.

## Root cause 2 — popup "Thêm số điện thoại" dạng BOTTOM SHEET không detect

- Triệu chứng: classifier ra `for-you` 0.89 NHƯNG ảnh có popup add-phone + XML
  đầy đủ marker ("Thêm số điện thoại", "+84", "Số điện thoại", "Tiếp tục",
  node đóng desc='Đóng'). → flow không dismiss popup → keyboard xiaowei bên dưới
  → keyboard cleanup fail → manual-needed.
- Root cause: core `automation_core/tiktok/benign_popup.py::_close_candidate`
  (dòng ~374) loại mọi close có `top > 350` (giả định close X góc trên màn).
  TikTok add-phone bottom sheet có close X ở góc phải CỦA SHEET:
  bounds `(936,804,1056,936)` → top=804 > 350 → bị loại → `detect_add_phone_popup`
  trả None → classifier không thấy add-phone.
- Verify trực tiếp bằng XML artifact máy fail trước khi sửa: nhúng XML → thử
  core detect → None; thử consumer detect → cần fallback.
- Fix consumer-local (KHÔNG sửa core — cấp độ: classifier là consumer-local):
  `python_runner/core/benign_popup.py::detect_add_phone_popup` thêm fallback
  `_bottom_sheet_close_candidate(elements)` — nhận close label
  Đóng/Close/Dismiss/×/X bất kể vị trí khi 4 content markers đủ → detect ra
  `add_phone` (markers + close_x) → classifier `manual-needed:add-phone` 0.98
  → `dismiss_add_phone_popup` được gọi đúng.
- Verify: detect trực tiếp XML thật → match; test_classifier +
  test_account_switcher 71 passed.
- ⚠️ Popup này có thể chỉ mở 1 lần (run kế tiếp không thấy) — luôn test với XML
  artifact đã lưu, đừng chỉ dựa run lại máy.