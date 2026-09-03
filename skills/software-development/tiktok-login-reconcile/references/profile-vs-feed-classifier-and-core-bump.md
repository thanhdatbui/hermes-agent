# Profile-vs-feed classifier + core version bump — evidence & reproduction (2026-08-06/07)

## Bug gốc máy 34: feed bị nhận nhầm là profile

`social_reg_v1.py` (Tiktok_Reg). `_is_personal_profile_screen_xml` / `_has_profile_header_marker`
match SUBSTRING "follower" trong flat text. Feed LIVE có nút share-to-followers
`text="Đăng lại cho follower"` → chứa substring → `has_header: True` SAI.

Debug transcript (ad-hoc trên máy 34, serial `ce031603b3158b0b02`):
```
has_header: True   ← SAI (do "Đăng lại cho follower")
RESULT: True       ← feed bị nhận là profile
```

Fix commit `86c122d` (Tiktok_Reg): regex match NODE RIÊNG, không substring:
```python
follower_pattern = re.compile(r"^(?:[\d.,\s]*)?(?:nguoi dang follow|dang follow|followers?)$")
for node in root.iter("node"):
    t = (node.attrib.get("text") or "").strip()
    if t and follower_pattern.match(strip_accents(t).lower()):
        return True
```

Các nhánh khác cùng class bug phải kèm `_has_profile_header_marker` (user name clickable,
header y≤300, không số/stopword):
- "đã follow/thích" (feed bottom tabs có cùng text)
- "chia sẻ video/tải lên"

## Verification pattern (ad-hoc, không cần máy thật)

1. Dump XML thật:
```
adb -s <serial> shell "uiautomator dump /sdcard/wd.xml" && adb -s <serial> shell cat /sdcard/wd.xml
```
2. Inject node synthetic trước `</hierarchy>` để test 2 chiều:
```python
prof = xml.replace("</hierarchy>",
    '<node text="yobi" clickable="true" bounds="[435,117][645,183]"/>'
    '<node text="Follower" bounds="[435,200][600,250]"/></hierarchy>')
feed_share = xml.replace("</hierarchy>",
    '<node text="Đăng lại cho follower" bounds="[100,1500][400,1600]"/></hierarchy>')
```
Kết quả chuẩn (7/7 pass): feed→False, has_header→False; profile synthetic→True;
feed có "Đăng lại cho follower"→False; node "Người đang follow"→True.

Lưu ý Windows: python (MSYS bash) không thấy `/tmp` — dùng `C:\Users\Kibe\AppData\Local\Temp`
cho file XML, hoặc `tempfile.gettempdir()`.

## Core version bump (venv + runner gate)

Ví dụ 0.4.42 → 0.4.43 (`a57ab2b` pkill -9 SIGKILL cho atx-agent wedged futex_wait):

```bash
# 1. build wheel trong automation-core (version bump pyproject.toml)
# 2. cài đè sạch vào venv consumer
"D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" -m pip install --force-reinstall --no-deps "D:/Taadaa/automation-core/dist/automation_core-0.4.43-py3-none-any.whl"
# 3. verify 2 lớp
python -c "import importlib.metadata as md; print(md.version('automation-core'))"   # 0.4.43
python -c "import automation_core.ui as u, inspect; print('pkill -9:', 'pkill\", \"-9\"' in inspect.getsource(u))"
# 4. nâng REQUIRED_CORE_VERSION trong runner consumer
# 5. verify gate
python -c "from scripts.run_tiktok_recovery_new_handler import _require_runtime_core_version; print(_require_runtime_core_version())"
# → {'version': '0.4.43', 'source': 'installed-distribution', 'lease_verifier': True}
```

### Dual dist-info trap
Sau khi cài 0.4.43 lên venv vốn có 0.4.42, `importlib.metadata.version('automation-core')`
vẫn trả 0.4.42 (2 dist-info nằm cạnh nhau, metadata cũ ưu tiên). `--force-reinstall`
dọn dist-info cũ → mới đúng. Luôn verify bằng BOTH version AND nội dung module.

### pytest treo — test gọi ADB thật với serial giả
`tests/test_profile_detection.py::test_account_dropdown_dismisses_overlay_before_canonical_navigation`
treo vô hạn: `_try_open_account_dropdown_once` gọi `ensure_rotation_locked`/`shell`/`get_ui_xml`
thật với serial-6 không tồn tại. Dấu hiệu: `[adb warn] adb.exe: device 'serial-6' not found`
lặp lại, mỗi call ~30-40s. Pre-existing, KHÔNG phải do fix classifier — chạy các test khác
trong file riêng lẻ `-k` cho nhanh, đừng đuổi theo test treo.

## Run máy 34 sau bump — lưu ý khi đọc log runner

- Log fail `SWITCHER_ANCHOR_AMBIGUOUS` + dump UI lúc fail thường là FEED LIVE
  ("Đang LIVE", "Nhấn để xem LIVE", `rid=...:id/tv_live_nickname`) chứ không phải profile —
  đọc dump trước khi kết luận core sai.
- Runner chạy với `env -i` + PATH/PYTHONPATH tường minh (pattern chuẩn Tiktok_Reg):
```bash
env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
  PYTHONPATH="D:\\Taadaa\\python-envs\\tiktok-reg-recovery\\Lib\\site-packages;D:\\Taadaa\\Tiktok_Reg;D:\\Taadaa\\Hotmail" \
  "/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" scripts/run_tiktok_recovery_new_handler.py --stt 34
```
- atx-agent wedged (futex_wait, S-state) bỏ qua SIGTERM → cần core có `pkill -9` (0.4.43).
