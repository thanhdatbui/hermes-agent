# AI Auto-Recovery Architecture & Benign Popup Registry Patterns

## 1. Root Cause: Dead Code via Append-only Patching
- **Anti-pattern**: AI Auto-Recovery appending standalone functions (`def dismiss_xxx(...)`) to the bottom of `benign_popup.py` without registering them into dispatch loops (`dismiss_any_popup`, `dismiss_allowed_generic_popup`, `classifier.py`).
- **Symptom**: Every device hitting the same screen triggers a new AI recovery session and creates duplicate functions (e.g. 5+ camera dismissal handlers across machines).
- **Fix**: Centralize all benign popups into `BENIGN_POPUP_REGISTRY` in `benign_popup_registry.py` with `(name, priority, detector, dismisser, enabled, source)`.

## 2. Dual-Path Dispatch & Fallback Chain
- In `benign_popup.py` (`dismiss_allowed_generic_popup` and `dismiss_any_popup`):
  1. Always query `find_matching_handler(xml_content, ocr_text)` from `benign_popup_registry.py` FIRST.
  2. If matched and dismissed -> return `PopupDismissResult` immediately.
  3. If not matched -> fallback to legacy core popup dismiss logic.
- In `feed_swipe_smoke.py` (`_dismiss_allowed_or_blanket_popup`):
  - Expand fallback trigger to check all allowlist miss reason variants:
    `any(k in dismiss.reason for k in ("not in the benign allowlist", "not in the shared TikTok allowlist", "not an allowlisted generic popup"))`

## 3. Classifier Screen Mapping
- Màn hình Camera / Video Creation UI (`15s`, `60s`, `10 phút`, `ẢNH`, `VĂN BẢN`, `ĐĂNG`, `TẠO`) phải được phân loại trực tiếp thành `GENERIC_POPUP_SCREEN` trong `core/classifier.py` thay vì rơi vào `unknown` / `manual-needed:popup` không có handler.
- Khi được gán `GENERIC_POPUP_SCREEN`, feed loop tự động trigger `benign_popup_registry` gửi `KEYCODE_BACK` để thoát camera và tiếp tục lướt feed mà không dừng phiên.

## 4. AI Recovery Safety & Deduplication Guards
- **Deduplication**: In `code_patcher.py`, check `is_duplicate_handler(handler_name, code_patch)` against `BENIGN_POPUP_REGISTRY` before attempting code generation. If existing, skip code patch and only execute ADB unblock.
- **AST Allowlist & Safety**: Use `ast.parse` and resolve full dotted attribute names (`_resolve_call_name`). Block dangerous APIs (`subprocess`, `shutil`, `os.system`, `os.popen`, `eval`, `exec`, `__import__`).
- **Emergency Rollback**: Must revert the EXACT recorded commit SHA (`git revert --no-edit <sha>`), acquire `GIT_PATCH_LOCK`, and handle rebase aborts on conflict. NEVER use `git revert HEAD`.
