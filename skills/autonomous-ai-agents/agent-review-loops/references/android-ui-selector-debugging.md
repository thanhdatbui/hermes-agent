# Android UI Selector Debugging Guide

## When like/follow/tap actions silently fail

**Symptom**: Action (like, follow, tap) produces no log entry — not even "skipped" — but rate > 0
and flags are enabled.

**Root cause pattern**: `find_by_fields(root, resource_id="", content_desc="X")` uses EXACT
matching on all non-None fields. If `resource_id=""` is passed, it only matches elements where
`resource-id` is literally empty in the XML. TikTok buttons often have real resource-ids like
`com.ss.android.ugc.trill:id/fan`.

### Diagnosis workflow

1. **Find the last successful UI XML dump** in the run artifact:
   ```bash
   find .ai-runs/<run-id> -name "ui.xml" -path "*swipe_*_after*" | tail -1
   ```

2. **Extract all content-desc values** to see what's actually on screen:
   ```bash
   grep -o 'content-desc="[^"]*"' <ui.xml> | sort -u
   ```

3. **Find the target element's FULL attributes**:
   ```bash
   grep -o '<node[^>]*content-desc="Thích"[^>]*/>' <ui.xml>
   ```
   Look at `resource-id`, `clickable`, `bounds`, `class`.

4. **Check if `find_by_fields` would match**:
   - `text=X` → exact text match (`is not None + !=`)
   - `content_desc=X` → exact content-desc match
   - `resource_id=X` → exact resource-id match
   - Pass `None` to skip filtering on that field

### Common fixes

| Problem | Fix |
|---------|-----|
| `resource_id=""` doesn't match `resource-id="com.xxx:id/yyy"` | Use `resource_id=None` |
| `content_desc="Follow"` doesn't match `"Follow username"` | Prefix match: `desc.startswith("Follow ")` |
| "Đã follow" tab text matches `already_following` check | Add `element.clickable` filter to distinguish buttons from tabs |
| `find_by_fields` returns None silently | Add explicit "not found" logging |

### TikTok-specific selectors (Vietnamese UI)

| Button | content-desc pattern | resource-id |
|--------|---------------------|-------------|
| Like (chưa thích) | `"Thích"` | `com.ss.android.ugc.trill:id/fan` |
| Liked (đã thích) | `"Đã thích video"` | varies |
| Follow (chưa follow) | `"Follow <tên>"` | varies |
| Following (đã follow) | `"Following"` or text `"Đang follow"` | varies |
| Top tab "Đã follow" | `"Đã follow"` | — (tab, not button!) |

### Pitfall: UI dump failures on Samsung SM-G930F

`uiautomator_idle_state_error` is common. When it occurs:
- `_capture_step` marks the row as `degraded` (acceptable for continuing)
- `_maybe_like_video` / `_maybe_follow_video` try their own `dump_current_ui()` which may also fail
- On dump failure, logs `result="skipped"` with `reason="ui_dump_unavailable"`
- The feed session continues to next swipe
