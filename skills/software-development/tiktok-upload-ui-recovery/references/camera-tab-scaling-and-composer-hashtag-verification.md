# Camera Tab Scaling, Composer Hashtag Verification & Failure State Tracking

## 1. Dynamic Camera Tab Ratio Fallback
When opening the camera viewfinder, TikTok sometimes opens on the LIVE tab or CapCut Template Hub instead of the standard camera mode.

### Pitfall of Hardcoded Coordinates
Older implementations used hardcoded coordinates:
```python
# BROKEN on non-1080x1920 displays (e.g. tablets, 720p phones, folded devices)
adapter.tap(315, 1820)
```
On devices with different screen resolutions or densities, hardcoded coordinates tap outside the tab bar or miss the camera tab target entirely.

### Dynamic Ratio Pattern
Scale the tap coordinates relative to the device's actual screen dimensions:
```python
width, height = 1080, 1920
if hasattr(adapter, "get_screen_size") and callable(adapter.get_screen_size):
    try:
        size = adapter.get_screen_size()
        if size and len(size) == 2 and size[0] > 0 and size[1] > 0:
            width, height = size[0], size[1]
    except Exception:
        pass
# Ratios: 0.292 horizontal (CAMERA tab), 0.948 vertical (bottom tab row)
adapter.tap(int(width * 0.292), int(height * 0.948))
```

---

## 2. Composer Hashtag Verification (50% Threshold Heuristic)
In `_caption_is_visible`, verifying caption input via uiautomator XML requires checking hashtags.

### Pitfalls of Strict vs Loose Matching
- **Strict `all(...)`**: Fails when long captions cause later hashtags to wrap off-screen, or when TikTok truncates pills in the composer XML.
- **Loose `any(...)`**: Falsely validates a caption when only 1 generic hashtag matches out of 10, masking typing or clipboard failures.

### The 50% Threshold Heuristic
Require at least 50% of the target hashtags to be matched, checking both the raw hashtag `#tag` and unhashed token `tag`:
```python
hashtags = [part for part in normalized_caption.split() if part.startswith("#")]
if hashtags:
    if all(tag in normalized_visible for tag in hashtags):
        return True
    matched_tags = sum(
        1 for tag in hashtags
        if tag in normalized_visible or tag.lstrip("#") in normalized_visible
    )
    if matched_tags >= max(1, (len(hashtags) + 1) // 2):
        logger.info(
            "[CAPTION] At least 50% hashtag tokens verified in composer (%d/%d)",
            matched_tags,
            len(hashtags),
        )
        return True
```

---

## 3. Failure State Tracking in State Machine
When an error occurs during execution and the state machine transitions to `WorkflowState.FAILED`:
- `self.current_state` becomes `WorkflowState.FAILED`.
- If caller inspects `current_state`, the root-cause state where the failure occurred is masked.

### Pattern
In `__init__`, initialize:
```python
self.last_failed_state: Optional[WorkflowState] = None
```
In the transition handler before switching to `WorkflowState.FAILED`:
```python
self.last_failed_state = self.current_state
if not self.context.error:
    self.context.error = f"Failed at state {self.current_state.value}"
self.current_state = fail_state
```
This preserves the exact failing state for telemetry, retry heuristics, and recovery logging.
