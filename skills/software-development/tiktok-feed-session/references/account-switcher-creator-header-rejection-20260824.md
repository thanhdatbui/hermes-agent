# Account Switcher Creator Header Rejection & Fresh Anchor Recovery

## Context & Incident
Trong flow `verify_and_switch_profile` (hoặc profile preflight trong `feed_swipe_smoke`), sau khi điều hướng vào Profile hoặc sau khi gặp overlay/popup, script cần tìm semantic anchor của Account Switcher ở đỉnh trang (header) để mở danh sách chuyển đổi tài khoản.

Khi XML capture tại thời điểm đó bị trễ, dính transition state hoặc rơi vào trang profile của người khác (creator profile từ video/sự kiện trước đó), helper `find_switcher_anchor` (với fallback username header hoặc `allow_generic_header=True`) có thể trả về node `@creator_user` hoặc text display name lạ. Nếu consumer tap vào node này, app sẽ mở trang cá nhân của creator thay vì mở bottom sheet Account Switcher, dẫn đến failure `manual-needed:account-switcher-not-open`.

## Quy tắc kỹ thuật bắt buộc (Fail-closed Anchor Resolution)

1. **Từ chối Header `@handle` không khớp identity:**
   - Khi identity đã biết (từ capture profile ban đầu hoặc config `ctx.account`), nếu node anchor được resolve là một `@handle` (bắt đầu bằng `@`) nhưng giá trị khác với `identity["username"]`, consumer BẮT BUỘC trả về `None` (từ chối tap).
   - Tuyệt đối không cho phép node creator `@handle` trở thành mục tiêu tap của account switcher.

2. **Từ chối Generic Header Text không có Identity / Semantic Marker:**
   - Nếu không có identity context và node không có `resource-id` đặc hiệu (`s8k`, `rv5`, `pcq`, v.v.) hoặc content-desc chuẩn, không được tap vào text mơ hồ.

3. **Recapture Fresh XML sau phím `BACK`:**
   - Khi tap anchor lần 1 không mở được switcher (ví dụ bị vướng overlay/keyboard), sau khi gửi `BACK` để hạ overlay/keyboard, layout TikTok có thể thay đổi vị trí.
   - Script phải recapture `ui.xml` mới và resolve lại semantic anchor tươi (`_find_sticky_profile_header`) trước khi retry tap; không dùng lại tọa độ hoặc element cũ.

## Regression Test Pattern
- `test_find_sticky_profile_header_rejects_generic_text_without_identity`: Khẳng định header text chung chung không có identity bị từ chối (`assertIsNone`).
- `test_find_sticky_profile_header_rejects_generic_creator_when_identity_capture_misses`: Khẳng định `@creator_user` trên header khi capture lệch danh tính bị từ chối (`assertIsNone`).
- `test_account_switcher_retry_resolves_fresh_anchor_after_back`: Mô phỏng profile ban đầu và profile sau `BACK` ở tọa độ khác nhau, khẳng định sau `BACK` script tap vào tọa độ tươi thay vì tọa độ cũ.
