# Contact Follow Suggestion vs Login Marker Exemption Contract

## Context
When TikTok displays the recommendation / contact follow card ("Tài khoản được đề xuất" / "Đồng bộ danh bạ để tìm bạn bè"):
- The UI contains sensitive keywords like "tài khoản", which trigger generic sensitive/login screen checks in `has_sensitive_marker()`.
- This causes the flow to misclassify a benign suggestion popup as a sensitive login or account error screen (`manual-needed:login` / sensitive marker), halting feed or automation runs prematurely.

## Exemption Contract
In both the shared core and the consumer adapter:
1. `automation_core.tiktok.benign_popup.has_sensitive_marker(root)`:
   Exempt the screen if `detect_contact_follow_suggestion(root)` matches before checking general `marker_elements`:
   ```python
   if _has_any_packageinstaller_permission_marker(elements):
       return True
   if detect_contact_follow_suggestion(root) is not None:
       return False
   if not marker_elements:
       return False
   ```
2. `python_runner.core.benign_popup.has_sensitive_marker(root)`:
   Exempt the screen in the consumer override:
   ```python
   if detect_add_phone_popup(root) is not None:
       return False
   if detect_contact_follow_suggestion(root) is not None:
       return False
   return _impl.has_sensitive_marker(root) or _impl.detect_save_login_popup(root) is not None
   ```

## Verification
- Unit test: `pytest D:/Taadaa/automation-core/tests/test_tiktok_benign_popup.py -q`
- Screen classification check: verify that an XML hierarchy containing "Tài khoản được đề xuất" classifies as `manual-needed:popup` with reason `"known contact_follow_suggestion popup detected"`, rather than false-positive login.
