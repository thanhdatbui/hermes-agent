# TikTok Bio Edit Screen Misclassification & Topic Delivery Invariant (2026-10-21)

## 1. Bio Edit Screen Misclassification Trap (`@ Nhắc đến` vs `PROFILE`)

### Root Cause
When an automated runner opens the Bio Edit screen (e.g. by tapping `+ Thêm tiểu sử` on a profile without bio), TikTok renders:
- Header: `Tiểu sử` (often OCR'd as `Tieu sd`).
- Prompt: `Bạn có thể chỉnh sửa tiểu sử bất kỳ lúc nào.`
- Mention chip: `@ Nhắc đến` (below text field).
- System keyboard.

If `classify(lines)` tests for profile markers first:
```python
profile_has_user = any(l.startswith("@") for l in lines)
profile_markers = any(k in t for k in ("follower", "da follow", "daf", "thich", "dang follow"))
if (profile_has_user and profile_markers) ...:
    return "PROFILE"
```
Because `@ Nhắc đến` starts with `@` and the screen buffer or OCR trace may retain residual follower/like markers, `classify()` falsely returns `"PROFILE"` instead of `"BIO_EDIT"`.

### The Fatal Loop
1. Runner thinks it is on `PROFILE`.
2. It tries to tap the edit profile button (which does not exist on the bio editing keyboard screen).
3. The screen remains unchanged across multiple steps (`s03` through `s07`).
4. Runner hits `MAX_SAME_STATE` and triggers `Abort("ket o trang thai PROFILE 5 lan lien tiep")` (`exit_2`).

### Verified Fix
Prioritize `BIO_EDIT` before `PROFILE` in the classification cascade:
```python
def classify(lines):
    t = norm(" | ".join(lines))
    # Detect Bio Edit screen first: '@ Nhac den' or 'tieu su' with edit instruction/keyboard limits
    if any(k in t for k in ("nhac den", "@ nhac den")) or (
        any(k in t for k in ("tieu su", "tieu sd")) and any(k in t for k in ("chinh sta tieu", "chinh sua tieu", "160", "80"))
    ):
        return "BIO_EDIT"
    ...
```
When classified as `BIO_EDIT` without bio modification requested, the runner immediately dispatches `keyevent 4` (`BACK`) to retreat cleanly to Profile.

---

## 2. Cronjob Topic Thread Delivery Invariant

### Issue
When an operator executes `/new` to flush context in a long chat session, background recurring cronjobs (e.g. `tiktok-rolling-rename-watchdog`) with unpinned delivery (`deliver: origin` or omitted) can lose their specific thread context and deliver alerts to root or unintended topics.

### Invariant
For farm watchdogs operating inside specific platform topics/threads:
1. Always bind `deliver` explicitly to `platform:chat_id:thread_id`.
   - Example: `telegram:1076231895:296400`
2. Update the cronjob via tool or CLI:
   ```json
   {
     "action": "update",
     "job_id": "35e94bb43979",
     "deliver": "telegram:1076231895:296400"
   }
   ```
3. This guarantees that watchdog failure and success notifications reliably post to the active operating topic regardless of session clearing (`/new`) or gateway restarts.
