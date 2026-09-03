# Live recovery: capture-first-report-first + terminal_capture_recovery break (2026-08-10)

## Sự cố

- User yêu cầu "fix 14 máy lock, bị kẹt ở màn nào thì gửi lại đây" → quy trình ĐÚNG là
  **chụp màn + báo trước, recovery chỉ sau khi user duyệt**.
- Đã dispatch background worker chạy recovery 10 máy (6,16,20,24,31,50,57,60,68,69)
  TRƯỚC khi user đính chính hướng → `LIVE_PARTIAL`:
  - success + lock released: 31, 57, 68, 69 (3/3 swipes)
  - vẫn `blocked` capture-invalid: 6, 16, 20, 24, 50, 60
- User nổi nóng: "thì nãy m báo nhóm máy đó auto recovery thất bại, thì thất bại chỗ nào
  báo lại đây" — muốn BÁO MÀN KẸT, KHÔNG muốn tự chạy recovery trước.

## Quy trình chuẩn khi user nói "báo màn kẹt / fix máy lock"

1. Chụp screen + UI dump song song (14 threads: `uiautomator dump` + `screencap -p` +
   `dumpsys window` lấy mCurrentFocus) → thư mục evidence.
2. Phân loại từng máy: feed / popup / launcher / splash / login / add-phone
   (dùng contact-sheet ghép ảnh + vision để xác nhận, không đoán từ tên lock).
3. Gửi contact-sheet + ảnh máy kẹt về chat, kèm bảng trạng thái.
4. CHỈ sau khi user duyệt mới chạy recovery bounded.

## Kết quả capture 08-10 (14 máy)

| Nhóm | Máy |
|---|---|
| Feed (không kẹt UI) | 6, 20, 24, 50, 52, 60, 68, 74 |
| Popup TikTok Shop "Mua ngay" | 16, 31 |
| Android Launcher (TikTok chưa foreground) | 57, 63, 69 |
| Add-phone "Thêm số điện thoại" | 65 (KHÔNG sensitive) |

## Root cause máy 16/6: `terminal_capture_recovery` break sớm → ladder KHÔNG chạy

Log máy 16 (bằng chứng):
```
uiautomator_null_root_node
capture_deadline_exceeded
screencap output too small: 12 bytes
UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2 → FINAL_BLOCKED
```
grep count: `recovery_force_stop` = 0, reboot = 0, coordinate swipe = 0.

**Chuỗi code:** `python_runner/flows/feed_swipe_smoke.py` L2601:
```python
if attempt.get("terminal_capture_recovery") is True:
    break   # bỏ qua toàn bộ ladder (uiautomator cleanup → force-stop → soft reboot → coordinate swipe)
```
Khi core trả `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`, attempt mang
`terminal_capture_recovery=True` → `break` ngay → **fix CTA swipe (08-09) tồn tại nhưng
KHÔNG BAO GIỜ tới lượt vì capture chết trước khi classifier chạy**.

User: "3 bước fix all lỗi chứ k chỉ UI" — ladder phải áp cho capture-invalid, không chỉ
popup/UI. Fix đề xuất: khi terminal do capture-invalid (không phải sensitive login/OTP),
vẫn đi tiếp ladder thay vì break.

## Add-phone KHÔNG phải sensitive — core xử lý được

- Core: `automation-core/src/automation_core/tiktok/benign_popup.py:722` `detect_add_phone_popup`
- Consumer: `python_runner/core/benign_popup.py:93` wrapper tiếng Việt
  (markers: `thêm số điện thoại`, `+84`, `tiếp tục`, `close_x`)
- Xử lý: chạy với `--allow-benign-popup-dismiss` → dismiss tự động.
- **KHÔNG** hướng dẫn worker bỏ qua add-phone như sensitive (chỉ login/OTP/2FA/captcha/
  security thật mới skip). Chỉ thị "bỏ qua sensitive" quá rộng = worker bỏ qua máy lẽ ra
  tự xử lý được (user: "chỉ thị bỏ qua ngu lồn à").

## Root cause CUỐI máy 65: core WHEEL cài (0.4.40) ≠ SOURCE — `unmatched_sensitive_popup`

**Chuỗi fail live (`current-blocker-dismiss-smoke`, artifact `.ai-runs/20260810-130243`):**
`not-at-target-blocker` → sau khi route ADD_PHONE_SCREEN thì `shared_popup_dismiss`
→ `unmatched_sensitive_popup` → "add-phone blocker not cleared".

**Chẩn đoán 3 bước (từng bước loại trừ):**
1. Consumer wrapper `core/benign_popup.py detect_add_phone_popup` trên XML thật M65 → **match OK**
   (BenignPopupMatch đủ 5 markers + close_element `Đóng` bounds (936,84,1056,216));
   consumer `has_sensitive_marker()` → **False** (exemption đã thêm).
2. Nhưng `automation_core.tiktok.benign_popup.detect_tiktok_popup_action(root)` trên CÙNG XML → **None**;
   `has_sensitive_marker`(core) → **True** → `dismiss_known_startup_popups` trả `unmatched_sensitive_popup`.
3. So sánh wheel CÀI vs source: `inspect.getsource(bp.detect_add_phone_popup)` trong
   `venv-core024/Lib/site-packages/automation_core` → core 0.4.40 CHỈ match
   `("add phone", "add your phone number")` (tiếng Anh); source `D:\Taadaa\automation-core\src`
   + wheel `dist/automation_core-0.4.44` ĐÃ có `_ADD_PHONE_TITLE_TERMS = ("Thêm số điện thoại", ...)`.
   Vòng lặp `detect_tiktok_popup_action` gọi core detector (không phải consumer wrapper) →
   core không match tiếng Việt → sensitive gate bật.

**Kết luận:** consumer match được ≠ core dismiss được. `dismiss_add_phone_popup` (flows)
ủy thác `_dismiss_shared_popup_via_core` → `dismiss_known_startup_popups` (core) →
`detect_tiktok_popup_action` (core wheel cũ) → fail. Fix consumer-only: nhánh match
tap TRỰC TIẾP `match.close_element` (tọa độ center `input tap`) + recapture verify,
KHÔNG qua core path cho add-phone; giữ screenshot fallback khi match None. KHÔNG nâng
core bừa vì `venv-core024` dùng chung với tiktok-video (đăng video).

**Kiểm tra version core ĐANG CÀI (không phải source):**
```bash
PYTHONPATH= "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -c "
from automation_core.tiktok import benign_popup as bp
print(bp.__file__)                     # site-packages = wheel thật đang chạy
print(hasattr(bp, '_ADD_PHONE_TITLE_TERMS'))  # False = wheel cũ chưa có tiếng Việt
"
```

## Bài học delegation (quan trọng)

- KHÔNG dispatch background worker có side effect (live recovery, `--full-scope-takeover`)
  khi user yêu cầu "báo màn kẹt" — worker chạy async, có thể thực hiện recovery TRƯỚC khi
  user đính chính hướng, gây chạm máy ngoài ý muốn.
- Capture + báo trước; recovery bounded chỉ sau khi user duyệt danh sách.
- Khi pass context cho worker, liệt kê ĐÚNG máy sensitive cần skip (login/OTP/2FA/captcha),
  không dùng cụm chung chung "sensitive".
