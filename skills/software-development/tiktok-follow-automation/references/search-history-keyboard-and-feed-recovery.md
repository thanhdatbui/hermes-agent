# Search History, Soft Keyboard Back, and Feed Recovery Ladder

## Incident Pattern: Search History Keyboard Trap (Máy 10)

### Symptoms
- Runner stops with `MANUAL_REVIEW: không chứng minh được Feed trước Search UID` on Máy 10.
- Attached screenshot shows TikTok on the Search History screen ("Bạn có thể thích", "Tìm kiếm gần đây", suggested keywords) with the Samsung English (US) soft keyboard actively deployed.

### Root Cause
1. **Samsung Soft Keyboard Consumes Back Input:** On Samsung Android, when a soft keyboard is active, the first `adapter.press_back()` (Android keyevent 4) dismisses only the keyboard. It does not exit the Search activity or history screen.
2. **Missing Back Resource IDs:** TikTok 46.x frequently rotates the Back button resource-id on Search/Search History screens (`id/bq8`, `id/bq7`, `id/bq9`, `id/bqc`, `id/bqe`, `id/back_btn`, `id/iv_back`). If `_back_to_feed` relies on an incomplete whitelist, it falls back to `press_back()`.
3. **Bounded Input Exhaustion:** With 4 max Back attempts, 1 back dismisses the keyboard, leaving only 3 backs which may be consumed by Search suggestions or intermediate fragments, exhausting the budget before Feed is proven.
4. **Missing Recovery Ladder in Mode 1:** `run_mode1` and `ensure_feed_for_follow` previously raised `MANUAL_REVIEW` immediately on the first `_back_to_feed` failure without invoking `engine.recover_ui()`.

## Standard Solution (Case Fix)

### 1. Broaden Search History Screen Detection (`_is_search_history_screen`)
Recognize Search History screen by:
- Input IDs: `id/tv_search_textview`, `id/search_input`, `id/et_search_kw`, `id/search_edit_text`, `id/et_search`, `id/hhu`, `id/c0c`, `id/ho3`, `id/tvl_his`, `id/tvl_view_more`.
- Top-level EditText: Any `android.widget.EditText` belonging to a verified TikTok package with `top_y < 300`.
- Text/Desc: "Tìm kiếm", "Search".
- History headers: "Bạn có thể thích", "Tìm kiếm gần đây", "Recent searches", "Search history", "Xem thêm", "Lịch sử tìm kiếm", "Xóa tất cả".
- Negative constraint: No bottom navigation (`Trang chủ`, `Home`, `Hồ sơ`, `Profile`).

### 2. Geometry & Semantic Back Detection in `_back_to_feed`
Do not rely solely on specific resource IDs. Accept any clickable node in the top-left region:
- Coordinates: `bounds[0] < 250 and bounds[1] < 250`.
- Class: `android.widget.ImageView`, `android.widget.ImageButton`, `android.widget.Button`, `android.view.View`.
- Semantic content-desc: `{"Quay lại", "Trở lại", "Back", "Close", "Đóng"}`.
- Resource IDs: `id/bow`, `id/bqp`, `id/bq8`, `id/bq7`, `id/bq9`, `id/bqc`, `id/bqe`, `id/bqq`, `id/bq3`, `id/bq4`, `id/bq5`, `id/bq6`, `id/back_btn`, `id/back`, `id/btn_back`, `id/iv_back`, `id/action_bar_back`, `id/img_back`, `id/left_icon`, `id/action_bar_left_action`.
- Sorting precedence: Sort back button candidates with `clickable=True` first before non-clickable containers (`key=lambda n: (0 if n.get("clickable") else 1, x**2 + y**2)`).
- Profile root Home tap: Allow up to 2 consecutive Home taps on Profile root (`homes[0].get("selected") is not True`) before falling back.

### 3. Feed Recovery Ladder Integration (`run_mode2`, `ensure_feed_for_follow` & `run_mode1`)
If standard `_back_to_feed` fails (e.g. nested fragments or unresponsive keyboard):
In `run_mode2`:
```python
feed_ready = False
try:
    feed_ready = bool(_back_to_feed(engine))
except Exception as exc:
    logger.exception("run_mode2: _back_to_feed exception before seed search for anchor @%s: %s", uid, exc)
    feed_ready = False
if not feed_ready:
    recover_feed_ok = False
    try:
        recover_feed_ok = bool(engine.recover_ui() and _back_to_feed(engine))
    except Exception as exc:
        logger.exception("run_mode2: recover_ui + _back_to_feed exception before seed search for anchor @%s: %s", uid, exc)
        recover_feed_ok = False
    if not recover_feed_ok:
        res.status = "MANUAL_REVIEW"
        res.reason = "MANUAL_REVIEW: không quay về được feed trước seed search"
        res.failed = True
        failed = True
        break
```

### 4. Unit Test Speed Optimization
When running offline unit test suites containing multiple navigation flows (`mode1_search_follow`, `mode2_follow_followers`):
- Monkeypatch `time.sleep` to avoid accumulating hundreds of seconds of real sleep delays.
- Full suite (380+ tests) executes in ~20-25 seconds with patched sleep vs timing out.
