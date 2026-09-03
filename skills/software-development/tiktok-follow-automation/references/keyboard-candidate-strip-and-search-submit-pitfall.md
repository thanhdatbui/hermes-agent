# Keyboard Candidate Strip & Search Submit Pitfall (Case UI-27)

## Root Cause Analysis
When typing an exact target UID into TikTok search on Android devices (especially with Samsung Keypad `com.sec.android.inputmethod` or Gboard `com.google.android.inputmethod.latin`), the on-screen keyboard displays a predictive text / candidate strip (`candidate_layout`) at the top of the virtual keyboard.

This candidate strip contains a `TextView` whose text equals the exact typed UID.

### Pitfall Breakdown:
1. **XML Parser Package Loss**: If `parse_nodes` does not extract and inherit the `package` attribute from the uiautomator XML, downstream selectors cannot distinguish between TikTok app nodes and keyboard/system nodes.
2. **False Search Result Detection**: In `_exact_search_result_from_xml`, checking only `text == target` without filtering out input method / system UI packages causes the keyboard candidate node to be classified as a valid non-input search result.
3. **Skipped Search Submit**: Because `_exact_search_result_from_xml` returned a node, `_nav_search` skips tapping the semantic "Tìm kiếm" (`_unique_search_submit`) button.
4. **False Navigation & Identity Mismatch**: `tap_center` taps the candidate bar on the keyboard instead of an actual profile or search result. `_nav_search` falsely returns `True`. When subsequent steps verify the profile identity (`profile_identity_from_xml`), the screen is still on the Search input with the keyboard open, leading to `hồ sơ identity mismatch: expected @<uid> got ""` and halting the session.

## Standard Fix Recipe
1. **Node Parsing Precedence**: `parse_nodes` must extract `package` for every node with strict inheritance precedence to prevent child element spoofing (e.g. child node under IME parent having a TikTok resource-id):
   ```python
   def _traverse(element: ET.Element, inherited_pkg: str) -> None:
       raw_pkg = (element.get("package") or "").strip()
       if raw_pkg:
           current_pkg = raw_pkg
       elif inherited_pkg:
           current_pkg = inherited_pkg
       else:
           res_id = (element.get("resource-id") or "").strip()
           current_pkg = res_id.split(":id/")[0].strip() if ":id/" in res_id else ""
   ```
2. **Unified TikTok Package Allowlist**:
   Allowlist all 5 official variants (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.zhiliaoapp.musically.go`, `com.ss.android.ugc.aweme`, `com.ss.android.ugc.aweme.lite`) and reject IME/SystemUI across:
   - Exact search result (`_exact_search_result_from_xml`)
   - Search submit (`_unique_search_submit`)
   - Profile header handle (`_find_header_handle_node`)
   - Independent `identity_element` in Path B verification
   - Profile action buttons (`_is_profile_action_node`)
3. **Submit Button Class Flexibility**:
   In `_unique_search_submit`, allow both `android.widget.Button` and `android.widget.TextView` for `id/tv_search_textview`.
4. **TOCTOU Back Safety in Path B Verification**:
   When verifying profile in Mode 2 Path B, do NOT blindly call `adapter.back()` based on historical navigation flags if the latest UI dump proves the screen is currently on the follower list (`currently_on_follower_list=True`). Calling Back on a follower list causes accidental exit to Feed. Only call Back when leaving a non-list screen.
5. **Fail-Closed State Persistence in Follow Failure**:
   If `state.set_follow_failed()` raises an exception (e.g. disk/IO error), preserve `MANUAL_REVIEW` / `failed=True` (dirty technical failure). The cleanup ladder (`_cleanup_follow_failed`) must close apps to Home but NEVER downgrade a dirty failure to clean `failed=False` / `FOLLOW_FAILED`.
