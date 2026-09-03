# Contextual Home-feed LIVE misclassification replay

## Incident pattern
A recurring `unknown TikTok state` / `manual-needed:popup` can be caused by a real TikTok Home feed whose newer header no longer uses the classic `Đề xuất/Bạn bè/Đã follow` row. The observed layout may contain `LIVE`, `Cộng đồng`, a location label such as `Hồ Chí Minh` or `Lân cận`, and `Đã follow`, while the bottom `Trang chủ` tab is selected.

The older detector path can classify the fullscreen `long_press_layout` + LIVE markers as `live_room_invite` before the generic feed classification. The alert's screenshot alone is not enough: read the exact machine log, exact attempt XML, and matching screenshot.

## Exact offline replay pattern
1. Read the target machine JSONL around the failure and the following popup-dismiss/re-observe events. A typical false-positive sequence is:
   - `classify_screen` -> `manual-needed:popup`
   - reason `known live_room_invite popup detected`
   - typed `press_back` succeeds
   - post-dismiss observe -> `for-you`
2. Open the exact `ui.xml` and matching `screen.png` from the failing attempt.
3. Confirm the XML has TikTok package/focus, a real feed container/viewpager, LIVE evidence (`LIVE`, `Nhấn để xem LIVE`, or `Đang LIVE`), and the contextual header plus selected Home tab.
4. Replay `classify_tiktok_screen()` offline before changing code. Record the pre-patch result as the regression baseline.
5. Add a minimal XML regression fixture that includes the production anchors: TikTok package, `:id/twc` header bounds `[0,72][1080,246]`, ViewPager resource, contextual labels, and selected `Trang chủ`.
6. Run the single regression test first and require it to fail before patching. Do not infer that an earlier artifact-backed test covers the new header shape.

## Safe classifier contract
Add a narrow predicate before `detect_allowed_generic_popup()`:
- required contextual labels: `LIVE`, `Cộng đồng`, `Đã follow`;
- required location/context label: `Hồ ...`, `Lân cận`, `nearby`, or equivalent tested marker;
- selected bottom `Trang chủ`/Home;
- TikTok ViewPager and exact contextual header container.

Return the selected feed state (`for-you`) with `manual_needed=False` only when all structural evidence is present. Do not accept a bare `LIVE`, a single city label, or a fullscreen LIVE node. Preserve typed `live_room_invite` and live product-drawer handlers for overlays that lack the feed/header evidence.

## Verification contract
- Exact artifact replay: `for-you`, `manual_needed=False`, safety `ok`.
- New contextual-header regression: `for-you`, `manual_needed=False`.
- Existing live-room popup tests remain green.
- Run focused classifier/popup/feed-session tests, `py_compile`, and `git diff --check`.
- Offline replay proves classifier behavior only; it does not prove a live machine is running the patched source. Report live runtime as unproven unless a separately authorized canary/target recapture is performed.

## Failure to avoid
Do not stop after seeing an existing LIVE artifact test pass. The old test may cover the classic `Đề xuất` layout while the current alert uses the contextual header. Also do not claim “fixed” from a direct classifier call if the exact failing log still shows `known live_room_invite`; inspect and patch the actual precedence path.
