# Follower Surface Transient Recovery & Cleanup-Failed Interaction

## 1. Transient Follower Surface Classification in Mode 2

### Symptom & Root Cause
In Mode 2 (`mode2_follow_followers.py`), while scrolling or navigating within the anchor's Following/Follower list, TikTok frequently performs a brief UI re-render of the relation `RecyclerView` (e.g. `id/u5r`, `id/uoc`, `id/uo1`) or header text (`android:id/text1`, `id/sdn`).
An instantaneous XML dump taken during this frame often yields an unpopulated or malformed state where `_classify_follower_surface(nodes)` evaluates to `"invalid"`.

Previously, a single `"invalid"` surface triggered an immediate:
`MANUAL_REVIEW: rời khỏi màn follower list giữa chừng`
halting the session prematurely even though the follower list returned to a healthy, populated state in the very next second.

### Standard Fix Pattern (Bounded Recapture + Active Back Recovery)
1. **Passive Recapture:** Execute bounded recapture with short jitter for transient re-renders:
```python
surface = _classify_follower_surface(nodes)
for _ in range(2):
    if surface != "invalid":
        break
    time.sleep(1.0)
    try:
        nodes = _parse_mode2_nodes(engine.adapter.dump_ui())
    except FollowAdapterError:
        nodes = []
    surface = _classify_follower_surface(nodes)
```

2. **Active Back Recovery (`_recover_follower_list`):**
If `surface` remains `"invalid"` (e.g. navigation transiently entered a Profile screen from Path B or scroll tap), execute active recovery before failing closed:
```python
def _recover_follower_list(engine) -> bool:
    """Bounded recovery helper when follower surface becomes invalid."""
    adapter = engine.adapter
    for attempt in range(2):
        try:
            nodes = _parse_mode2_nodes(adapter.dump_ui())
        except Exception:
            nodes = []
        back_btn = _find_top_left_back_button(nodes)
        tapped = False
        if back_btn is not None:
            try:
                tap_center(adapter, back_btn)
                tapped = True
            except Exception:
                tapped = False
        if not tapped:
            try:
                if hasattr(adapter, "press_back"):
                    adapter.press_back()
                else:
                    adapter.back()
            except Exception:
                pass
        time.sleep(1.2)
        try:
            new_nodes = _parse_mode2_nodes(adapter.dump_ui())
        except Exception:
            new_nodes = []
        surface = _classify_follower_surface(new_nodes)
        if surface in ("populated", "empty"):
            return True
    return False
```

3. **Path B Restore Retry:**
In `_path_b_verify`, during the restore loop (`for attempt in range(3):`), if `attempt > 0` and not `_on_follower_list`, retry back navigation (tap top-left back button if present or call `adapter.back()`) before re-dumping UI. Ensure tests accounting for restore failure expect 3 back calls (1 initial + 2 retries).

### Invariants & Safety Gates
1. **Never bypass surface validation:** Empty surfaces must still break out cleanly to avoid infinite scrolling.
2. **Fail-Closed after budget exhaustion:** If the surface remains `"invalid"` after all recapture retries, emit `MANUAL_REVIEW` and preserve the scene.
3. **No unbounded sleep loops:** Cap retries strictly to 2 attempts with <= 1.0s interval.

---

## 2. FOLLOW_FAILED vs CLEANUP_FAILED Status & Exit Code Contract

### Clean FOLLOW_FAILED (Business Cooldown)
When TikTok drops a relationship after tap (detected via Path B or inline verify), this is a handled business outcome:
- Runner closes app via `close_all_recent_apps()`.
- State records `follow_failed = True` and persists daily cooldown.
- Result payload: `status = "FOLLOW_FAILED"`, `failed = False`, `follow_failed = True`.
- Process exit code: `0` (suppresses Telegram red banner / device lock retention).

### Dirty FOLLOW_FAILED / Cleanup Failure (Technical Failure)
If `close_all_recent_apps()` fails (raises exception, returns `False`, or is missing/non-callable):
- Runner status promotes to `CLEANUP_FAILED`.
- Flag preservation: `failed = True`, but `follow_failed = True` is preserved so callers know both the business release and cleanup crash occurred.
- Process exit code: `1` (fail-closed, triggers alert and preserves incident scene).
