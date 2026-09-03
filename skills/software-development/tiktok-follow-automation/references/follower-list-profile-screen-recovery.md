# Follower List Profile Screen Recovery & Path B Multi-Attempt Back

## 1. Symptom & Root Cause
In Mode 2 (`mode2_follow_followers.py`), while navigating or scrolling through an anchor's Following/Follower list, the UI can transiently navigate into a user's profile page (e.g. from Path B identity verification where a single `adapter.back()` was delayed/dropped, or an accidental touch-down during follower list swipe).

When the main `run_mode2` loop checks the follower surface:
1. `_classify_follower_surface(nodes)` evaluates to `"invalid"` because the screen is a Profile page rather than the relation `RecyclerView`.
2. The initial transient re-render guard sleeps passively for 2 seconds.
3. Because the UI remains on the Profile page without any Back navigation, `surface != "populated"` triggers immediately:
   `MANUAL_REVIEW: rời khỏi màn follower list giữa chừng`
   leaving the device stranded on the profile screen and halting the session.

## 2. Active Recovery Pattern (`_recover_follower_list`)
Before escalating to `MANUAL_REVIEW`, the runner must execute bounded active recovery (up to 2 attempts):

```python
def _recover_follower_list(engine) -> bool:
    """Attempt bounded Back navigation when follower surface is invalid (e.g. stranded on Profile)."""
    adapter = engine.adapter
    for attempt in range(2):
        try:
            nodes = _parse_mode2_nodes(adapter.dump_ui())
        except Exception:
            nodes = []
        
        # Check for top-left Back button (x < 250, y < 250) or invoke press_back()
        back_btns = [
            n for n in nodes
            if isinstance(n, dict)
            and is_tiktok_package(n.get("package"))
            and _node_left_x(n) is not None and _node_top_y(n) is not None
            and _node_left_x(n) < 250 and _node_top_y(n) < 250
            and (n.get("class") in ("android.widget.ImageView", "android.widget.Button", "android.widget.TextView")
                 or (n.get("resource_id") or "").endswith(("_back", "back_btn", "iv_back", "btn_back", "pm2"))
                 or (n.get("content_desc") or "").strip() in {"Quay lại", "Back"})
        ]
        if back_btns:
            try:
                tap_center(adapter, back_btns[0])
            except Exception:
                adapter.press_back()
        else:
            adapter.press_back()
            
        time.sleep(1.2)
        try:
            restored_nodes = _parse_mode2_nodes(adapter.dump_ui())
        except Exception:
            restored_nodes = []
            
        surface = _classify_follower_surface(restored_nodes)
        if surface in ("populated", "empty"):
            return True
            
    return False
```

## 3. Path B Multi-Attempt Back Retry
In `_path_b_verify`, when returning to the follower list from a sampled profile:
- Do not rely solely on a single initial `adapter.back()`.
- During the restore verification loop (`for attempt in range(3):`), if `attempt > 0` and `_on_follower_list` is still False, re-issue Back navigation (preferring the top-left back button or `adapter.back()`) before taking the next UI dump.
- Fail closed to `"manual"` only after all 3 restore attempts fail to observe `_on_follower_list`.

## 4. Invariants & Safety Gates
1. **Bounded retries:** Active recovery must be capped at 2 attempts in the main loop and 3 attempts in Path B.
2. **Package ownership:** Top-left back buttons must belong to official TikTok packages.
3. **Fail-closed preservation:** If active recovery fails to restore the follower list, preserve the scene and emit `MANUAL_REVIEW: rời khỏi màn follower list giữa chừng`.
