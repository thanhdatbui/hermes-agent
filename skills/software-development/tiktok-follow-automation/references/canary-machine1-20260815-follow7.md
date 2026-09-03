# Live canary evidence — máy 1 (2026-08-15) — follow-7 tiếp theo

## FOLLOW_FAILED transient — reset + chạy lại thành công (13:44–15:50)
- Run `20260815-134423` (sau khi reset `follow_failed=False`): fail ngay UID đầu
  (`stevemgjqec`) — `FOLLOW_RESULT {"status":"FOLLOW_FAILED","failed":true}`,
  budget không tăng. Lần 2 liên tiếp fail → acc `lipsellczaw` bị TikTok giới
  hạn follow TẠM THỜI (không phải ban vĩnh viễn).
- User chạy lại lần nữa (run `20260815-135844`): `FOLLOW_RESULT
  {"status":"MANUAL_REVIEW","followed":["hectornwrigh45","jorgebnstdk","thoanvrr5n8"],
  "reason":"exact profile identity không khớp sau reload"}` — follow được 3 UID
  mới rồi dừng vì identity mismatch (UI đang ở profile người khác sau follow).
- Run `20260815-153333`: `CONFIG_ERROR: VERIFY_IDENTITY fail — nick không khớp
  @lipsellczaw` — UI bị Android permission dialog chặn (xem dưới). Sau dismiss
  thủ công, máy về profile `@lipsellczaw` đúng.
- **Run `20260815-153820` (EXIT 0, OK):** follow được ĐỦ 7 UID —
  `["quocthuong99","hoangvy5328","phanmai0464","anhdo829","tongly2009",
  "nhuphuong458934","trieuha2048"]`. State cuối: followed_count=14,
  budget_used=13/30, follow_failed=False.

## UID dedupe case-insensitive (fix 2026-08-15)
- `WorkbookMapping.tik_ids()` dedupe theo `casefold()` — trước đây case-sensitive
  → `Samnga2403` vs `samnga2403` (CÙNG acc) xuất hiện 2 lần trong list.
- User hỏi \"sao follow trùng acc steve rồi lỗi\": không phải trùng — workbook có
  2 acc khác nhau chứa \"steve\" (`stevemgjqec`, `danielbsteve01`). Kiểm tra
  `m.tik_ids()` + đếm substring trước khi kết luận.

## Android permission dialog sau relaunch (15:36)
- Sau MANUAL_REVIEW + Splash, máy hiện dialog \"Cho phép TikTok có quyền truy
  cập...\" (nút \"OK\" / \"Không cho phép\") → `VERIFY_IDENTITY` fail (không thấy
  `@lipsellczaw`).
- `popup.dismiss_all` có `POPUP_DECLINE` (\"Không cho phép\") nhưng có thể chạy
  trước khi dialog xuất hiện. Handle thủ công: `adb shell input tap` tọa độ tâm
  nút. **Bounds format `(left, top, width, height)`** — center =
  `(left+w/2, top+h/2)`. Nút \"Không cho phép\" `(120,1333,419,143)` → tap
  `(329,1404)` thành công (lần đầu tap bằng bounds \"right/bottom\" sai vị trí).
  Sau đó verify `@lipsellczaw` xuất hiện (profile acc row 1).

## Fix _back_to_feed — profile người khác (commit 62d4cfb)
- Bug: sau follow xong UI dừng ở profile người khác; `_back_to_feed` chỉ tap Home
  khi `profiles[0].selected is True` (chỉ đúng own Profile) → profile người khác
  `selected=False` → không về Feed → UID kế tiếp search từ profile sai →
  identity mismatch → MANUAL_REVIEW.
- Fix: chấp nhận mọi profile root có bottom nav (`sf5` + homes + profiles,
  không follower recycler) rồi tap Home. Test mới:
  `test_back_to_feed_taps_home_from_third_party_profile_not_selected`.
- Probe live xác nhận: search `charakrh768` từ Feed → `SF5=['@charakrh768']`,
  nút \"Đã follow\" — UI-first đúng.

## UI-first principle (user correction)
- User: \"bản chất ID đã follow rồi thì vào profile nó sẽ hiện nút khác, cần gì
  phải ghi lại; handle tức là handle cách script hoạt động cho đúng\".
- UI là nguồn sự thật; state chỉ dedupe budget + fail-closed. Script đã có nhánh
  `cls == \"followed\"` → skip. Không gán yêu cầu cho user.
