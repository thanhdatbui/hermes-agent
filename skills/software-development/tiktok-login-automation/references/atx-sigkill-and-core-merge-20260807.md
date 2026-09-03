# atx-agent SIGKILL + core legacy-API merge (2026-08-07, máy 34)

Session: Tiktok_Reg máy 34 reg `truongthuy111034@gmail.com` — đợt core
reconciliation "đẩy atx-kill lên core cho all repo" (user-mandated).

## 1. SIGTERM không kill được atx-agent wedged — phải SIGKILL

**Triệu chứng:** runner kẹt transport-recovery loop vô hạn. Log đứng ở dòng
cuối `? UI XML: ..._before_...xml`, dump mới nhất không có `_after_`/`_transport_`,
`ps -A | grep atx-agent` cho PID ĐỔI liên tục (watchdog restart) nhưng
uiautomator dump shell trả "Terminated"/E=137 mãi.

**Chẩn đoán:** `ps -A | grep atx-agent` → process state `futex_wait_queue_me`
(S-state, D-state không nhận SIGTERM). `pkill -f atx-agent` exit 0 nhưng
`ps | grep -c atx-agent` vẫn = 1 — SIGTERM bị bỏ qua.

**Fix:** `pkill -9 -f atx-agent` (toybox: `pkill [-SIGNAL|-l SIGNAL] [PATTERN]`).
Kết quả máy 34: SIGTERM E=137 kéo dài → SIGKILL → dump E=0 TỨC THÌ.
`pkill -9 -f uiautomator` trả "Operation not permitted" (app u0_a196, không
root) — vô hại; atx kill + `uiautomator quit` đủ.

**Core:** `_recover_uiautomator` đổi `["pkill","-f",...]` → `["pkill","-9","-f",...]`
(cả 2 marker). Test `tests/test_ui_dump.py` assert cũ `["pkill","-f","atx-agent"]`
→ phải cập nhật song song `["pkill","-9","-f",...]` (2 test:
`test_dump_kills_wedged_uiautomator_child_for_idle_state_error` + sibling).

## 2. Core legacy API — hết dilemma "không wheel nào có cả 2"

Trước: 0.4.38 có atx-kill nhưng mất 4 API cũ; 0.4.32 có API cũ nhưng không
atx-kill; fix tạm = patch venv (mất khi upgrade). **Đã resolve:**

- Merge verbatim từ wheel 0.4.32 (pip cache `...\wheels\8b\a3\35\...\
  automation_core-0.4.32-py3-none-any.whl`, unzip `/tmp/core032`) vào
  `src/automation_core/device_recovery.py`: `MissingVpnRecoveryError`,
  `AndroidTransportRecoveryError`, `MissingVpnRecoveryResult`,
  `AndroidTransportRecoveryResult`, `recover_missing_android_vpn`,
  `recover_android_transport`.
- Version: 0.4.41 (expected_marker) → 0.4.42 (legacy API) → 0.4.43 (SIGKILL).
- Commits nhánh `feat/hermes-cli-fallback`: `fc5d237`, `9561f3d`, `a57ab2b`.
- Build: `python -m pip wheel . --no-deps -w dist` (Hermes venv KHÔNG có
  `python -m build`). Install: `pip install --force-reinstall --no-deps`.
- **dist-info lẫn:** nhiều `automation_core-<v>.dist-info` cùng tồn tại →
  `importlib.metadata.version` trả bản CŨ NHẤT. Dọn: xóa hết chỉ giữ mới nhất.
- **Runner version gate:** `_require_runtime_core_version()` so
  `REQUIRED_CORE_VERSION` (constant trong runner) với metadata version →
  upgrade core phải bump constant song song, không thì
  `AUTOMATION_CORE_VERSION_MISMATCH:expected=0.4.31;actual=0.4.42` chết lúc import.

## 3. pyproject.toml conflict marker khi bump version

Stash/merge đè lúc đang bump → file chứa `<<<<<<< Updated upstream` /
`=======` / `>>>>>>> Stashed changes` → pytest chết `Invalid statement (at line 7)`.
Fix: viết lại file giữ version mới, `git commit --amend`, `git push --force-with-lease`.

## 4. Gmail OTP — refresh TRƯỚC fast-path (user rất tức)

Gmail không tự sync mail mới ngay khi TikTok gửi. Đọc Promotions preview ngay
→ chỉ thấy mail cũ (timestamp `'6 Th8'` = hôm trước) → nhập code cũ → reject.
Fix: `_gmail_pull_refresh(1)` (swipe `540,780→540,1500` dur 900 + sleep 7) NGAY
SAU khi vào Promotions, TRƯỚC `extract_recent_tiktok_otp_from_gmail_list`.
Verified `hermes-verify-refresh.py` 5/5.

## 5. TikTok 46.x account dropdown — anchor bị badge che

Profile header: tên `@handle` + badge đỏ `9+` che mũi tên dropdown → core
`find_switcher_anchor` không thấy marker → `SWITCHER_ANCHOR_AMBIGUOUS`. Tap
chính tên user (vd `yobi` bounds `[435,117][645,183]` → tap 540,150) mở dropdown
("Chuyển đổi tài khoản" + list account + "Thêm tài khoản"). Tap bừa quanh
header (540,250 / 575,230) đẩy về feed. **Điểm kẹt cuối session:** core
`open_account_switcher` chưa có fallback tap-identity — chờ user chọn hướng.

## 6. Verification evidence (turn cuối)

- Ad-hoc `hermes-verify-sigkill-fresh.py` 10/10 (source + venv pkill -9,
  test kỳ vọng đúng, expected_marker, compile).
- Canonical core `test_ui_dump` 13/13; `test_ui_capture_state_machine` 15/15;
  `test_ui_capture_circuit` 3/3; `test_ui_capture_replay` 26/26;
  `test_device_recovery` 18/18; consumer pytest 10/10.
- Live máy 34: `_recover_uiautomator` (SIGKILL) → dump E=0 — 3/3.

## 7. Profile-vs-feed classifier dương tính giả (CÒN MỞ cuối session)

Sau khi SIGKILL fix, runner vượt transport nhưng vẫn loop ở
`[3] Open account dropdown`: log `profile selected` nhưng dump quanh đó là
feed ("Tây Ninh"/"Bạn bè") → core chạy switcher trên feed → anchor None →
`SWITCHER_ANCHOR_AMBIGUOUS` loop relaunch vô hạn.

**Root cause:** `_is_personal_profile_screen_xml` (social_reg_v1.py) nhận
nhầm feed TikTok là profile. Các nhánh dương tính giả ĐÃ sửa:
- `all(marker in flat for ["follower", "da follow", "thich"])` — feed có
  bottom tabs "Đã follow"/"Thích" → phải kèm `_has_profile_header_marker(xml)`.
- `all(marker in flat for ["chia se video", "tai len"])` — feed có nút
  "Chia sẻ" → phải kèm header marker.
- `_has_profile_header_marker` (hàm mới): tên user profile phải là node có
  **`clickable="true"`** + **bounds y1 ≤ 300** (header region; creator/video
  names ở giữa màn y>1000 — vd "Thanh Thượng Tiên" clickable=false y1=1466
  không lọt) + không `isdigit` + không thuộc stopwords
  (`trangchu/cuahang/hopthu/hos/banbe/dafollow/dexuat/thich/...`);
  `@username` phải clickable.
- `_is_personal_profile_screen_xml` ưu tiên `_has_profile_header_marker`
  TRƯỚC `_is_home_feed_xml` (dump có thể còn sót feed-tab markers).
- `_try_open_account_dropdown_once` thêm verify profile thật trước khi gọi
  core: loop 2 lần `get_ui_xml` → `_is_personal_profile_screen_xml`; nếu False
  → `tap(COORD["profile_tab"])` + sleep 1.5.

**BUG CÒN MỞ:** node **"Đăng lại cho follower"** (nút share-to-followers của
video) → substring `"follower"` trong `flat` làm `_has_profile_header_marker`
trả True sai trên feed. Debug cuối:
```
has_header: True   ← SAI (do "Đăng lại cho follower")
is_home_feed: True
RESULT: True       ← feed bị nhận là profile
follower texts: ['Đăng lại cho follower']
```
**Fix cần làm:** nhánh follower phải khớp **node riêng** (regex per-node
`^(Follower|Người đang follow)$` hoặc count trong header), không match
substring toàn text. Verify: feed → False, profile thật (node yobi clickable
bounds y≤300) → True; ad-hoc script + pytest + `git diff --check` trước commit.

**Pitfall verify:** script ad-hoc chạy social_reg_v1 phải có PYTHONPATH đầy đủ
(`D:\Taadaa\Hotmail` thiếu → `ModuleNotFoundError: No module named 'flows'`;
env thiếu → PIL Hermes `_imaging` ImportError). Dùng `env -i` + đủ path.

