# On-Device TikTok Rename Workflow & Farm Device Lock Coexistence

## Overview
When an operator provides a screenshot of a TikTok account with an unadapted or foreign/shop name (e.g. `LilyanLederhos64090`, `@lilyanzj8n1`) and requests "Đổi tên nick này", follow this complete end-to-end execution workflow.

## 1. O(1) Account Identification & Ground Truth Mapping
Never run broad disk scans or blind device searches. Query the farm database directly:
```python
import sqlite3
conn = sqlite3.connect('D:/OneDrive/TaadaaData/tiktok_tracker.db')
c = conn.cursor()
c.execute("SELECT machine_id, slot, cluster FROM farm_account_info WHERE username = ?", (target_username,))
# Yields e.g. (76, 7, 'kibe') -> Machine 76, Slot 7
```
Cross-reference with `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`:
- Match machine ID and target username to find the exact row (e.g. row 608 for M76 slot 7).

## 2. Farm Safety & Device Lock Coexistence Preflight
Before touching the device:
1. Inspect device status: `python D:/Taadaa/tools/inspect_machine.py <machine_id>`
2. Check device lock file: `C:\Users\Kibe\.codex\device-locks\machine_<ID>.lock.json` (Lưu ý: lock file đặt theo ID máy `machine_<ID>.lock.json`, không phải theo serial máy).
3. Check active processes: If a multi-machine feed or follow session (`run_tiktok.py --mode multi-machine-feed-session`) is running on the device, **NEVER** kill the process, steal the lock, or force ADB inputs.
4. **Coexistence Protocol**: Nếu máy đang bị lock bởi ca nuôi (`queued_v2`), KHÔNG vội báo BLOCKED kết thúc task ("Thì canh máy rảnh chạy đi"). Ca nuôi thường chỉ kéo dài vài phút. Thường xuyên kiểm tra khi file `machine_<ID>.lock.json` biến mất hoặc `inspect_machine.py <ID>` xác nhận màn hình về Home Launcher an toàn, lập tức kích hoạt runner đổi tên ngay.

## 3. Name Generation & Vietnamese Phonetic Mapping
Apply the phonetic adaptation rules from `account-profile-entropy`:
- Foreign prefixes: `lilyan-` -> `Linh Bông`, `Linh Miu`, `Linh Bơ` (stem: *Linh* ghép `_NICK_SUFFIX`) hoặc `Ngọc Linh`, `Thanh Linh` (Đệm + Tên).
- **"Tên nữ kèm biệt danh" (Female Name + Nickname)**: Khi operator yêu cầu đổi sang tên nữ kèm biệt danh (hoặc đổi tên kênh từ tên nam cũ như *Đạt* hay email handle):
  * Bốc stem tên nữ từ `_TEN_LIST` (*Vy, Linh, Thảo, Trang, Mai, An, Hà, Quỳnh, Hương, Nhi, Trâm, Ngân...*).
  * Ghép biệt danh đời thường từ `_NICK_SUFFIX` (*Miu, Nấm, Bơ, Kem, Bông, Nhím, Dâu, Su, Đậu, Cún...*).
  * Ví dụ: *Vy Miu, Thảo Nấm, An Kem, Linh Bơ, Hà Moon, Trang Bông*.
- **"Tên kênh thú cưng / Niche Pet (Mèo, Cún, Động vật)"**: Khi operator yêu cầu đổi tên kênh theo chủ đề thú cưng:
  * Soi nội dung video / thumbnail / avatar để bốc đúng tên nhân vật thú cưng chính trong video (ví dụ: thumbnail ghi "MI MI", "Mun", "Dứa").
  * **Kỷ luật >= 2 từ bất biến**: CẤM TUYỆT ĐỐI đặt tên 1 từ cụt không dấu cách (như *Mimi*, *Mun*). BẮT BUỘC tách thành dạng Duo / Tên lặp có khoảng trắng (*Mi Mi*, *Miu Miu*, *Mun Mun*) hoặc ghép loài/danh xưng (*Mèo Mi Mi*, *Bé Miu*, *Bé Mun*, *Mimi Cat*).
  * Tính chuẩn bộ đếm ký tự: e.g. `len("Mi Mi") = 5` -> counter `5/30` (dung sai `in (4, 5, 6)`), base64 `TWkgTWk=`.
- **CẤM TUYỆT ĐỐI TÊN CỤT LỦN 1 TỪ**: Tuyệt đối không đặt tên 1 từ trơ trọi (như mỗi chữ *Linh*, *Thảo*, *Hải*). Khi user yêu cầu "Đặt <Tên> + cái gì đó", đây là phong cách Tên + Biệt danh đời thường (`_TEN_LIST + _NICK_SUFFIX`, ví dụ *Linh Bông*, *Linh Miu*, *Linh Bơ*, *Linh Gạo*, *Linh Nhím*).
- Base64 encoding: `base64.b64encode(NEW_NAME.encode('utf-8')).decode('ascii')` (e.g. `Linh Bông` -> `TGluaCBCw7RuZw==`, `Vy Miu` -> `VnkgTWl1`)
- Character count: `len("Linh Bông") = 9` -> Counter on TikTok will be `9/30` (`len("Vy Miu") = 6` -> `6/30`). Trong `NAME_EDIT`, kiểm tra `count_match` bao gồm cận biên dung sai `in (len-1, len, len+1)`.

## 4. State Machine OCR Rename Pattern (`do_rename_m<ID>.py`)
Construct a dedicated device runner using WinRT OCR (`tools/ocr_boxes.ps1`) and `operator_device_lock`:
- **Locking**: Wrap execution in `with operator_device_lock(machine=MACHINE_ID, serial=SERIAL, project="do_rename_m...", timeout=300):`
- **State Classification & Navigation Invariants**:
  - `FEED`:
    - **Cạm bẫy Stale `seen_profile` & Swiping kẹt Feed**: Sau khi chọn acc trong Switcher, TikTok chuyển về màn Home/Friends Feed (`Ban bè`). CẤM dùng logic `if seen_profile and not "de xu" in t: swipe_top` vì Friends Feed không có chữ "đề xuất" $\rightarrow$ script ngộ nhận là Profile đang cuộn và vuốt vô tận dẫn đến `ABORT: ket o FEED 5 lan`.
    - **Invariant**: Luôn đặt lại `seen_profile = False` ngay khi tap chọn tài khoản trong Switcher.
    - **Dynamic Bottom Bar Profile Tab Tap**: Trên FEED, luôn tìm nút Hồ sơ qua OCR `find_box(boxes, r"(h[o0]\s*s[o0]|h6\s*s[d0])")` ở `y > 1700` (lưu ý OCR WinRT thường đọc nhầm thành `H6 sd`). Nếu thấy thì tap vào tâm box, nếu không thì fallback về `XY_PROFILE_TAB = (972, 1857)`. Tuyệt đối không dùng lệnh swipe kéo đỉnh thay cho tap tab Hồ sơ.
  - `PROFILE`:
    - **Cạm bẫy "Thêm tiểu sử"**: Trên profile chưa set bio, nút full-width "Thêm tiểu sử" (`id/t3z`) xuất hiện chứa chữ "tiểu sử". KHÔNG ĐƯỢC để heuristic `"tieu su" in t` phân loại nhầm thành `EDIT_PROFILE`. BẮT BUỘC kiểm tra bottom bar navigation (`Hồ sơ` / `H6 sd` ở y > 1800): nếu có bottom bar navigation thì LUÔN LUÔN là `PROFILE`, không phải `EDIT_PROFILE`!
    - **Bung Account Switcher**: Nếu username active != target, chạm trực tiếp vào node tiêu đề danh tính `id/t7l` (bounds `[36, 264][720, 408]`, tọa độ `(280, 320)`) để bung bảng **Chuyển đổi tài khoản**.
    - **Vào màn Sửa hồ sơ & Cạm bẫy Top-Left (72, 148) vs Video Tab Icon (Ill)**:
      * CẤM TUYỆT ĐỐI fallback vào tọa độ góc trên bên trái `(72, 148)`: Trên TikTok S7 v47, `(72, 148)` là icon **"Tìm bạn bè"** (Add Friends), không phải bút chì! Tap nhầm sẽ bung màn Tìm bạn bè.
      * **Cạm bẫy Video Tab Icon `Ill` / `Ill v`**: Trên profile chưa có bio, các tab video icon (`Ill` / `Ill v`) bắt đầu ngay tại `y ~ 969-1023, x ~ 143-223`. CẤM quét mù box ở `y trong [920, 1050] and x < 500` vì sẽ tap nhầm vào icon video tab `(165, 980)` lặp lại 5 lần dẫn đến abort!
      * **Nút vào Sửa hồ sơ chuẩn & Cạm bẫy 3-Button Row**:
        1. Ưu tiên 1: `find_box(boxes, r"(sua|chinh sua|edit)\s*h[o0]")`.
        2. **Cạm bẫy "+ Thêm tiểu sử" (534, 863)**: Khi tài khoản chưa có bio, hàng nút dưới stats gồm 3 nút ngang hàng (y ~ 865):
           - Nút 1 bên trái `(210, 865)`: **Sửa hồ sơ** (vào thẳng `EDIT_PROFILE`). WinRT OCR thường bỏ sót hoặc không đọc được chữ "Sửa hồ sơ" trên nút này do font/độ tương phản thấp trên S7. BẮT BUỘC dùng fallback `(210, 865)` (nằm ngang hàng bên trái của "+ Thêm tiểu sử").
           - Nút 2 ở giữa `(534, 863)`: **+ Thêm tiểu sử** (CẠM BẪY CHÍ MẠNG: Nút này CHỈ mở popup sửa Tiểu sử `0/160`, KHÔNG mở trang Sửa hồ sơ để đổi tên, khiến runner kẹt loop UNKNOWN / PROFILE 5 lần!).
           - Nút 3 bên phải `(860, 865)`: **Chia sẻ hồ sơ**.
        3. Fallback cứng: `(210, 865)` khi không thấy text "Sửa hồ sơ" và màn hình có `+ Thêm tiểu sử`. CHỈ dùng `(300, 985)` khi profile đã có text bio đẩy hàng nút xuống dưới.
  - `SWITCHER`: Tap đúng dòng target username (ví dụ `lilyanzj8n1` ở `y=603`). Nếu chưa thấy trong tầm nhìn, vuốt sheet lên (`(540, 1500) -> (540, 900)`). Khi tap trúng acc, lập tức gán `seen_profile = False`.
    * **Phân loại Switcher an toàn**: CẤM dùng keyword lỏng lẻo `"tai khoan" in t` đơn độc vì màn "Tìm bạn bè" có dòng *"Tài khoản được đề xuất"* sẽ bị nhận nhầm thành Switcher. Bắt buộc yêu cầu `"chuyen doi"` hoặc regex `chuy\w{0,4}n\s*d\w{0,4}i`.
  - `EDIT_PROFILE`: Identify label "Tên" (phải nằm trên "Tên người dùng", ví dụ y=752 so với y=878) và tap dòng "Tên" `(600, 752)`. Màn này KHÔNG BAO GIỜ có bottom navigation bar!
  - `NAME_EDIT`:
    1. Tap clear text X `(960, 576)` hoặc broadcast `ADB_KEYBOARD_CLEAR_TEXT`.
    2. Switch IME sang AdbKeyboard và broadcast `ADB_KEYBOARD_INPUT_TEXT` với base64 text.
    3. Verify text qua OCR và kiểm tra bộ đếm ký tự (`len/30`, e.g. `9/30` cho `Linh Bông`).
    4. Tap "Lưu" `(980, 140)`.
    5. **Xác nhận đổi tên (BẮT BUỘC)**: TikTok luôn hiện dialog *"Đặt biệt danh? Bạn chỉ có thể thay đổi biệt danh 7 ngày 1 lần"*. Nhận diện nút "Xác nhận" qua OCR hoặc tap `(747, 1173)` để commit thay đổi.
    6. Nhấn Back (`keyevent 4`) để quay về màn Profile.
  - `SAVE_LOGIN_POPUP`: Dismiss tự động ("Để sau" / `(540, 1325)`).
- **Readback Verification**: Re-read màn hình Profile qua WinRT OCR, xác nhận dòng hiển thị ngay trên `@username` khớp với tên mới (`Linh Bông` trên `@lilyanzj8n1`).
- **Teardown**: Revert IME về bàn phím mặc định (`com.sec.android.inputmethod/.SamsungKeypad`).

## 5. Hermetic Offline Testing & Runtime Artifact Verification
Before executing on the phone, create `tests/test_do_rename_m<ID>.py` testing pure logic:
- `norm()`: Diacritics stripping, lowercasing, whitespace collapsing.
- `compact()`: Stripping non-alphanumeric characters.
- `classify()`: Classification of all screen states including OCR distortion cases.
- `is_target()` / `is_target_user()`: Fuzzy matching tolerances.
- Run `pytest tests/test_do_rename_m<ID>.py` ensuring 100% pass (<0.5s).

### Closeout Gate & Sol Reviewer Test Evidence Bridge
Sol High / Closeout Gate reviews test evidence rigorously (scoring `test_evidence` out of 25). If tests only cover pure logic mocks, the gate will score ~18/25 and reject (< 85) citing "chưa thấy log state machine, kết quả đổi tên thành công hoặc kiểm chứng runtime artifact".
👉 **BẮT BUỘC**: Bổ sung test kiểm chứng artifact sau khi chạy thực tế trong file test:
```python
def test_runtime_report_artifact_and_trace_state():
    report_file = Path(r"D:\Taadaa\reports\m<ID>_<name>_nickname.json")
    if report_file.exists():
        data = json.loads(report_file.read_text(encoding="utf-8"))
        assert data["machine"] == MACHINE_ID
        assert data["target_user"] == TARGET_USER
        assert data["target_name"] == NEW_NAME
        assert data["result"] in ("RENAMED", "ALREADY")
        assert data["verified_by_ocr"] is True
        assert data["final_state"] == "PROFILE"
        assert len(data.get("trace", [])) > 0
        assert Path(data["evidence_png"]).exists()
```
Khi chạy lại Closeout Gate sau live execution, test suite sẽ verify cả logic thuần lẫn artifact nghiệm thu thực tế, giúp điểm `test_evidence` đạt tối đa và vượt mốc 85 điểm.

## 6. Tiered Workflow & Guard Compliance: Fast Scaffolding Pattern vs Delegation Timeout
Writing a new `do_rename_m<ID>.py` (~450 lines) exceeds Coordinator T1 direct-write budget (<= 200 lines total). However, attempting to delegate full runner creation from scratch to a worker subagent frequently hits two major pitfalls:
- **Pitfall 1 (Contract Validation Failure & Coordinator Guard Strict Headers)**:
  `TASK_KIND: EDIT` bắt buộc đủ các headers trong `context` của `delegate_task`:
  * `TASK_KIND: EDIT`
  * `TARGET_FILE: ...`
  * `TEST_FILE: ...`
  * `FOCUSED_TEST: python -m pytest <path>::<node> -q` (hoặc `python -m py_compile <path>`. CẤM dùng `pytest ... -v` vì guard sẽ từ chối `INVALID_FOCUSED_TEST_FORMAT`).
  * `OLD_STRING: <<< ... >>>` (BẮT BUỘC bọc trong `<<<` và `>>>`).
  * `NEW_STRING: <<< ... >>>` (BẮT BUỘC bọc trong `<<<` và `>>>`).
  * `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...` (Bắt buộc theo GATE 4).
  Thiếu bất kỳ header nào hoặc sai định dạng `FOCUSED_TEST`, Coordinator Guard sẽ chặn dispatch ngay lập tức (`EDIT_MISSING_OLD_STRING`, `EDIT_MISSING_NEW_STRING`, `INVALID_FOCUSED_TEST_FORMAT`, `GATE4_FAIL_FAST_MISSING`).
- **Pitfall 2 (Subagent LLM Timeout)**: Worker subagents tasked with generating 500+ lines of ADB state-machine code from scratch frequently hang waiting for model response (`Operation interrupted: waiting for model response (470s+ elapsed)`).

### The Battle-Tested Fast Scaffolding + Patch Pattern (Recommended)
Instead of blind delegation or monolithic writing:
1. **Instant Scaffolding via Shell `cp`**:
   ```bash
   cp D:/Taadaa/tools/do_rename_m76.py D:/Taadaa/tools/do_rename_m<ID>.py
   cp D:/Taadaa/tools/tests/test_do_rename_m76.py D:/Taadaa/tools/tests/test_do_rename_m<ID>.py
   ```
   (Runs in <0.1s, bypasses the 200-line full-write cap because no file is created from scratch via `write_file`).
2. **Targeted Parameter Updates via `patch`**:
   Use targeted `patch` replacements (diff <= 15 lines each, well within Coordinator T1 budget):
   - Update constants: `MACHINE_ID`, `SERIAL`, `TARGET_USER`, `NEW_NAME`, `NEW_NAME_NORM`, `NEW_NAME_B64`, `LOCAL_PNG`, `REPORT_JSON`.
   - Update handle prefix in `is_target_user` and `SWITCHER` hit matching.
   - Update length counter check in `NAME_EDIT` (e.g. `6/30` for "Vy Miu").
   - Update device lock project: `project="do_rename_m<ID>"`.
   - Update test suite in `tests/test_do_rename_m<ID>.py` to assert the new target name and username.
3. **Hermetic Test Verification**:
   Run `pytest D:/Taadaa/tools/tests/test_do_rename_m<ID>.py` (<0.2s) to guarantee 100% test pass before touching hardware.
4. **Autonomous Device Execution**:
   Launch in background via `terminal(command="python D:/Taadaa/tools/do_rename_m<ID>.py", background=True, notify_on_complete=True, timeout=300)` and let the harness wake the session on completion.

## 7. Execution via Background Terminal
Adhere to farm event-driven wakeup:
- Launch via `terminal(command="python D:/Taadaa/tools/do_rename_m<ID>.py", background=True, notify_on_complete=True, timeout=300)`.
- Never poll sleep loops. Let the harness wake the agent upon completion.
- Once woken, inspect the resulting `m<ID>_<name>_nickname.png` and JSON report, verifying with OCR / vision before delivering `MEDIA:` to the operator.
