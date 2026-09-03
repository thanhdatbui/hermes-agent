# Account Switcher & Account Update Prompt Recovery in Feed Session

## Problem: `navigation target profile not found in XML`

### Root Causes
1. **Already Selected Account in Switcher Sheet:**
   - Khi mở drawer "Chuyển đổi tài khoản" (`account-switcher`) để switch sang nick mục tiêu, nếu nick đó đã active sẵn (`selected="true"` hoặc `checked="true"` mang icon checked `com.ss.android.ugc.trill:id/ffv`), việc tap lại row tài khoản không làm sheet tự đóng.
   - Sheet che toàn bộ nửa dưới màn hình (từ Y=420..1920 hoặc Y=852..1920), che khuất thanh bottom navigation bar chứa tab "Hồ sơ" (Y=1794..1920).
   - Khi `_navigate_profile_for_preflight` quét XML tìm tab Hồ sơ, không tìm thấy node -> crash fail-closed `navigation target profile not found in XML`.

2. **Popup Cập nhật tài khoản ("Để sau"):**
   - Modal reminder bảo mật yêu cầu liên kết email/SĐT khi switch account ("Tài khoản của bạn cần được cập nhật...").
   - Che màn hình và chặn flow điều hướng Profile nếu không được bấm bỏ qua.

### Solution Pattern (XML-First, CẤM tap tọa độ mù)
1. **Kiểm tra trạng thái `selected/checked`:**
   - Trong `verify_and_switch_profile`:
   ```python
   is_already_selected = any(
       account_element.attrib.get(attr, "false").casefold() == "true"
       for attr in ("selected", "checked")
   )
   if is_already_selected:
       ctx.logger.log(
           device_id=ctx.device_id,
           account=ctx.account,
           step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight_switch_{attempt}",
           action="dismiss_already_selected_switcher",
           result="success",
           extra={"reason": f"expected account {expected} is already selected in switcher; sending BACK to dismiss sheet"},
       )
       ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 15))
       time.sleep(1.0)
       ok, reason = True, "account already selected, switcher dismissed"
   ```
2. **Handle popup Account Update Prompt:**
   - Đăng ký `ACCOUNT_UPDATE_PROMPT_SCREEN = "manual-needed:account-update-prompt"` trong `benign_popup.py` / `classifier.py`.
   - Thêm handler `dismiss_account_update_prompt_popup` bấm nút *"Để sau"* vào `_maybe_handle_profile_add_phone_guard` và `_maybe_recover_navigation_from_add_phone`.
3. **Đọc lại XML**:
   - Sau khi đóng sheet/popup, luôn dump lại UI XML màn hình chính để xác thực node tab "Hồ sơ" trước khi tap điều hướng.
