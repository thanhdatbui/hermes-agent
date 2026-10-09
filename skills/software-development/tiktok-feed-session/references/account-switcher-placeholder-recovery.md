# Fallback & Recovery: Account Switcher Placeholder (`user...`) - Case 124

## Context & Problem
Khi tài khoản mới đăng ký, vừa đổi thông tin hoặc cache UI chưa cập nhật trên TikTok, danh sách switcher hiển thị tên mặc định dạng placeholder `user\d+` (ví dụ: `user1196792370966`), trong khi workbook/config yêu cầu tên đích `expected` (ví dụ: `stevemgjqec`).
Khi đó, hàm `_find_account_switch_option(popup_xml, expected)` sẽ trả về `None` dẫn đến lỗi `manual-needed:account-switcher-missing-expected` làm treo máy trên farm.

## Kiến trúc và Pitfalls kỹ thuật (Đúc kết từ Case 124)

1. **Parser độc lập qua Standard Library XML (`xml.etree.ElementTree`):**
   - Tránh phụ thuộc vào private helper `_nodes` từ `automation_core.tiktok.account_switcher` vì cấu trúc đối tượng có thể thay đổi hoặc thiếu tương thích thuộc tính.
   - Duyệt `root.iter()` trực tiếp từ `ET.fromstring(xml_text)`:
     ```python
     def _find_user_placeholder_switch_options(xml_text: str) -> list[UIElement]:
         """Find all account switch options matching placeholder pattern user\d+."""
         if not xml_text:
             return []
         import re
         import xml.etree.ElementTree as ET
         try:
             root = ET.fromstring(xml_text)
         except Exception:
             return []
         results: list[UIElement] = []
         for n in root.iter():
             text = (n.attrib.get("text") or n.attrib.get("content-desc") or "").strip()
             # Khớp chính xác regex chữ thường ^user\d+$ (không dùng IGNORECASE để tránh bắt nhầm User... thông thường)
             if re.match(r"^user\d+$", text):
                 bounds_str = n.attrib.get("bounds", "")
                 m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                 if m:
                     x1, y1, x2, y2 = map(int, m.groups())
                     if (x2 - x1) > 0 and (y2 - y1) > 0:
                         results.append(
                             UIElement(
                                 text=n.attrib.get("text", text),
                                 content_desc=n.attrib.get("content-desc", ""),
                                 resource_id=n.attrib.get("resource-id", ""),
                                 bounds=(x1, y1, x2, y2),
                                 attrib=dict(n.attrib),
                             )
                         )
         return results
     ```

2. **Multi-Candidate Disambiguation (Vòng xoay đa ứng viên):**
   - Nếu trong switcher có từ 2 tài khoản `user...` trở lên, không được chọn mù quáng ứng viên đầu tiên lặp đi lặp lại.
   - Sử dụng cơ chế xoay vòng round-robin theo số lần thử (`attempt`):
     ```python
     cand_idx = (attempt - 1) % len(placeholder_candidates)
     placeholder_opt = placeholder_candidates[cand_idx]
     ```

3. **Nguyên tắc Fail-Closed Profile Verification sau khi Switch:**
   - Khi chọn một placeholder option, **bắt buộc** đánh dấu không phải exact match:
     ```python
     selected_account_by_exact_switcher = not is_placeholder_candidate
     ```
   - TikTok Profile đôi khi không render kịp `@handle`. Nếu `is_placeholder_candidate = True`, **tuyệt đối không chấp nhận** trường hợp `not recaptured_username` để verify bừa (loại bỏ `selected_account_recaptured_without_handle`).
   - Bắt buộc profile sau switch phải thực sự khớp `expected` qua `username_matches` hoặc `display_name_matches`:
     ```python
     if is_placeholder_candidate:
         verified = bool(
             latest_identity.get("xml_available") is True
             and recaptured_xml
             and not _is_profile_account_switcher_xml(recaptured_xml)
             and (username_matches or display_name_matches)
         )
         selected_account_recaptured_without_handle = False
         if not verified:
             last_reason = (
                 f"placeholder account '{placeholder_label}' did not match expected account "
                 f"'{expected}' on profile (found username: '{recaptured_username}', "
                 f"display: '{recaptured_display_name}')"
             )
     ```

4. **Hạ Modal Switcher Tránh Kẹt Giao Diện (Dismiss Switcher on Missing Account):**
   - Khi không tìm thấy tài khoản (cả exact match và placeholder fallback) hoặc trước khi bàn giao cho auto-login reconcile:
     ```python
     if _is_account_switcher_missing_expected_reason(last_reason):
         ctx.logger.log(
             device_id=ctx.device_id,
             account=ctx.account,
             step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight",
             action="dismiss_switcher_on_missing_account",
             result="dismissed",
             extra={"reason": "dismissing account switcher modal before recovery login or exit"},
         )
         try:
             ctx.adb.shell(["input", "keyevent", "4"], timeout=ctx.timeout("adb_seconds", 5))
         except Exception as exc:
             logger.warning("Gặp lỗi khi gửi keyevent 4: %s", exc)
         time.sleep(1.0)
     ```
   - Bọc try/except kèm timeout 5s để tránh nghẽn ADB transport và đảm bảo giao diện luôn được trả về trạng thái sạch cho các session sau.
