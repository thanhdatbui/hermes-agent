# ATX-primary UI dump/click encode vào Hotmail login runner (máy 31, 2026-08-17)

Task: encode ATX-primary UI dump/click vào `flows/login_outlook_one_machine.py` +
`flows/hotmail_login.py`, giữ fallback uiautomator, test xanh, commit.
Kết quả: toàn bộ ATX nằm trong `flows/hotmail_login.py` (runner không cần sửa).

## Code pattern (đã merge vào `hotmail_login.py`)

- `ui_xml(adb, device)` — ATX-primary đầu hàm:
  `atx_xml = _atx_dump_window_hierarchy(adb, device)` → trả ngay nếu có `<hierarchy`;
  rồi mới `capture_ui_xml` (persistent-first, guard xml rỗng) → exec-out uiautomator 5×.
- `_atx_uiautomator_pid`: `run_adb(adb, device, "shell", "ps", "-A")`, tìm dòng chứa
  `com.github.uiautomator`, field[1] = pid. KHÔNG dùng pid atx-agent (endpoint chê).
- `_atx_jsonrpc_call(adb, device, method, params)`:
  - pid qua `_atx_uiautomator_pid` (None → return None)
  - **`AdbClient(adb_path=adb, serial=device, default_timeout=20).shell(["forward", "tcp:7912", "tcp:7912"], timeout=20)`** — dùng `AdbClient.shell` TRỰC TIẾP, KHÔNG qua `run_adb`. Lý do: test cũ mock `run_adb` (máy không-atx) vẫn chạy đúng fallback shell mà không cần monkeypatch atx → None.
  - `requests.post(f"http://127.0.0.1:7912/session/{pid}:com.github.uiautomator/jsonrpc/0", json={...}, timeout=30)`
  - mọi exception → None; thiếu key "result" → None.
- `_atx_dump_window_hierarchy`: `dumpWindowHierarchy` params `[true]` (bắt buộc), cắt từ `<hierarchy`.
- `_atx_tap`: `click` [x, y] → `result is True`.
- `_atx_input_tap`: ATX click → fallback `run_adb(..., "input", "tap", x, y)` + sleep 1.2.
- `_atx_adb_text`: `run_adb(..., "input", "text", value.replace(" ", "%s"))` — ATX `setText` = UiObjectNotFound trên WebView.
- `_atx_app_password_field_point`: ATX dump → `choose_password_node(edit_nodes(xml))`; fallback node resource-id chứa "password" + password="true" → center bounds; fallback cuối (540,690) máy 31.

## Root cause máy 31: entry "Outlook" không có text

`ChooseAccountActivity` ("Chọn loại tài khoản"): entry Outlook chỉ có
resource-id `btn_add_account_outlook`, bounds [360,384][720,768] → center (540,576).
`tap_text(adb, device, xml, "Outlook")` KHÔNG land vì node không có text/content-desc
→ runner chết `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`.
Fix: `_tap_outlook_app_add_account_entry(adb, device, xml)`:
`_outlook_app_node_bounds(xml, "com.microsoft.office.outlook:id/btn_add_account_outlook")`
→ fallback `OUTLOOK_APP_ADD_ACCOUNT_ID` → fallback bounds (360,384,720,768) → `_atx_input_tap` center.
**3 call-site trong `login_outlook_app` đều phải đổi** (grep `tap_text(..., "Outlook")`):
1. onboarding → account-type selector (nhánh đầu)
2. persisted account-type selector (nhánh giữa)
3. nhánh cuối sau drawer-add-account (`if _outlook_app_account_type_selector_visible(xml)` ở cuối hàm)
→ Sót nhánh nào là còn nguyên bug.

## `_outlook_app_fill_password_and_finish` (dùng chung mọi nhánh password)

- Guard interstitial trước: AddAnother/QuickNote/PrivacyTour → `_outlook_app_finalize_new_account` → nếu đã tới folder surface → `_outlook_app_verify_and_write` (mở inbox nếu cần qua archive → drawer verify → artifact) → return True.
- `outlook_app_password_visible(xml)` False → return False (caller raise `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`, giữ status).
- `_outlook_app_password_node_with_retry` → có node: `type_text(sensitive=True)` (AdbKeyboard, cho máy uiautomator OK).
- Không node (S7 OOM): `_atx_app_password_field_point` → `_atx_input_tap` → `_atx_adb_text(password)` → `input keyevent 4` dismiss IME.
- Submit: `tap_text("Tiếp theo","Next","Đăng nhập","Sign in")` → fail thì `_atx_input_tap(540, 1011)` (máy 31 live; nút WebView không text).
- wait_for inbox/passkey/keep-signed-in/protection/add-another/quick-note/privacy-tour (90s) → passkey raise → protection `handle_account_protection_full` → finalize → keep-signed-in Có/Yes → inbox verified → `_tap_outlook_app_id(account_button)` → `ui_xml` → `outlook_app_identity_matches` → artifact `outlook_app_login_<ts>.json`.

Trả False vs raise: caller giữ nguyên `LoginBlocked("OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND")`
nên không đổi contract test cũ.

## Test

- `tests/test_atx_primary_ui.py` (module riêng, 21 test): pid parse từ ps output (u0_a184 + pid col 2); None khi thiếu process/adb fail; `test_atx_jsonrpc_call_posts_to_session_encoded_with_pid` assert `AdbClient(adb_path=..., serial=..., default_timeout=20)` + `shell(["forward","tcp:7912","tcp:7912"], timeout=20)` + URL `/session/11246:com.github.uiautomator/jsonrpc/0`; error paths (no result, no pid, forward fail, requests exception); dump non-xml → ""; tap True-only; `_atx_input_tap` fallback→`input tap`; password point (EditText bounds [96,660][984,720] → (540,690), empty→fallback); add-account-entry bounds (540,576) + fallback; `ui_xml` ordering (atx → capture; atx fail → exec-out `run_adb.args == ("exec-out","uiautomator",...)`); fill-password sensitive path (`type_text` kwargs sensitive=True); ATX fallback path (assert `("ATX_TAP",)`/`("ATX_TEXT",)` trong calls, keyevent 4, và KHÔNG có raw `("input","tap","540",...)` — Tap tiếp theo phải qua `_atx_input_tap`).
- Baseline 163 passed → sau encode 184 passed (+21 test). `-p no:cacheprovider`, venv `D:/Taadaa/python-envs/automation`.

## Pitfall kỹ thuật khi sửa file lớn (2746 dòng)

- **ATX block đặt trước `class LoginBlocked` → NameError lúc import** (`class ATXUnavailable(LoginBlocked)`). `LoginBlocked` định nghĩa ở giữa file (~line 339), không ở đầu. Di chuyển block sau class def.
- **Thay block `if` lớn (180 dòng) bằng 1 patch → fuzzy match chọn nhầm / indent lệch**: lần đầu "Found 3 matches" (nhánh gần giống), lần sau body thụt 20 spaces. Cách xử lý sạch:
  ```python
  # dedent line-range bằng script
  lines = p.read_text(encoding='utf-8').splitlines(keepends=True)
  for i, line in enumerate(lines, start=1):
      if 2230 <= i <= 2275 and line.startswith('    '):
          line = line[4:]
  ```
  rồi verify `ast.parse`. Đừng vật lộn patch nối tiếp.
- `_atx_jsonrpc_call` không dùng `run_adb` → khi test máy thật bị fail (`serial` không tồn tại) probe trả None nhanh, không treo — cần giữ timeout nhỏ (20/shell, 30/http).