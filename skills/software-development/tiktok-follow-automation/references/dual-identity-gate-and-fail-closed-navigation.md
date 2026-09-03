# Dual Identity Gate, Fail-Closed Navigation, and Contract Enforcement

## 1. Dual Structural Identity Gate vs Header/Bio Imposters

When validating target identity on a profile screen (e.g. before tapping the Following tab in Mode 2, or during Path B verification), searching for `@target_uid` among header nodes alone is vulnerable to false positives:
- A profile belonging to `@other_user` may contain a bio, link, or promotional text in the header area (`y < 650`) mentioning `@target_uid`.
- Pure text matching on `text` or `content_desc` without structural proof can cause the runner to follow followers of the wrong profile or falsely classify Path B as `followed`.

### Dual Gate Rule:
1. **Structural Verification**: Call `profile_identity_from_xml(profile_xml)` to extract `username_element` and `username`. Ensure `username_element` is not `None` and normalized `username` equals normalized `target_uid`.
2. **Visual Consistency & Scoping**: Validate with `_find_header_handle_node(profile_nodes, uid)`:
   - Scoped strictly to header bounds (`y < 650` with finite numerical validation).
   - Ensure the node's `text` or `content_desc` exactly matches `@target_uid`.
   - Reject conflicting text vs content-desc on the same node (`conflict_node`).
   - Reject multiple distinct header handles (`ambiguous_duplicate_header_handle`).
3. **Revalidation on Reload**: If `_ensure_anchor_followed` reloads the XML (e.g. following the anchor or pull-refresh), re-run the complete dual identity gate before tapping the relation tab.

---

## 2. Fail-Closed Navigation in `_back_to_feed`

In `_back_to_feed`, when an explicit semantic input is attempted:
- **Home Tab Tap**: If `tap_center(adapter, home_node)` raises an exception (e.g., ADB transport error, timeout, or node bounds issue), do NOT fall through or continue processing stale nodes. Return `False` immediately.
- **Search History Back Button Tap**: If `tap_center(adapter, back_btn)` raises an exception, do NOT fall through to `adapter.press_back()`. Return `False` immediately.
- **Why**: An ADB or UI driver exception during a tap does not prove the tap failed to reach the device. Blindly issuing `press_back()` afterwards risks executing double-navigation or exiting to the home launcher/backgrounding TikTok.

---

## 3. Zero Silent Failures in Recovery Ladders

In `run_mode2` and multi-step recovery ladders:
- Never use bare `except Exception:` that swallows errors without structured logging.
- Use `logger.exception("run_mode2: ... on anchor @%s: %s", uid, exc)` to preserve full tracebacks.
- Preserve sanitized exception types/messages in `res.reason` (e.g., `MANUAL_REVIEW: không khôi phục được UI sau lỗi mở tab anchor @{uid}: {exc_type}: {exc_msg}`).

---

## 4. Case 49 Cleanup Contract & Payload Normalization

- **Strict Clean State**: `cleanup_after_result` only executes `close_all_recent_apps` when `res_status in ("OK", "FOLLOW_FAILED")` AND `failed` is strictly clean (`failed is False` or `type(failed) is int and failed == 0`).
- **Contract Violation**: If `res_status == "OK"` but `follow_failed is True` (or set in details), convert to `status="CONTRACT_ERROR"`, `failed=True`, set reason `"CONTRACT_ERROR: status=OK nhưng follow_failed=True"`, and skip app closing.
- **Cleanup Failure Promotion**: If `close_all_recent_apps` raises or returns `False` on a clean `FOLLOW_FAILED`, promote status to `CLEANUP_FAILED`, mark `failed=True`, but strictly preserve `follow_failed=True` in payload and result objects for forensic evidence.
