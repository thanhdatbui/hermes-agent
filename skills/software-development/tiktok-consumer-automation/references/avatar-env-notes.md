## Tạo avatar từ kho video (YOLO animal / frame sáng)

Video thú cưng/thiên nhiên không có mặt người → `make_representative_avatar(subject_type="person")` fail (face cascade rỗng) → fallback frame đầu tối. Giải pháp:

1. Cài `ultralytics` + opencv vào env automation:
   ```bash
   /d/Taadaa/python-envs/automation/Scripts/python.exe -m pip install opencv-python-headless ultralytics
   # numpy phải tương thích 3.12 (2.2.x), không dùng bản cp311
   ```
2. Tải model: `D:\CodexRuntime\tiktok-video\models\yolo11n.pt`.
3. Gọi `make_representative_avatar(subject_type="animal", subject_model=<path>, diagnostics=...)` từ `scripts/pipeline_common.py` — nó chọn **nhân vật xuất hiện nhiều nhất** (cluster theo binary hash). Nếu không detect được động vật đủ tin cậy → fallback chọn frame sáng có nội dung (std>50, mean 60-200, sat cao) crop vuông 512x512.
4. Script chuẩn đã có: `scripts/make_avatar_yolo.py` (map folder nguồn→output, guard `_assert_outside_source`, verify size/std, ghi report).
5. Output avatar chỉ ghi vào `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg`, workdir tạm `D:\CodexRuntime\tiktok-video\avatar-yolo-work\<folder>`.

**Pitfall env**: chạy bằng `env -i PATH=...` (bỏ PYTHONPATH/PYTHONHOME lẫn hermes venv) nếu `import cv2/numpy/PIL` báo sai version hoặc lỗi C-extension — sys.path bị hermes venv chèn trước automation site-packages.

**Pitfall `AVATAR_EDIT_OPEN_FAILED`**: máy có thể kẹt ở surface khác (vd `FindFriendsPageActivity` — Tìm bạn bè) làm workflow không mở được màn Sửa hồ sơ → avatar fail dù ảnh nguồn tốt. Retry avatar smoke lần sau (sau khi máy tự về đúng surface) thường qua được như máy 45; máy 74 vẫn kẹt → giữ MANUAL_REVIEW, không spam retry cùng signature. Chạy avatar smoke song song với các máy khác, không làm lẻ.

**Cách chạy avatar smoke ĐÚNG** (launcher PS1 KHÔNG có flag avatar-smoke → chạy trực tiếp python):
```bash
printf 'AVATAR-SMOKE\n' | env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/automation/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" PYTHONPATH="D:\\Taadaa\\Tiktok-video\\scripts" \
  "D:/Taadaa/python-envs/automation/Scripts/python.exe" -c \
  "import sys; sys.path.insert(0, r'D:\Taadaa\Tiktok-video\scripts'); from tiktok_workflow.run_post import main; sys.exit(main())" \
  --config "D:\\CodexRuntime\\tiktok-video\\config-machine-62.yaml" \
  --workflow-workbook "D:\\OneDrive\\Tiktok\\Tik1.xlsx" \
  --machine <N> --avatar-smoke --no-dry-run \
  --force-avatar-upload --force-avatar-machines <N> --avatar-source-root "D:\\video goc"
```
Pitfall:
- Token xác nhận là **`AVATAR-SMOKE`** (KHÔNG phải YES — YES sẽ abort). Đọc prompt trước khi pipe.
- Bắt buộc `env -i` sạch + `PYTHONPATH=scripts` (không env -i → `No module named automation_core.usb_popup` do hermes venv chèn).
- `-c "...; main()"` KHÔNG dùng `--` phân cách (argparse không nhận) — đặt args trực tiếp sau `-c`.
- Nếu máy bị feed session `tiktok-luot nuoi acc` giữ lock SỐNG → không giành; chỉ giành khi user cho phép (backup + evidence).

**Pitfall `AVATAR_UPLOAD_MENU_MISSING` (máy 34, 2026-08-05)**: force avatar mở Sửa hồ sơ, tap "Thay đổi ảnh" OK nhưng menu sau đó KHÔNG có text "Tải ảnh lên" → raise. Chẩn đoán: máy giữ ở ProfileEditActivity; uiautomator treo nên không dump được XML menu thật (ảnh ASCII quá tối để đọc text). Cần: bắt XML lúc fail (sửa handler log XML) hoặc nhờ user xác nhận text menu thật, rồi thêm selector variant + regression test + COMPAT entry theo rule bắt buộc.

**ĐÃ FIX (2026-08-05, commit `6c16368`, COMPAT-AVATAR-004)** — fallback chain trong `_handle_ensure_avatar_impl`:
```python
if not adapter._tap_if_found(change_xml, text="Tải ảnh lên"):
    if not adapter._tap_if_found(change_xml, text_contains="Tải ảnh"):
        if not adapter._tap_if_found(change_xml, text_contains="Thư viện"):
            if not adapter._tap_if_found(change_xml, resource_id="g9u"):
                raise WorkflowError(... "AVATAR_UPLOAD_MENU_MISSING")
```
exact → substring "Tải ảnh" → substring "Thư viện" → resource-id `g9u` → fail-closed. Regression test `test_avatar_upload_menu_falls_back_to_contains_variants`. Lưu ý test: mock trực tiếp chuỗi tap fallback (không gọi `_handle_ensure_avatar_impl` nguyên khối — nó đi nhiều nhánh `_reserve_avatar_recovery`/`_looks_like_profile_root`/usb_popup khiến test khó ổn định).

**Pitfall tiếp theo `AVATAR_PICKER_NO_MATCH` (máy 34, cùng ngày)**: sau khi menu fallback hoạt động, push avatar OK (`/sdcard/Download/avatar_<folder>.jpg`), mở picker thành công (ProfileAvatarChoosePhotoActivity) nhưng `AVATAR_PICKER_NO_MATCH` — `similarity=0.047 threshold=0.600` — tile picker không khớp ảnh nguồn.

**Root cause THẬT (đã tìm ra bằng thực nghiệm, KHÔNG phải false-negative khung tròn):**
`_avatar_picker_candidates` lọc tile với điều kiện `200 <= top <= 300` (CHỈ hàng đầu
của grid). Picker máy 34 (TikTok 46.3.3) hiển thị avatar mới ở **hàng giữa y~800**
→ candidates rỗng → recent_fallback dùng tile mặc định `(135,350)` → crop sai vùng
→ similarity 0.047. Kỹ thuật chẩn đoán: **quét correlation cửa sổ trượt** trên
screenshot picker so với ảnh nguồn (window 270x270, step 30) — tìm được vùng
`(120,800)` corr=0.412 và `(510,590)` corr=0.537 → avatar CÓ trong picker, chỉ là
workflow crop sai vị trí.

**ĐÃ FIX (2 lớp, 2026-08-05):**
1. **COMPAT-AVATAR-005** (commit `bfee8cf`): mở rộng `_avatar_picker_candidates` —
   `top 150-1800` thay vì `200-300`, vẫn yêu cầu kích thước tile 250-280px (loại
   nút/icon). Regression: `test_avatar_picker_accepts_tiles_below_first_row`.
2. **COMPAT-AVATAR-006** (commit `9b877de` + `855b617`): `_avatar_picker_visual_match`
   — screenshot correlation scan trước khi tin XML candidates (uiautomator treo → XML
   thiếu tile node). Quét cửa sổ trượt trên `_capture_avatar_screen(...)` so với
   nguồn, ngưỡng 0.35, trả candidate `{center, bounds, similarity}`; nếu beat XML
   candidates thì thay thế. Regression:
   `test_avatar_picker_visual_match_finds_true_tile_below_first_row`.

**Pitfall CUỐI cùng của chuỗi — crop-preview central-band (máy 34, commit `855b617`):**
sau khi visual scan tìm ĐÚNG tile (corr=0.666) và tap, vẫn `AVATAR_PICKER_NO_MATCH`
similarity=-0.003. Nguyên nhân: sau tap tile, TikTok chuyển sang **màn crop preview**
— avatar phóng to nằm ở **dải trung tâm ~23-77% chiều cao, full width** — còn
`_avatar_picker_tile_similarity` vẫn crop theo `candidate["bounds"]` (bounds của tile
trong grid cũ) → trúng vùng trống → similarity ~0. Xác minh bằng artifact
`avatar-picker-tile-01.png`: ASCII thấy avatar lớn giữa màn (y448-1472), correlation
toàn ảnh chỉ 0.277 nhưng crop dải 23-77% = **0.982**.

Fix: trong `_avatar_picker_tile_similarity`, nếu grid-bound similarity < 0.6 → fallback
so sánh **dải trung tâm** `full.crop((0, int(h*0.23), w, int(h*0.77)))`; dùng similarity
cao hơn. Đừng dùng toàn màn (0.277 — nền trắng làm loãng) mà phải dải trung tâm.
Kỹ thuật chẩn đoán: sau tap, nhìn artifact xem surface có đổi (grid → crop preview)
rồi chọn vùng so sánh theo surface MỚI, không theo bounds cũ.

**Kỹ thuật tái sử dụng — screenshot correlation scan khi uiautomator treo:**
khi XML không đáng tin (dump treo/thiếu node), quét screenshot bằng correlation
trượt để định vị object thật. Luôn verify bằng cách pull ảnh trên máy so với nguồn
(`adb pull` + `corr == 1.0` chứng minh file push đúng; correlation thấp = crop sai
vùng hoặc hiển thị ảnh khác, KHÔNG phải file sai). Phân biệt: corr 0.4-0.5 trên
vùng đúng = tile thật bị overlay/scale; corr ~0.05 trên mọi vùng = ảnh không nằm
trong picker (tab sai, file chưa index).

**Khi patch test cho hàm mới trong flow avatar picker:** các test cũ
(`test_avatar_picker_tries_next_tile_until_source_match`,
`test_avatar_recent_fallback_does_not_back_out_of_picker`) mock `Transport.screenshot`
với số ảnh cố định — hàm mới gọi thêm `_capture_avatar_screen` làm hết screens
(IndexError) hoặc đổi tap. Mock `_avatar_picker_visual_match → None` trong các test
đó để giữ hành vi cũ; thêm test riêng cho hàm mới. Cũng lưu ý `_avatar_picker_candidates`
là instance method (cần `machine.context` fake), test static sẽ TypeError.

**Pitfall `OPEN_TIKTOK_FAILED` transient khi avatar smoke**: máy kẹt SplashActivity (không vào feed) — force-stop + relaunch thủ công (`am force-stop` + `am start ...MainActivity`) thường đưa máy về MainActivity, chạy lại avatar smoke sẽ qua. Không phải lỗi handler avatar; retry sau relaunch.

**Pitfall `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` — máy kẹt màn TỐI lúc VIDEO_PICK (máy 74, 2026-08-05)**: workflow vào VIDEO_PICK, tap nút + nhưng `Visual create-button gate rejected screenshot: white=0.000, dark=0.976` → recapture không chứng minh được labelled bottom-centre create control → MANUAL_REVIEW. Root cause KHÔNG phải selector create-button — máy kẹt **SplashActivity màn tối** (dark 81-97%) nên visual gate không thấy nút create. Chẩn đoán:
```bash
adb -s <serial> shell dumpsys activity activities | grep mResumedActivity  # → SplashActivity
adb -s <serial> exec-out screencap -p | ...  # mean brightness <50 / dark% >80
```
Fix: force-stop + relaunch (`am force-stop com.ss.android.ugc.trill` + `am start ...MainActivity`), verify brightness cải thiện (dark% giảm, mean tăng) rồi chạy lại workflow. Cùng pattern `OPEN_TIKTOK_FAILED` transient — kiểm tra màn hình THỰC TẾ trước khi đổ lỗi handler mới.


## Env automation_core dở dang (import fail module mới)

Khi core build wheel mới (`dist/automation_core-X.Y.Z.whl`) nhưng env thực thi
(`D:\Taadaa\python-envs\automation`) import **không thấy module mới** (vd
`usb_popup`) — dù `pip show` báo version cao hơn:

- Nguyên nhân: dist-info bị cập nhật nhưng site-packages KHÔNG có file module
  tương ứng (cài dở dang/force-reinstall lỗi) → import fail im lặng.
- Chuẩn đoán: `ls site-packages/automation_core/ | grep usb` rỗng nhưng
  `dist-info` version mới hơn wheel hiện có.
- Fix: cài lại đúng wheel theo pin consumer:
  ```bash
  env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/automation/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
    HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
    /d/Taadaa/python-envs/automation/Scripts/python.exe -m pip install --force-reinstall \
    "D:\\Taadaa\\automation-core\\dist\\automation_core-0.4.21-py3-none-any.whl"
  ```
  (đúng version trong `requirements-automation-core.txt`). Verify:
  `python -c "from automation_core.usb_popup import ..."`.
- Lưu ý: `env -i` PHẢI kèm `HOME`/`USERPROFILE` nếu không pathlib `expanduser`
  raise "Could not determine home directory".

## Codex exec bị kill → để lại patch dở (working tree dirty)

`codex exec` chạy background qua Hermes bị kill giữa chừng (user interrupt /
process.kill) sẽ để lại **working tree lẫn lộn**: file đã patch một phần, test
mới viết dở, import mới thêm nhưng module chưa tồn tại. Trước khi chạy lại:

1. `git status --short` để thấy toàn bộ file dính.
2. `git diff --stat` đánh giá mức độ: thay đổi nhỏ/đúng hướng → giữ + hoàn thiện;
   thay đổi sai/chưa rõ → `git checkout -- <file>` revert.
3. Kiểm tra import mới có module đích chưa (vd `from automation_core.usb_popup
   import ...` mà core chưa build) — nếu chưa, workflow sẽ import-fail ngay
   đầu run.
4. Dispatch lại Codex với prompt yêu cầu "hoàn tất/verify trạng thái git trước,
   rồi implement tiếp" — không giả định run trước sạch.

## Verify avatar sau save — false negative (so sánh pixel thô)

Workflow verify avatar sau save bằng grayscale correlation trên vùng crop;
ngưỡng 0.8. Khi avatar hiển thị trong **khung tròn + overlay** (TikTok), ảnh bị
crop/scale khác nguồn vuông → correlation thấp (0.02-0.25) dù nội dung ĐÚNG →
`AVATAR_VERIFY_FAILED` false negative.

- Người nhìn (user) xác nhận avatar đúng là bằng chứng mạnh hơn correlation
  pixel — báo user kết quả + để user xác nhận trước khi kết luận fail.
- Nếu user xác nhận avatar đúng: không cần sửa handler (hoặc chỉ sửa verify
  poll recapture sau save 2s×15, lưu artifact ảnh sau save).
- Phân biệt: similarity thấp TRƯỚC Next trong picker (chọn sai tile — bug thật)
  vs thấp SAU save (có thể false negative do overlay).
- Vision model (vision_analyze) KHÔNG khả dụng trên môi trường này — đừng dựa
  vào nó để xác nhận ảnh; dùng ASCII preview (PIL convert L → chars) + user xác
  nhận.

## Launcher PS1 + PYTHONPATH nhiễm hermes venv (version mismatch 0.4.32 vs 0.4.34)

`run_tiktok_upload_batch.ps1` (HEAD) kiểm tra automation-core version khớp
`TIKTOK_VIDEO_AUTOMATION_CORE_VERSION` (mặc định **`0.4.35`**; runtime pin
`D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`).
Bash session của Hermes luôn có `PYTHONPATH` trỏ `hermes-agent\venv\Lib\site-packages`
→ python bên trong PS thấy automation-core **0.4.32** (bản hermes venv) dù env thật
0.4.35 → launcher throw `automation-core version mismatch: expected=0.4.35; actual=0.4.32`.

- `env -i` bọc lệnh bash KHÔNG truyền env vào `powershell.exe` (process con kế thừa
  env bash cũ) — không đủ để fix.
- Fix đúng: xoá `PYTHONPATH`/`PYTHONHOME` ngay trong shell gọi:
  ```bash
  cd /d/Taadaa/Tiktok-video && PYTHONPATH= PYTHONHOME= powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_tiktok_upload_batch.ps1" -Tik 1 -PythonPath "D:\Taadaa\python-envs\automation\Scripts\python.exe" ...
  ```
- Launcher tự set `$env:PYTHONPATH = scripts` (khoảng dòng 129) nhưng metadata check
  version chạy TRƯỚC đó với PYTHONPATH kế thừa nhiễm → mismatch.
- Verify nhanh trước khi chạy launcher: `python -c "import importlib.metadata as m; print(m.version('automation-core'))"`
  — nếu ra 0.4.32 khi chạy trực tiếp (không env -i) là đang nhiễm, phải dọn.

## TikTok Registration (Tiktok_Reg) — workbook writer identity + core pin

### Writer identity env (mọi workbook write đều cần)

Mọi mutation workbook (deferred tracking write, CAPTCHA-confirmed source-row
delete, mail-die Audit Pending) đi qua `single_writer_workbook_update` yêu cầu
cặp env khớp nhau:

```bash
TIKTOK_REG_WRITER_ID=tiktok-reg-runner TIKTOK_REG_EXPECTED_WRITER_ID=tiktok-reg-runner
```

Thiếu → `BLOCKED_EXPECTED_WRITER_ID_MISSING:tiktok_tracking` / `:gmail_clean_v2`.
Bẫy nguy hiểm: device cleanup chạy TRƯỚC và thành công (`ALREADY_ABSENT`) nhưng
row Excel KHÔNG xoá được vì writer env thiếu (đã xảy ra STT 40: `[captcha-delete]
x gmail_clean_v2: ... BLOCKED_EXPECTED_WRITER_ID_MISSING:gmail_clean_v2`).
Runner `run_tiktok_recovery_new_handler.py` phải `env.setdefault` cả 2 cho child
worker + `_apply_workbook` (không chỉ child). Writer ID đơn giản là chuỗi
máy-local giống nhau (conftest dùng `test-writer`); `declared != expected` →
`BLOCKED_WRONG_WRITER_ID` fail-closed.

### Core version pin — phải tồn tại trong git history

`REQUIRED_CORE_VERSION` trong runner phải là version CÓ THẬT. Lịch sử bump
nhảy cóc: ...→0.4.28→0.4.31→0.4.35 — **0.4.30 không bao giờ tồn tại** (runner
pin sẵn `0.4.30` → fail cứng `AUTOMATION_CORE_VERSION_MISMATCH` dù cài bản nào).
HEAD 0.4.35 đổi API: `recover_missing_android_vpn`/`recover_android_transport`
bị thay bằng `soft_reboot_and_wait`/`reboot_and_restore` → recovery runner cũ
vỡ import. Kiểm tra commit nào còn giữ API cũ:
`git show <commit>:src/automation_core/device_recovery.py | grep -c "def recover_missing_android_vpn"`.
Build wheel từ đúng commit đó: `git archive <commit> | tar -x -C <dir sạch>` rồi
build trong dir đó (đừng `git checkout <commit> -- pyproject.toml` — chỉ lấy
pyproject, src vẫn là HEAD → wheel version mới nhưng code cũ).

### NEVER `pip install -e .` core vào env chạy runner

Test core bằng `PYTHONPATH=<core>/src` — **KHÔNG** `pip install -e .`. Editable
install ghi đè wheel đã pin (0.4.31 → source 0.4.35), lần chạy runner kế tiếp
import-fail `cannot import name 'AndroidTransportRecoveryError'`. Đã dính
2026-08-05: chạy pytest core xong quên, runner 52/57/62 vỡ ngay đầu. Fix: cài
lại đúng wheel pin (`--force-reinstall --no-deps <wheel 0.4.31>`).

### Vietnamese header + accent normalization

- `gmail_clean_v2.xlsx` header là tiếng Việt: `số máy` / `tài khoản gmail` /
  `pass mail` — alias map PHẢI có `tai khoan gmail`/`tai khoan` (thiếu →
  `SOURCE_WORKBOOK_HEADERS_MISSING: email`).
- Alias `tik` đơn lẻ cho `tiktok_id` đụng cột slot `Tik` trong tracking →
  `TRACKING_WORKBOOK_HEADERS_AMBIGUOUS: tiktok_id` — bỏ `tik`, giữ `id`/`tiktok`...
- **Classifier tiếng Việt**: NFKD strip bỏ dấu nhưng KHÔNG bỏ `đ` — phải thêm
  `text.replace("đ","d")` (marker `da bi khoa` không khớp flat `đa bi khoa`).
  Nhãn nằm TRONG attribute XML (`<node text='Đăng nhập...'/>`) → flatten CẢ
  blob, đừng strip thẻ (`re.sub(r"<[^>]+>",...)` ăn luôn attribute → text rỗng).

### OTP conversation extract — regex bắt nhầm số trong email address (STT 34, 2026-08-06)

Log `Skip stale opened-message code [REDACTED] (timestamp='07:02')` nhưng OTP
THẬT là mã MỚI (07:02). Root cause: `extract_recent_tiktok_otp_from_gmail_conversation`
quét `(?<!\d)\d{6}(?!\d)` trên CHUỖI GỘP toàn bộ text node của conversation →
bắt nhầm 6 số liền trong địa chỉ email (`truongthuy111034@gmail.com` →
`111034`) thay vì code trong node có marker. Code sai → không khớp
`not_before`/marker → bị log "skip stale" dù OTP mới hợp lệ. Dấu hiệu nhận
biết: skip stale lặp nhiều lần cùng timestamp gần `not_before`, và số bị skip
trùng với chuỗi số trong email. Hướng fix: chỉ lấy code 6 số từ node chứa
`tiktok`/`mã TikTok`/`verification`; loại pattern email `…@…`; không fallback
regex toàn chuỗi khi có node marker. Chi tiết replay offline + code locations:
`references/tiktok-reg-otp-extraction-and-core-venv.md`.

### Core pin ≠ env chung — dùng venv riêng, đừng cài đè env automation

Runner `run_tiktok_recovery_new_handler.py` pin `REQUIRED_CORE_VERSION` (vd
0.4.31, wheel tại `D:\Taadaa\_core031_build\dist\`) nhưng env automation chung
có thể là 0.4.34+ và đang bị scheduler khác dùng (`tiktok-log-in --live`,
feed recovery). Cài đè wheel cũ vào env chung = phá consumer khác. Fix: tạo
venv riêng kế thừa site-packages rồi force-reinstall wheel đúng pin:
```bash
python -m venv --system-site-packages "D:\Taadaa\python-envs\tiktok-reg-recovery"
env -i PATH="...tiktok-reg-recovery/Scripts;...automation/Scripts;..." HOME=... USERPROFILE=... \
  python -m pip install --no-index --no-deps --force-reinstall <wheel-pin>.whl
```
**Pitfall `flows`**: `social_reg_v1.py` import `from flows.hotmail_login import
check_mailbox_alive` — module `flows` KHÔNG nằm trong automation-core wheel mà
là package `taadaa-hotmail` (repo `D:\Taadaa\Hotmail`) cài trong env automation.
Venv `--system-site-packages` có site-packages automation → `flows` có sẵn,
nhưng nếu dùng venv KHÔNG kế thừa hoặc `PYTHONPATH` thiếu `D:\Taadaa\Hotmail`
thì import fail `ModuleNotFoundError: No module named 'flows'` / `cannot import
name 'check_mailbox_alive'` (bản site-packages cũ thiếu hàm). Chạy runner với
`PYTHONPATH="D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail"`; verify import trước live:
```python
env -i ... PYTHONPATH="D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail" python -c \
  "from flows.hotmail_login import check_mailbox_alive, login, resolve_adb; print('ok')"
```
Đừng `pip install -e` core vào venv này (rule NEVER editable vẫn áp dụng).

### Hotmail OTP sau resend — CDP reload không lấy mail mới, phải swipe inbox (máy 57/66, 2026-08-06)

Sau khi TikTok reject OTP và bấm `Gửi lại mã`, `_try_get_otp_outlook_cdp` chỉ
`location.reload()` tab Outlook → inbox vẫn hiện email cũ → trả về **đúng code
đã bị reject** → log `refusing reuse` → dừng, không bao giờ lấy được code mới.

Fix (đã áp dụng): trong `_request_and_read_fresh_tiktok_email_otp`, khi code
trả về trùng `excluded_codes` (code cũ bị reject) và mail không phải Gmail →
gọi `_swipe_outlook_inbox_refresh(device_id)` — swipe Chrome xuống
(pull-to-refresh) rồi đọc lại CDP; nếu vẫn không có code mới thì thử
`_try_get_otp_browser` lần nữa. `_swipe_outlook_inbox_refresh` chỉ swipe khi
XML chứa `com.android.chrome` (tránh swipe mù khi Chrome không foreground).

Lưu ý thứ tự trong `_request_and_read_fresh_tiktok_email_otp`: `_try_get_otp_outlook_cdp`
chạy TRƯỚC `_try_get_otp_browser`; cả hai đều có thể trả code cũ → nhánh
refuse-reuse phải đặt sau cả hai reader, không chỉ sau CDP.

**Pitfall Gmail app đọc OTP → mất màn OTP TikTok (STT 34, 2026-08-06)**: với
Gmail, flow mở **Gmail app** (không phải CDP) để đọc OTP — account verify +
extract code đều OK (`Recent code found timestamp mới`), nhưng khi quay lại
TikTok qua `_return_to_tiktok_via_recents` (Recents → `--activity-reorder-to-front`),
TikTok rơi về `SignUpOrLoginActivity` (registration entry) thay vì màn OTP →
`[otp-enter] TikTok OTP screen unavailable after Recents recovery`. Root cause:
**TikTok KHÔNG preserve OTP screen khi bị đưa xuống nền lâu** (đọc Gmail app
mất 1-2 phút) — Android kill/restart activity. Đối với Hotmail/Outlook, CDP đọc
tab nền KHÔNG rời TikTok → không dính lỗi này. Hướng fix: với Gmail cũng đọc
qua CDP Chrome tab Gmail web (`mail.google.com`) thay vì mở Gmail app, giữ
TikTok foreground — hoặc chấp nhận retry khi máy về đúng surface. Đây là blocker
nghiệp vụ/app-behavior, KHÔNG phải lỗi extractor hay account verify (verify +
extract đã chạy đúng).

**Pitfall 2 OTP email dồn 1 conversation — CDP đọc mail CŨ thay vì mới (user chỉ
ra, 2026-08-06)**: Outlook gộp 2 mail OTP TikTok thành 1 conversation, DOM xếp
**mail cũ ở TRÊN, mail mới ở DƯỚI**. JS querySelectorAll quét theo thứ tự DOM →
`candidates[0]` = code của mail CŨ (đúng code đã bị reject) → dù swipe refresh
vẫn `refusing reuse` vì mail mới chưa tới hoặc vì lấy nhầm code cũ. Fix trong
`_try_get_otp_outlook_cdp`: **duyệt `reversed(candidates)`** (code mới nhất nằm
cuối DOM) thay vì `candidates[0]`. User: *"nó dồn 2 mail OTP về 1 mail thành ra
otp ở trên là mail cũ kéo xuống dưới ms ra mail đúng"*. Khi chẩn đoán
`refusing reuse` kéo dài: check xem reader lấy code nào — nếu lấy code trùng
code đã nhập (reject) nhiều lần liên tiếp, nghi conversation gộp mail, đừng chỉ
đổ lỗi "mail mới chưa tới".

### Gmail PHONE_VERIFY ≠ mail die — chạy core live probe trước khi xóa (máy 36, 2026-08-06)

Canonical policy (repo `add mail khoi phuc` / `automation_core/google_health.py`):
- `PHONE_VERIFY` → `HEALTH_MANUAL` (MANUAL_BLOCKED) → **GIỮ mail** — đây là gate
  thủ công của Google, không phải bằng chứng mail chết.
- Chỉ `CAPTCHA`/`IDENTITY_BLOCKER` → `HEALTH_CAPTCHA` → xóa device + source row.

Consumer Tiktok_Reg cũ thiếu bước này: `recover_missing_gmail_target_account`
gặp phone_verify chỉ `raise GmailMailboxRecoveryBlocked("GMAIL_RECOVERY_PHONE_VERIFY")`
rồi dừng, không phân loại live/die. Fix (đã áp dụng): thêm
`_gmail_account_live_probe()` gọi `automation_core.google_health.run_google_live_check`
với callback classify (phone markers → PHONE_VERIFY, captcha → CAPTCHA,
identifier → RELOGIN, `com.google.android.gm` → LIVE) rồi quyết định:
`HEALTH_CAPTCHA` → `_cleanup_google_captcha_account`; còn
`NORMAL/RELOGIN/MANUAL/UNKNOWN` → giữ mail + ghi `PHONE_VERIFY_KEEP_MAIL:<status>`
vào recovery_verdict. Markers phone_verify trong
`_google_mailbox_recovery_surface`: `xac minh so dien thoai cua ban` /
`verify your phone number` / `them so dien thoai` — đừng nhầm với CAPTCHA.

### "Mail mất trên máy" — verify AccountManager trước khi xóa + policy user (2026-08-06)

Khi flow báo `GMAIL_TARGET_ACCOUNT_NOT_LISTED` / `target_account_unverified`, ĐỪNG
vội xóa mail khỏi excel:

1. **Verify AccountManager thật**:
   `adb -s <serial> shell dumpsys account | grep 'Account {'`. Account CÓ trên máy
   = lỗi uiautomator treo / Gmail UI, KHÔNG phải mail mất. Thực tế 2026-08-06:
   `truongthuy111034@gmail.com` (STT 34) và `macthuong1905200031@gmail.com`
   (STT 31) đều CÓ trong AccountManager dù flow báo "không list". Check thêm
   `dumpsys activity top | grep uri=` — `content://.../<email>/label/...` = Gmail
   đang mở đúng account đó dù uiautomator dump `Killed`/rỗng.
2. **Account THẬT SỰ vắng mặt** (vd `vonhuong2509200436@gmail.com` STT 36 không
   có trong AccountManager) → theo **policy user (chốt 2026-08-06)**: xóa khỏi
   excel + **PHẢI gửi danh sách mail đã xóa cho user kiểm tra lại** — user:
   *"mất mail r thì xoá khỏi excel luôn, hễ máy nào k tra đc mail đó trên máy thì
   xoá nhưng nhớ gửi lại t để t kiểm tra lại"*.
3. uiautomator `Killed`/rỗng trên Samsung = transport treo — KHÔNG dùng dump làm
   bằng chứng account vắng mặt; `dumpsys account` là nguồn sự thật.

### Test env cho Tiktok_Reg — tránh nhiễm hermes venv + mock ADB

- Pytest phải chạy bằng venv recovery (core đúng pin) + PYTHONPATH ưu tiên venv
  site-packages trước (`...tiktok-reg-recovery\Lib\site-packages;...`), KHÔNG để
  hermes venv lọt vào sys.path (hermes venv có PIL hỏng `_imaging` / core sai
  version). Dùng `timeout 90` bọc pytest để không kẹt vô hạn.
- Unit test gọi hàm chạm device (`get_ui_xml`, `shell`) **PHẢI monkeypatch** —
  nếu không, test treo vì gọi ADB thật với device fake (vd
  `_swipe_outlook_inbox_refresh("fake-device")` treo 180s). Pattern:
  `monkeypatch.setattr(social, "get_ui_xml", lambda *a, **k: "<hierarchy/>")`
  + `monkeypatch.setattr(social, "shell", lambda *a, **k: None)`.

### Manifest cũ sau khi xoá mail

Sau khi xoá mail die khỏi source, **PHẢI chạy lại detector** để refresh
manifest (`_detect_clean.py` → `artifacts/pending/tiktok_reg_clean_targets.json`).
Runner đọc file manifest, không đọc live workbook — manifest cũ vẫn trỏ mail đã
xoá → `[07] Email override ... khong co trong Gmail source` → final-block vô ích.

### Recovery runner flags

- `--recover-after-failure` BẮT BUỘC kèm `--full-scope-takeover` (guard dòng
  `if args.recover_after_failure and not args.takeover_locked: raise`).
- Transport recovery chỉ proxy-reassign (`rebooted: false`) — với app crash
  thật (TikTok → Launcher), reassign không cứu; cần `adb reboot` tay trước
  retry. Sau reboot phải đợi VPN watcher (xem mục watcher dưới).

### DEVICE_NOT_PROVISIONED — không phải lỗi setup cứng

Nghĩa: tại thời điểm capture, persistent UI backend (atx-agent) không chạy.
Check nhanh: `ps -A | grep atx` (process), `netstat -tlnp | grep 7912` (LISTEN),
`uiautomator dump` (hoạt động). atx-agent có thể tự lên sau → retry qua được.
Đừng kết luận "máy chưa provision" vĩnh viễn từ 1 lần fail.

## Hotmail mailbox alive check (check_mailbox_alive)

Repo `D:\Taadaa\Hotmail` (taadaa-hotmail). `flows/hotmail_login.py::check_mailbox_alive(adb, device, email, password, artifact_dir) -> str` là wrapper mỏng của `login(force_login=False)` — trả terminal classification cho consumer TikTok OTP (`D:\Taadaa\Tiktok_Reg\social_reg_v1.py` wiring `_canonical_hotmail_check_alive` ở 2 nhánh OTP: timeout + reject; mail `DEAD` bị xoá khỏi source + Audit Pending, `ALIVE`/`UNKNOWN`/`BLOCKED` GIỮ mail — xem mục "Mail-die guard"):

- `ALIVE` — login trả `SUCCESS`/`ALREADY_SIGNED_IN` (inbox reached + account confirmed)
- `DEAD` — login trả status khác (`LOGIN_NOT_VERIFIED`...)
- `BLOCKED` — `LoginBlocked` chứa marker captcha/passkey/protection/wrong password/account could not be confirmed/loginblocked
- `UNKNOWN` — `LoginBlocked` không khớp marker HOẶC exception transport khác (ADB/network) → GIỮ mail, không xoá

**Pitfall "protection" ≠ mail die (STT 54, 2026-08-06)**: `BLOCKED` với marker
"protection"/"Hãy bảo vệ tài khoản của bạn" (account.live.com) KHÔNG phải pass
sai hay 2FA sai — đăng nhập ĐÃ THÀNH CÔNG (màn hình hiện đúng email target),
nhưng Microsoft bắt buộc **thêm email khôi phục (recovery email)** trước khi
vào inbox. Screenshot: tiêu đề "Hãy bảo vệ tài khoản của bạn", ô nhập
`ai_do@example.com`, nút "Tiếp theo". Flow hotmail có `tap_skip_now` (tap "Bỏ
qua bây giờ") để bypass tạm; nếu máy kẹt ở màn hình này + uiautomator treo thì
không qua được. **Mail này KHÔNG die** — consumer KHÔNG xóa khỏi source khi
status=BLOCKED (chỉ DEAD mới xóa, xem mục "Mail-die guard"). Khi nghi ngờ, chụp
screenshot (`adb exec-out screencap -p`) + đọc text để phân biệt "Protect your
account" (còn dùng được, cần skip/bypass) vs wrong password thật. Lưu ý: nếu đã
xóa mail khỏi excel theo logic cũ, báo user để quyết định khôi phục lại hay
giữ xóa.

Contract đã ghi vào `docs/ui-compatibility.md` (entry `hotmail-mailbox-alive-check-20260805`); regression tests `tests/test_hotmail_login.py::MailboxAliveTests`. Commit pattern: chỉ 3 file (flow + test + docs) — docs entry theo mẫu chuẩn (ID/owner, UI signature redacted, selector/fallback, safety bounds, post-action verification, regression tests, nhánh cũ giữ, core version/consumer ảnh hưởng).

**Pitfall unittest.mock — `side_effect` với string**: `patch(..., side_effect="SUCCESS")` KHÔNG trả nguyên string; mock coi string là iterable → trả từng ký tự (`"S"`, `"U"`, `"C"`...) → test fail kỳ lạ ở assert đầu. Fix: bọc fake function:
```python
def _fake_login(*_args, **_kwargs):
    if isinstance(login_result, Exception):
        raise login_result
    return login_result
with patch("flows.hotmail_login.login", side_effect=_fake_login): ...
```

**Pitfall chạy test Hotmail**: full suite cần `PYTHONPATH=.` (test_append_mail_account import `tools.append_mail_account` module-level → collection error `ModuleNotFoundError` nếu thiếu) + `-p no:cacheprovider` (pytest cache không ghi được trên D: → PytestCacheWarning + Permission denied). Target file: `python -m pytest tests/test_hotmail_login.py -q -p no:cacheprovider`; full suite: `PYTHONPATH=. python -m pytest tests/ -q -p no:cacheprovider`. `docs/ui-compatibility.md` dùng CRLF — patch giữ nguyên line ending (git diff chỉ +dòng mới, không đổi toàn file).

## Proxy watcher gan-proxy không chạy sau reboot

Upload fail `DEVICE_LOCK_FAILED` / `proxy readiness timed out` / `tun0 does not
exist` sau reset máy → nghi watcher gan-proxy KHÔNG chạy (máy reset xong không
được gán proxy). Check nhanh:

```bash
wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep -i gan_proxy
schtasks /Query /TN "TikTokAllSchedulerTray" /FO LIST /V | grep -E "Last Result|Status"
```

- **Pitfall false-positive: `cockpit-cliproxy.exe` KHÔNG phải proxy watcher** — nó
  là quota sidecar của Antigravity Cockpit. Chỉ process `gan_proxy_fleet.py
  watch`/`run` mới là watcher thật. `scheduler.recovery_runtime` của
  `tiktok-luot nuoi acc` cũng không phải watcher. Check đúng tên process.
- Sau `adb reboot` tay: app VPN `vn.vichanger.app` KHÔNG tự khởi động → `tun0`
  không lên dù proxy config có trong workbook. Máy healthy có `ps -A | grep
  vichanger` + `ip addr show tun0 | grep inet`. Watcher (khi chạy) xử lý qua
  `VPN_START_NOT_VERIFIED` → `force_stop_relaunch_vichanger`; nếu watcher chết
  thì không ai mở app → VPN chết vĩnh viễn tới khi chạy lại watcher.
- **Pitfall (2026-08-06): watcher CHẠY nhưng KHÔNG gán lại VPN sau reboot** —
  `wmic ... | grep gan_proxy` thấy 2 process watch, nhưng không có fleet-run/log
  mới trong runtime dir sau reboot; mở app thủ công thấy vichanger vào
  `LoginActivity` ("Vi Changer / API Key / Change") hoặc popup
  `No LSPosed access !!!`. **Fix nhanh: tự gọi `set_proxy`** (cơ chế watcher:
  mở app + broadcast START_VPN với proxy value → app connect trong ~5-40s):
  ```python
  # D:\Taadaa\gan-proxy\scripts — proxy từ PROXYgandienthoai.xlsx cột proXy
  from vi_changer_runner import set_proxy, vpn_connected
  set_proxy(ADB, serial, proxy, timeout=45)
  vpn_connected(ADB, serial)   # True sau khi tun0 có inet
  ```
  Đã gán lại 6 máy (30,31,36,54,57,66) trong 1 lượt sau reboot. Verify:
  `adb -s <serial> shell "ip addr show tun0 | grep -c inet"` = 1.

- Watcher được spawn bởi task Windows `TikTokAllSchedulerTray` (chạy lúc logon).
  Task có thể exit lỗi (`Last Result 267014` = terminate/fail) → KHÔNG spawn
  watcher dù task tồn tại. Không có process `gan_proxy_fleet.py watch` = watcher
  chết im lặng, máy nào reset sẽ không lên VPN.
- Fix: chạy lại tray background bằng đúng lệnh trong task (lấy từ
  `schtasks /Query /TN "TikTokAllSchedulerTray" /XML`, phần `<Arguments>`):
  ```bash
  powershell.exe -NoProfile -STA -WindowStyle Hidden -ExecutionPolicy Bypass -File \
    "D:\Taadaa\automation-core\src\automation_core\scheduler\tiktok-scheduler-tray.ps1" \
    -ProxyWatcherScript "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-proxy-watcher.ps1" \
    -ProxyMapping "D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx" \
    -ProxyPythonPath "D:\Taadaa\python-envs\automation\Scripts\python.exe" \
    -ProxyAdbPath "C:\Program Files (x86)\xiaowei\tools\adb.exe" \
    -ProxyRuntime "D:\CodexRuntime\codex_gmail_debug-gan-proxy" -ProxyWorkers 80
  ```
  (chạy qua `terminal background=true`; watcher sẽ spawn 2 process
  `gan_proxy_fleet.py watch --all --workers 80`, poll 30s, tự gán proxy tuần tự
  80 máy — máy 34/36 lên `tun0` trong vòng ~1 phút).
- Verify VPN máy: `adb -s <serial> shell ip addr show tun0` — có `inet ` = OK.
  Marker proxy_ready nằm trong runtime dir `D:\CodexRuntime\codex_gmail_debug-gan-proxy`.

## uiautomator `Killed` EXIT=137 toàn farm — canonical TikTok UI ladder (2026-08-06)

Triệu chứng: `uiautomator dump` trả `Killed` / `EXIT=137` trên MỌI máy; logcat:
```
E AndroidRuntime: at android.app.UiAutomation.connect(UiAutomation.java:223)
E AndroidRuntime: java.lang.RuntimeException: Bad file descriptor
```
→ `UiAutomationService` treo (stale ATX/uiautomator giữ service), KHÔNG phải
ADB mất. atx-agent process vẫn sống nhưng persistent capture fail.

**Policy hiện hành, đúng 4 bước:** (1) ATX kill với evidence → check feed; (2) đúng một TikTok force-stop/relaunch → check feed; (3) đúng một soft reboot **chỉ khi user đã authorize và recovery eligibility/preconditions đạt** → check feed; (4) sau khi ladder cạn, evidence-gated coordinate fallback an toàn → recapture bắt buộc, fail-closed. Không có force-stop/relaunch lần hai; không coordinate fallback nếu soft reboot bị cấm/không eligible. Cùng signature lặp lại không reset các tầng đã tiêu thụ.

Chi tiết + pitfall preflight SKIPPED_LOCKED dù `-RecoveryMode` (phải xoá lock stale trước):
`references/uiautomator-force-stop-atx-20260806.md`.

**Popup "Thêm số điện thoại" (core 0.4.37, máy 27/65)**: onboarding bottom sheet
chỉ có X `content-desc="Đóng"` (KHÔNG "Close") → ACCOUNT_SWITCHER
`Header candidates=0` + WAIT_FEED tưởng màn tối. Rule `add_phone_number_vi` đã
thêm. **Đọc content-desc THẬT từ device XML trước khi viết selector popup mới.**
`dumpsys account | grep 'Account {'` KHÔNG list account TikTok (authenticator
`com.tiktok.auth.type`) — nguồn thật = switcher UI/screenshot (máy 27). Permission
camera/mic khi mở composer (máy 74) nghi chặn nút Paste — cần handler riêng.
Chi tiết: `references/tiktok-onboarding-popups-20260807.md`.
Profile (avatar + chevron) là sheet đã mở. Lặp 2 lần cùng signature → dừng.

**Root cause thật (STT 30)**: dialog **"Tiếp tục chỉnh sửa bài đăng này?"**
(`Lưu bản nháp` / `Chỉnh sửa`, rid `tk5`/`u68`/`tk1`) xuất hiện khi có bài đăng
dở (draft) che account sheet — flow tưởng dropdown đã mở rồi fail. Fix:
`dismiss_edit_post_dialog()` tap "Lưu bản nháp" (fallback tap ngoài dialog),
gọi trong `_wait_account_dropdown_open` (trước permission dismiss) + đầu
`tap_add_account` (dismiss rồi mở lại dropdown + continue). Markers:
`tiep tuc chinh sua bai dang` / `continue editing` / `luu ban nhap` / `save draft`.

**Live-proven**: STT 30 qua được Add account → **VERIFIED_SUCCESS**
`@susannemorti9` cho `susannemortimerabby9@hotmail.com` (row 178, Tik 236,
workbook WRITTEN, backup trước khi ghi) — fix draft-dialog + hotmail recovery
wrapper combo đưa máy từ fail-liên-tục sang SUCCESS. Ad-hoc verify:
`tests/test_hotmail_mail_die_alive_guard.py` + mock `get_ui_xml` trả draft 1
lần rồi trả sạch (nếu mock luôn trả draft → loop 3 attempts → raise; đó là lỗi
test, không phải code).

## Hotmail "Protect your account" → nối `recover_account` (Tiktok_Reg, 2026-08-06)

`hotmail_login` chỉ thử `tap_skip_now` khi gặp account-protection; không có "Bỏ
qua bây giờ" → `LoginBlocked` → consumer break → mail bị xử lý sai. Fix ở
CONSUMER (không sửa repo Hotmail): wrapper
`_canonical_hotmail_login_with_recovery(device_id, email, password)` —
bắt `LoginBlocked` chứa `protection`/`recovery`/`skip now` → gọi
`flows.hotmail_recovery.recover_account(adb, device, artifact_dir,
target_email=email)` (DEFAULT_RECOVERY_EMAIL=`thanhdatbui1995@gmail.com`, đọc
TOTP từ IMAP) → retry login 1 lần. Thay chỗ gọi `_canonical_hotmail_login` trong
`_try_get_otp_browser` bằng wrapper. Import:
`from flows.hotmail_recovery import recover_account as _canonical_hotmail_recover_account`
(lưu ý import thêm làm pytest gộp nhiều file đôi khi collection error transient
— chạy từng file riêng vẫn pass).

**Pitfall Chrome \"Lưu mật khẩu?\" che form recovery (STT 54, 2026-08-06)**: máy
54 gặp Protect → wrapper gọi `recover_account` → fail
`RECOVERY_OTP_SCREEN_NOT_IDENTIFIED`. Artifact `before-recovery.xml` lộ nguyên
nhân: trang `account.live.com/proofs/Add` ĐÚNG, nhưng **Chrome save-password
dialog \"Lưu mật khẩu?\" (bounds [180,252][633,317], nút \"Lưu\") che giữa màn
hình** → flow điền recovery email vào ô save-password thay vì ô email khôi
phục → bấm \"Tiếp theo\" không vào OTP screen. Fix ở consumer (không sửa repo
Hotmail): trong wrapper `_canonical_hotmail_login_with_recovery`, TRƯỚC khi gọi
`recover_account` gọi `_dismiss_chrome_save_password_dialog(device_id)` — detect
marker `luu mat khau`/`save password` (strip_accents, đừng chỉ `"luu"` — nút
\"Lưu\" trong dialog là subset), tap `Không bao giờ`/`Never`/`Lưu`, fallback tap
ngoài dialog (960,300). Rule chung: bất kỳ flow web nào bị Chrome popup che form
(save-password, translate, notification-permission) đều phải dismiss popup
TRƯỚC khi điền field — XML artifact `before-*` là nơi bắt được popup.

## Hotmail OTP sau resend — swipe refresh phải đưa Chrome lên foreground trước (2026-08-06)

Bổ sung cho fix CDP-reload ở trên: `_swipe_outlook_inbox_refresh` cũ chỉ swipe
khi XML chứa `com.android.chrome` — nhưng sau khi bấm `Gửi lại mã`, máy đang ở
**TikTok OTP screen** (Chrome background) → trả False → không lấy được code mới
(STT 57/66 vẫn `refusing reuse`). Fix: khi Chrome không foreground, đưa Chrome
về trước qua `am start --activity-reorder-to-front -n
com.android.chrome/com.google.android.apps.chrome.Main` (giữ session tab cũ),
sleep 2s, re-dump; nếu vẫn chưa được → `input keyevent 187` (Recents) + dump;
chỉ swipe khi đã xác nhận Chrome foreground. Verify sau swipe:
`com.android.chrome` còn trong XML.

## DEVICE_STARTUP_FAILED — clear_all button / empty-recents (uiautomator treo)

Lỗi startup: `[DEVICE_STARTUP_FAILED] clear_all button and empty-recents evidence not found`.
User hỏi đúng: *"không có app nào mở thì sao hiện clear recent được?"* — phân biệt 2 trường hợp:

1. **Recent thực sự trống** (không app mở) → hợp lệ, KHÔNG phải lỗi. Consumer có
   nhánh riêng: `_verify_localized_empty_recents` kiểm tra text
   "không có ứng dụng đã dùng gần đây".
2. **Recent CÓ app nhưng core không tìm thấy clear-all** → lỗi thật do
   `automation_core/startup.py::close_all_recent_apps` dùng `dump_current_ui`
   (= uiautomator) → **treo trên Samsung** → XML rỗng → không tìm thấy nút.
   Verifier `_verify_localized_empty_recents` CŨNG dùng uiautomator → fail kép.

Chẩn đoán (xác minh thực tế trước khi kết luận):
```bash
adb -s <serial> shell input keyevent 187   # mở Recent
adb -s <serial> exec-out screencap -p > recents.png   # xem có app card không
adb -s <serial> shell dumpsys activity activities | grep mResumedActivity
# → RecentsActivity + có app card = trường hợp 2 (uiautomator treo)
```
Dấu hiệu phụ: màn hình Recent **xoay ngang 1920x1080** (app landscape) làm layout
khác → detect clear-all càng khó.

**ĐÃ FIX ở consumer (2026-08-05, commit `076ba05`, COMPAT-RECENTS-001)** — không
chờ core patch nữa:
- `StateMachine._recents_empty_via_dumpsys(adb)` — verify Recent rỗng bằng
  `adb shell dumpsys activity recents`, KHÔNG cần uiautomator (không treo). Parse
  từng dòng `Recent #N: TaskRecord{... A=<pkg> ...}`, loại trừ task luôn tồn tại
  (`com.sec.android.app.launcher`, `com.android.launcher3`,
  `com.android.systemui`), còn app task nào = chưa rỗng.
- `_close_recent_apps`: khi core `close_all_recent_apps` fail → **ưu tiên
  dumpsys probe trước**, fallback `_verify_localized_empty_recents` (uiautomator)
  CHỈ khi dumpsys không kết luận được (shell lỗi/ok=False).
- 3 regression tests: `test_recents_empty_via_dumpsys_accepts_only_launcher_systemui`,
  `test_recents_empty_via_dumpsys_detects_app_task`,
  `test_close_recent_apps_prefers_dumpsys_when_core_fails`.
- Pitfall khi patch: dumpsys result có thể là `SimpleNamespace` không có `stdout`
  (mock test) → dùng `getattr(result, "stdout", "")`. Khi patch khối if/else dài
  dễ mất dòng `self.context.recents_closed = True` — verify diff sau mỗi patch.

## Workbook là bằng chứng hoàn tất khi report thiếu/FAILED

Khi batch bị kill (foreground timeout hoặc user interrupt) lúc cuối run
(RELEASE/cleanup sau VERIFY_POST), report.json có thể KHÔNG được ghi hoặc ghi
`FAILED` dù video ĐÃ đăng xong. Cách xác định đúng:

- **Workbook `Video Đã Đăng` tăng = bằng chứng mạnh nhất** (atomic-update chỉ xảy
  ra sau VERIFY_POST success). Máy 36: workbook 3→4 nhưng report cuối `FAILED`
  (batch kill lúc RELEASE) → thực chất ĐÃ xong, không cần retry.
- Post-attempt `status: verification_pending` + `post_submission_state: ACCEPTED`
  + workbook tăng → đăng thành công, chỉ thiếu report.
- Ngược lại: workbook KHÔNG tăng + `verification_pending` → post mơ hồ, cần
  hậu kiểm (chạy lại, receipt barrier chống repost).
- Luôn cross-check: report cuối (timestamp mới nhất) + workbook + post-attempt,
  không dựa một nguồn duy nhất.

**Xác minh máy SUCCESS — 3 nguồn khớp (2026-08-06)**: máy báo THÀNH CÔNG (exit=0,
verified=True) phải thỏa CẢ: (a) workbook `Video Đã Đăng` tăng đúng 1 so với baseline
receipt cao nhất, (b) số receipt `completed` = số video đã đăng, không còn
`verification_pending`, (c) máy về `LauncherActivity` (home) — máy FAIL giữ nguyên
`SplashActivity` (đúng contract giữ trạng thái lỗi). 5 máy success batch 2026-08-06
đều khớp cả 3; máy success mà vẫn ở Splash = nghi ngờ.

**Pitfall đọc launcher output — PowerShell UTF-16 trong bash**: chạy
`run_tiktok_upload_batch.ps1` qua terminal bash, output tiếng Việt bị
`Binary file matches` khi grep / UTF-16 mojibake (`M�y m?c ti�u`) khi iconv sai.
Đọc nhanh: đừng parse stdout — đọc thẳng `batch-runs/batch_tik1_*/summary.csv`
mới nhất (`max(glob, key=os.path.getmtime)`) qua python csv, cột `Status` +
`SkipReason`. Batch dir name chứa luôn scope máy (vd `batch_tik1_5_10_21_..._213042`)
→ xác nhận manifest đúng scope không cần đọc stdout.

## CAPTION_FILL "Caption field not found via selectors" (composer UI variant)

Lỗi: vào CAPTION_FILL, chọn được hashtag (`Đã chọn 4 hashtag`) nhưng
`_find_caption_field` trả None → `Caption field not found via selectors` → fail
sau 3 attempt (máy 74, TikTok **46.2.3**, 2026-08-05).

- `_find_caption_field` tìm theo thứ tự: resource_id (`g9u`, `gv0`,
  `caption_edit_text`, `description_edit_text`, `post_description`, `edit_text`)
  → text markers (`Suy nghĩ của bạn`, `Thêm mô tả`, `Viết mô tả`, ...) → fallback
  EditText bounds ≥400x60. Fail = không khớp selector nào → UI composer version
  dùng resource_id/text khác.
- **Nghi version-specific**: máy 34 (TikTok **46.3.3**) đăng OK cùng flow; máy 74
  (46.2.3) fail caption. Check version:
  `adb -s <serial> shell dumpsys package com.ss.android.ugc.trill | grep versionName`.
  Máy 22 cũng 46.2.3 nhưng từng đăng thành công → composer 46.2.3 vẫn dùng được,
  lỗi có thể là UI chưa load xong lúc dump (chỉ sleep 2s) hoặc surface khác.
- Chẩn đoán: chạy lại máy, bắt UI dump lúc CAPTION_FILL (`ui_capture_*.json` chỉ
  là event log có `xml_bytes` — XML thật nằm trong event `VERIFIED_XML` nếu log
  đầy đủ; nếu không, cần capture trực tiếp). So resource_id thật vs danh sách
  selector → thêm selector mới + regression test + COMPAT entry (theo rule
  handler bắt buộc).
- Lưu ý: lỗi này có thể tự hết khi retry (UI load chậm) — nhưng theo rule
  handler bắt buộc, nếu tái diễn phải implement handler, không bỏ qua vì
  "transient".

## CAPTION "Clipboard setup failed" — broadcast not-ok → hashtag fallback (COMPAT-CAPTION-001)

Signature khác với "Caption field not found": `[WARNING] Clipboard setup failed`
ở attempt 1/2/3 trong CAPTION_FILL (máy 74, 2026-08-05) — caption chọn được
hashtag nhưng `am broadcast -a clipboard.set -e text <caption>` trả not-ok →
`_fill_caption_clipboard` return False.

Chẩn đoán trước khi kết luận:
```bash
adb -s <serial> shell am broadcast -a clipboard.set -e text "test_123"  # thử tay
adb -s <serial> shell service list | grep -i clipboard   # clipboard + semclipboard còn sống?
adb -s <serial> shell dumpsys meminfo | grep -i "Free RAM"
```
- Broadcast thử tay OK + service `clipboard`/`semclipboard` sống + RAM ổn →
  KHÔNG phải service chết. **QUAN TRỌNG: thử tay phải dùng caption CÓ `#`
  (hashtag), không chỉ "test_123"** — broadcast ngắn không `#` luôn OK kể cả
  khi bug escape `#` tồn tại; caption hashtag 50-65 chars fail vĩnh viễn với
  `Argument expected after "text"` (xem COMPAT-CAPTION-003 — root cause thật).
- Root cause trong code: `_fill_caption_clipboard` return False NGAY khi
  `not clipboard_result.ok` mà KHÔNG thử `_fill_caption_with_tiktok_hashtag_button`
  (fallback đã có sẵn: gõ từng token qua `input text` + `KEYCODE_SPACE`, dùng
  TikTok # shortcut).

**ĐÃ FIX (commit `47036a7`, COMPAT-CAPTION-001)**: khi `not clipboard_result.ok`
→ thử `_fill_caption_with_tiktok_hashtag_button(caption)` trước, verified thì
return True, còn fail mới return False. Regression:
`test_caption_clipboard_fail_falls_back_to_hashtag_button` (mock
`args[1] == "broadcast"` → FailResult, còn lại OkResult; mock
`_input_hashtag_marker → True`).

**Pitfall chạy test caption**: các test caption nằm trong class
`TestCaptionFill` (KHÔNG phải `TestStateMachine`) — node ID đúng:
`tests/test_tiktok_workflow.py::TestCaptionFill::test_caption_...`. Dùng sai
class prefix → pytest "no match in any of [<Module ...>]" (đã dính 2 lần trong
ad-hoc verify).

## CAPTION "Không thể xoá caption cũ" — field mất focus sau fallback (COMPAT-CAPTION-002)

Lỗi tiếp theo trong chuỗi caption fail (máy 74, 2026-08-05): sau khi clipboard
fail → hashtag fallback gõ caption, retry vào CAPTION_FILL lần nữa báo
`Không thể xoá caption cũ trước khi nhập lại` (attempt 3/3) → fail. Root cause:
`_clear_caption_input` chạy `KEYCODE_MOVE_END` + 256× `KEYCODE_DEL` nhưng
**caption field mất focus** sau clipboard/hashtag fallback → keyevent không có
tác dụng → `end_result.ok/delete_result.ok` vẫn True (lệnh chạy) nhưng UI không
đổi → clear "thành công" mà caption cũ còn → verify fail.

**ĐÃ FIX (commit `78ec9d0`, COMPAT-CAPTION-002)**: `_clear_caption_input` tap
caption field trước (`_find_caption_field(adapter, adapter.dump_ui())` →
`adapter.tap(*field["center"])` + sleep 0.5) để regain focus, RỒI MOVE_END +
DEL. Nếu không tìm thấy field vẫn thử MOVE_END + DEL như cũ (test cũ giữ
hành vi). Regression: `test_clear_caption_input_taps_field_when_visible` +
`test_clear_caption_input_uses_single_long_delete`.

**Chuỗi caption fail đầy đủ máy 74 (mỗi lỗi 1 handler riêng, đừng gộp):**
`Caption field not found` (UI load timing, transient) → `Clipboard setup
failed` (COMPAT-CAPTION-001 fallback hashtag → COMPAT-CAPTION-003 escape `#`
= root cause THẬT) → `Không thể xoá caption cũ` (COMPAT-CAPTION-002, tap
field trước khi clear). Mỗi signature nhìn giống "caption lỗi" nhưng root
cause khác nhau — chẩn đoán log line cụ thể trước khi patch.

**Signature MỚI: `Paste action not found` (máy 74, 2026-08-06)** — clipboard
broadcast OK (escape `#` đã fix) nhưng sau paste không tìm thấy paste action
menu → 3/3 attempts fail → FAILED exit=1 (khác hẳn MANUAL_REVIEW exit=2).
**Chưa có handler** — theo rule bắt buộc phải implement handler + regression
test + COMPAT entry trước khi retry (bắt XML lúc fail để biết paste menu
variant). Chi tiết: `references/retry-batch-recovery-20260806.md`.

## CAPTION "Clipboard setup failed" — root cause `#` bị ADB shell nuốt (COMPAT-CAPTION-003)

**Đây là root cause THẬT của clipboard fail kéo dài máy 74** (2026-08-05) —
sau khi CAPTION-001 (fallback hashtag) và CAPTION-002 (tap field) vẫn fail
lặp lại. Chẩn đoán phân biệt CAPTION-001 (transient) vs CAPTION-003 (bug):

```bash
# broadcast caption NGẮN (không #): OK
adb -s <serial> shell am broadcast -a clipboard.set -e text "test_abc"
# → Broadcast completed: result=0

# broadcast caption CÓ # (hashtag): FAIL — shell cắt từ #
adb -s <serial> shell am broadcast -a clipboard.set -e text "#meocung #thucung"
# → Exception occurred while executing:
#   java.lang.IllegalArgumentException: Argument expected after "text"
#   (caption dài 50-65 chars với # luôn fail; clipboard service vẫn sống)
```

**Root cause**: ADB shell coi `#` là bắt đầu comment → cắt phần còn lại của
caption → `am broadcast -e text` thiếu argument → `clipboard_result.ok=False`.
Service clipboard/semclipboard sống, RAM ổn, broadcast ngắn OK — nên chẩn
đoán CAPTION-001 (service chết/transient) SAI. Dấu hiệu phân biệt: caption
toàn hashtag fail MỌI lần (không phải thỉnh thoảng), broadcast tay với `#`
cũng fail đúng lỗi `Argument expected after "text"`.

**ĐÃ FIX (commit `95732e2`, COMPAT-CAPTION-003)**: escape `#` → `\#` trước
broadcast:
```python
escaped_caption = caption.replace("#", "\\#")
clipboard_result = adapter._adb.shell(
    ["am", "broadcast", "-a", "clipboard.set", "-e", "text", escaped_caption], ...)
```
Verify live: escaped `result=0`, unescaped `Exception occurred`. Regression:
`test_caption_unicode_uses_clipboard_and_verifies_paste` (assert calls chứa
`"\\#việt nam"`). Lưu ý `_escape_adb_input_text` hiện chỉ escape `\` + space
(`%s`) — KHÔNG escape `#`; nếu dùng nó cho broadcast phải bổ sung.

**Pitfall vòng lặp khi fix sai hướng**: máy 74 fail clipboard nhiều lần →
mỗi lần xóa fingerprint video 4 reserved rồi rerun → workflow tự reserve LẠI
đầu run → fail tiếp → lại xóa (dính 3-4 lần). Rule: khi cùng signature lặp
≥2 lần, DỪNG xóa-rerun, đọc report/last_state signature + thử broadcast tay
với chính caption dài có `#` để phân biệt transient vs bug escape. Xóa
fingerprint chỉ mở khóa chạy, không sửa lỗi gốc.

## Điều tra video trùng (duplicate) — root cause `PROVEN_NOT_POSTED` retry mùKhi user báo "video đăng trùng video trước" (máy 37, 2026-08-05), điều tra theo
thứ tự:

1. **Loại trừ nguồn trùng**: hash full file nguồn (`hashlib.sha256(open(p,'rb').read())`)
   so với `media_sha256` trong fingerprint ledger — máy 37 file 1-5 đều khác nhau,
   nguồn KHÔNG trùng → duplicate do cơ chế đăng, không phải file.
2. **Đọc post-attempt receipt** (`idempotency/post-attempts/machine_X_video_N.json`):
   tìm dấu hiệu đăng 2 lần:
   - `post_attempt_count: 2` + `post_retry_used: True` + `post_tapped_at` và
     `post_retry_tapped_at` cách nhau vài phút → **cùng video bấm Post 2 lần**.
   - `post_recheck_proof: PROVEN_NOT_POSTED` → hậu kiểm nói "chưa đăng" → retry.
3. **Root cause duplicate (đã xác nhận máy 37 video 3 & 5)**:
   code cũ (trước 05/08) cấp `PROVEN_NOT_POSTED` → retry khi submission state
   `UNKNOWN`/`None` — KHÔNG yêu cầu bằng chứng `NOT_ACCEPTED`. Khi lần 1 bấm Post
   nhưng verify fail (`PROFILE_ROOT_NOT_CONFIRMED`, tile chưa load, timeout) →
   hậu kiểm tưởng "chưa đăng" → bấm Post lại → **cùng video đăng 2 lần → trùng**.
4. **Guard đã thêm (commit `9e12a51`)**: retry chỉ khi
   `post_submission_state == "NOT_ACCEPTED"` (bằng chứng rõ chưa đăng);
   `UNKNOWN`/`ACCEPTED`/None → chặn repost, giữ MANUAL_REVIEW. Comment trong code:
   *"Legacy verification_pending receipts ... Treat them as accepted/ambiguous,
   never as safe-to-repost."* Lần sau không tái diễn duplicate kiểu này.
5. **Kiểm tra code hiện tại đã có guard chưa** trước khi kết luận bug còn sống:
   `git log -S "NOT_ACCEPTED" --oneline -- scripts/tiktok_workflow/state_machine.py`
   — nếu guard xuất hiện SAU thời điểm máy chạy thì bug đã được sửa, chỉ cần ghi
   nhận lịch sử, không sửa lại.

Pattern phát hiện nhanh duplicate: `post_attempt_count>=2 && post_retry_used=True`
trong receipt = nghi ngờ đăng trùng, kiểm tra `post_recheck_proof` có
`PROVEN_NOT_POSTED` không và submission state lúc đó là gì.

## DRAFT_CLEANUP_FAILED + POST_VERIFY_PROOF_INSUFFICIENT (máy 74, 2026-08-05)

Hai lỗi nối tiếp trên cùng máy 74 (TikTok 46.2.3) khi retry đăng video 3:

**1. `DRAFT_CLEANUP_FAILED` — "Không xoá được toàn bộ bản nháp"** (state
ACCOUNT_READY, trước khi vào composer): `_delete_all_profile_drafts` chạy chuỗi
tap `Bản nháp` → `Chọn` → `Chọn tất cả` → `Xóa` → `Xóa` (confirm) → verify
`"bản nháp" not in xml`. Log lộ `[DRAFT_CLEANUP] Vẫn còn bản nháp sau khi xoá`
= đi hết chuỗi nhưng XML cuối vẫn chứa text "bản nháp" (xác nhận Xóa không
ăn / UI chưa cập nhật / verify quá sớm). **Transient — retry qua được**: lần
chạy kế tiếp vào thẳng ACCOUNT_SWITCHER không dính draft nữa (draft đã hết từ
lần trước). Đừng sửa handler ngay khi chỉ fail 1 lần; nếu tái diễn → chẩn đoán
bước nào chết (bắt XML sau từng tap) rồi mới thêm handler + COMPAT entry.

Xử lý đúng (giống pattern máy 22): **giữ nguyên fingerprint (đã ACCEPTED —
xóa = nguy cơ duplicate), chạy lại workflow để hậu kiểm tile** — receipt
barrier chặn repost. Tile tăng → ghi workbook; tile vẫn baseline → điều tra
(TikTok xử lý chậm vs đăng thất bại ngầm dù ACCEPTED). Phân biệt với máy 5
video 6 (`verification_pending` + tile không tăng nhưng workbook cuối vẫn
tăng — bài đăng thành công trễ): luôn cross-check workbook + post-attempt +
report, không kết luận theo 1 nguồn.

**Kết cục máy 74 (hậu kiểm lần 2, cùng ngày)**: chạy lại workflow để hậu kiểm
(receipt ACCEPTED giữ nguyên, KHÔNG xóa fingerprint) — vẫn `MANUAL_REVIEW` +
`POST_VERIFY_PROOF_INSUFFICIENT`, `Profile video tiles: 2 (baseline=2)` sau
~25 phút kể từ lúc bấm Post. Chẩn đoán bổ sung bằng pixel — đếm tile thật:
```python
a = np.asarray(Image.open("profile.png").convert("L"))
grid = (a[900:1560, :] < 100).astype(np.uint8)
# segment cột/hàng tối liên tục (col_sums>50, row_sums>50) → ước lượng tile
```
Máy 74 cho 2 cột × 2 hàng = 4 khối tối nhưng **layout 2-cột (tile rộng ~360px)
vs 3-cột (tile ~180px) KHÔNG phân biệt được bằng threshold đơn** → kết luận mơ
hồ → **nhờ user nhìn máy xác nhận** (user xác nhận = bằng chứng mạnh hơn pixel,
cùng rule với avatar). Khi ACCEPTED + tile không tăng sau 20+ phút: khả năng
video bị set private/ẩn, đăng nhầm account, hoặc TikTok xử lý chậm — không tự
đăng lại mù, giữ fingerprint + hỏi user.

**Cách BIẾT video bị ẩn hay không — verify qua TikTok web API (không cần login):**
```bash
# videoCount trên profile CÔNG KHAI = số video public thật
curl -s --max-time 15 "https://www.tiktok.com/@<username>?lang=en" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0" \
  | grep -oE '"videoCount":[0-9]+'
# máy 74 (muyduyen4589): videoCount:2 → video 3 ACCEPTED nhưng KHÔNG public
# cũng đọc được stats: {"followerCount":0,"followingCount":1,"heartCount":1,"videoCount":2,...}
```
- `videoCount == baseline` → bài ACCEPTED **không hiện public** → bị ẩn
  (private/moderated) hoặc không thực sự đăng.
- Response web KHÔNG có `privateItemCount` cho người ngoài → **không phân biệt
  được "private" (vẫn xem được trong app chủ TK) vs "moderated/removed" từ web**.
  Cách duy nhất: mở app máy, tab "Riêng tư" (private videos) — nếu video nằm đó
  → bị private; không thấy → bị removed. Hoặc user xác nhận trực tiếp.
- Browser nặng (TikTok web có bot detection, snapshot rỗng) — dùng curl thẳng
  HTML + grep là đủ; `?lang=en` ổn định hơn.
- Sau khi xác nhận ẩn: user quyết định đăng lại (chấp nhận rủi ro duplicate nếu
  thật sự đã private) vs bỏ video chuyển video khác vs chờ thêm — KHÔNG tự đăng
  lại mù vì fingerprint còn `reserved` + receipt `verification_pending`.

**Bỏ hẳn video bị ẩn — đánh dấu receipt `completed` để skip vĩnh viễn (máy 74, 2026-08-05):**
khi user chọn "bỏ video luôn", nếu chỉ xóa fingerprint + giữ workbook, lần sau
workflow resolve video kế tiếp = posted+1 → **lại resolve đúng video bị ẩn đó** →
đăng lại bài chặn. Phải đánh dấu receipt để cursor skip:

1. **Cơ chế skip trong code** (state_machine.py):
   - `_find_completed_post_receipts_for_machine` (~line 5982) CHỈ đếm receipt có
     `status == "completed"` (khớp `machine` + `target_account`).
   - `_advance_video_cursor_past_completed_receipts` (~line 6006) tự tăng
     `video_number` qua mọi video đã completed → resolve video kế tiếp.
   - `_route_existing_post_receipt_to_verification` (~line 6598) trả False với
     status=completed (không route verify lại).
2. **Thao tác** (backup trước):
   ```python
   pa = "idempotency/post-attempts/machine_74_video_3.json"
   d["status"] = "completed"                    # verification_pending → completed
   d["post_outcome"] = "SUPPRESSED_NOT_PUBLIC"  # đánh dấu rõ KHÔNG phải đăng thành công
   d["post_outcome_reason"] = "TikTok ACCEPTED but not public (videoCount=2 via web API); user dropped"
   d["post_outcome_resolved_at"] = <iso>
   # + xóa fingerprint video đó (chỉ khi status=reserved, chưa verify) — backup kèm
   ```
   Không có code nào tự sync workbook từ receipt `completed` → workbook KHÔNG bị
   đếm nhầm thành "đã đăng". Field `post_outcome` bắt buộc để người đọc sau
   không tưởng nhầm đây là post thành công.
3. **Verify live**: chạy lại workflow máy 74 → push `585/4.mp4` (video 4) thay vì
   video 3 — cơ chế skip hoạt động, video 3 không bao giờ bị resolve lại.
4. Trả lời user "verify lệch thì sao": receipt completed + outcome rõ ràng =
   cursor tự skip; workbook vẫn phản ánh đúng số video public thực tế.

## COMPAT-GRID-001 — profile-grid swipe timeout làm tile count sai → false MANUAL_REVIEW

Sau khi video 4 máy 74 ĐĂNG THÀNH CÔNG (caption qua nhờ CAPTION-003, POST +
published-surface gate matched=True) nhưng workflow vẫn `POST_VERIFY_PROOF_INSUFFICIENT`:
`[PROFILE_GRID] Unique video tiles across 1 viewport(s): 2 (baseline=2)` trong khi
web API xác nhận `videoCount=3` (video public). **Verifier đếm SAI, không phải
đăng thất bại.**

Root cause (log rõ): `adb command timed out: ('...adb.exe', '-s', serial,
'shell', 'input', 'swipe', '540', '1729', '540', '1242', '450')` — máy Samsung
chậm (máy 74) mất >10s cho 1 swipe → `adb.shell(timeout=10)` timeout →
`scroll_profile_grid` (adapter.py) break → chỉ 1 viewport → tile count thiếu.

**ĐÃ FIX (commit `d0b8dea`, COMPAT-GRID-001)**: trong `scroll_profile_grid`,
swipe fail/timeout lần đầu → **retry 1 lần với timeout 30s** trước khi bỏ
viewport:
```python
result = self._adb.shell([...swipe...], timeout=10, check=False)
if not getattr(result, "ok", False):
    logger.warning("[PROFILE_GRID] Swipe %d thất bại/timeout; retry với timeout 30s", swipe_index)
    result = self._adb.shell([...swipe...], timeout=30, check=False)
if not getattr(result, "ok", False):
    logger.warning("[PROFILE_GRID] Swipe %d thất bại; giữ evidence hiện tại", swipe_index)
    break
```
Regression: `test_scroll_profile_grid_retries_swipe_on_timeout` (mock shell:
lần 1 ok=False → assert shell_calls[1]["timeout"]==30). Test scroll cũ nằm
module-level (`test_adapter_profile_grid_scroll_is_resolution_aware_and_bounded`),
không phải class — node ID không có prefix class.

**Pattern xử lý khi web API xác nhận nhưng verifier tile count fail** (máy 74
video 4, 2026-08-05) — đối lập với SUPPRESSED_NOT_PUBLIC:
- `curl ... https://www.tiktok.com/@<user>?lang=en | grep -oE '"videoCount":[0-9]+'`
  trả **baseline+1** → bài ĐÃ public dù tile count workflow sai (swipe timeout).
- Xử lý: receipt post-attempt → `status="completed"` +
  `post_outcome="PUBLISHED_VERIFIED_WEB_API"` + `post_verify_evidence="web_api_videoCount_3_20260805"`
  + `post_verified=True`; fingerprint → `verified_success`; workbook posted+1.
  KHÔNG đăng lại mù (video đã public — đăng lại = duplicate).
- Phân biệt: `videoCount == baseline` → SUPPRESSED_NOT_PUBLIC (bỏ video, xem
  pattern trên); `videoCount > baseline` → PUBLISHED_VERIFIED_WEB_API (ghi nhận
  thành công). Web API là bằng chứng mạnh hơn tile count khi verifier bị
  timeout/UI treo.

**Pitfall "verify lại" = workflow sẽ tự đăng video KẾ TIẾP (máy 74, 2026-08-05):**
sau khi GRID-001 fix, user yêu cầu \"đúng verify lại\" máy 74 — chạy lại workflow
với manifest retry cũ. Kết quả: verifier giờ đếm ĐÚNG (tile=3, fix hoạt động
live) → post-attempt video 4 completed → workflow **tự resolve video 5
(posted+1) và bắt đầu push `585/5.mp4`** — chỉ dừng vì tôi kill kịp trước khi
bấm Post. Bài học:
- **Chạy lại workflow KHÔNG bao giờ là \"chỉ verify\"** — nếu máy đã ở trạng
  thái hoàn tất (receipt completed / workbook đã ghi), workflow resolve video
  kế tiếp và bắt đầu đăng. Muốn chỉ hậu kiểm: dùng manifest scope rỗng đúng
  máy + sẵn sàng kill ngay khi thấy `Pushing .../N+1.mp4` TRƯỚC khi vào
  composer, hoặc xác nhận trước với user rằng \"chạy lại = đăng video mới\".
- Sau kill kịp: kiểm tra `post-attempts/machine_X_video_{N+1}.json` KHÔNG tồn
  tại (chưa bấm Post = an toàn), xóa fingerprint `reserved` của video N+1
  (chưa post-attempt), dọn lock stale — máy về SplashActivity là sạch.
- Dấu hiệu nhận biết sớm trong log: `Pushing D:\\...\\{N+1}.mp4` +
  `[MEDIA_FINGERPRINT] Backfilled ... verified source hash(es)` — kill ngay,
  đừng đợi CAPTION_FILL.

## Mail-die guard — CẤM xóa mail sống (Tiktok_Reg, 2026-08-06)

**Sự cố**: run recovery xóa 3 mail CÒN SỐNG khỏi `gmail_clean_v2.xlsx` (STT 54
`eulalia...`, 57 `Derek...`, 36 `vonhuong...`) vì điều kiện xóa chỉ dựa trên
`_outlook_inbox_visible(current_xml)` trả False — UI dump không hiện inbox
(Chrome navigate đi sau resend) KHÔNG chứng minh mail die, dù
`check_mailbox_alive` trả `ALIVE`. Fix áp dụng cho CẢ 2 nhánh (otp-refresh +
`[7c]`).

**TRẠNG THÁI CUỐI (sau 2 vòng fix — đúng code hiện tại)**: CHỈ xóa khi
`inbox_status == "DEAD"` VÀ inbox không visible. `ALIVE` / `UNKNOWN` /
`BLOCKED` đều GIỮ mail:
```python
# nhánh otp-refresh
if inbox_status == "DEAD" and not _outlook_inbox_visible(current_xml):  # xóa
else:  # giữ
# nhánh [7c]
elif inbox_status in {"ALIVE", "UNKNOWN", "BLOCKED"}:  # giữ
else:  # chỉ DEAD lọt vào đây
```
Lý do đưa `BLOCKED` vào nhóm giữ (vòng fix 2, sau khi STT 54 lại bị xóa lần 2):
`check_mailbox_alive` map MỌI `LoginBlocked` có marker
captcha/passkey/**protection**/wrong-password → `BLOCKED`, không phân biệt được
Protect-account prompt (mail còn sống, chỉ cần recovery email) vs wrong-password
thật. Cả 2 đều cần xử lý thủ công → không auto-xóa; chỉ `DEAD` (login chạy hết
mà không verify được inbox) là chết thật. Regression:
`test_blocked_mail_not_deleted` trong `tests/test_hotmail_mail_die_alive_guard.py`.

Rules bắt buộc:
- Chỉ xóa mail khỏi source khi **CAPTCHA-confirmed** (Google reCAPTCHA/identity
  blocker có evidence) hoặc `check_mailbox_alive` trả `DEAD`.
- Account không có trong AccountManager ≠ mail die (STT 36 account vắng nhưng
  mail phải giữ trong source — đã restore).
- Mail bị xóa nhầm → restore từ
  `workbook-backups/gmail_clean_v2_before_captcha_delete_<mail>_<ts>.xlsx` vào
  đúng vị trí (trước row máy kế tiếp) + xóa Audit Pending sai. Pattern script:
  `scripts/restore_sttXX_source.py` + `scripts/remove_audit_sttXX.py` (backup
  trước khi sửa, `insert_rows` đúng vị trí, reopen verify, SKIP nếu đã có).
- Regression test phải gọi **caller** (`_enter_tiktok_email_otp_with_one_fresh_retry`
  với `enter_otp_code→False`), KHÔNG phải hàm con — nhánh mail-die nằm ở caller
  sau khi fresh-read trả None, hàm con trả None sớm ở nhánh "refusing reuse".
  Test file: `tests/test_hotmail_mail_die_alive_guard.py`.

## Retry cuối (2026-08-06) — blocker còn lại là NGHIỆP VỤ, không phải bug code

Sau khi toàn bộ fix code hoạt động (draft-dialog, mail-die guard, OTP marker-node, swipe refresh, hotmail recovery wrapper), retry 31/34/54/57/66 vẫn 5/5 FINAL_BLOCKED — nhưng mỗi signature giờ là **blocker nghiệp vụ/môi trường**, KHÔNG phải lỗi script:

| STT | Blocker | Loại | Hướng xử lý |
|---|---|---|---|
| 57/66 | TikTok **reject OTP dù code đúng + mới** (`Fresh code found` → nhập → reject) | TikTok chặn device/IP fingerprint (reg quá nhiều cùng proxy) | **đổi proxy/fingerprint**, không retry code |
| 57/66 | CDP sau swipe vẫn trả **code cũ** (`refusing reuse`) | mail TikTok mới **chưa tới inbox** trong thời gian chờ — swipe không lỗi | chờ lâu hơn / đổi proxy; không phải bug swipe |
| 31/34 | Gmail `target_account_unverified` dù account CÓ trong AccountManager | Gmail app đang hiện **account khác** (multi-account), account switcher không chọn đúng | dọn account thừa / chọn đúng account trong Gmail app trước retry |
| 54 | Protect account → `recover_account` fail `RECOVERY_OTP_SCREEN_NOT_IDENTIFIED` | Microsoft recovery OTP screen không nhận diện được trên máy đó | xử lý thủ công / cấp mail khác |
| 34 | `[otp-enter] TikTok OTP screen unavailable after Recents recovery` | máy rời OTP screen giữa recovery (Recents) | retry khi máy về đúng surface |

**Bài học chính**: khi đã hết bug code (guard + test pass + live-proven), đừng retry mù cùng signature — phân loại blocker còn lại là (a) nghiệp vụ cần đổi proxy/mail thủ công, (b) cần dọn trạng thái máy (Gmail multi-account, surface kẹt). Retry thêm cùng signature = tốn thời gian, kết quả giống nhau. Chi tiết: `references/tiktok-reg-final-retry-20260806.md`.

## CDP-only KHÔNG đủ — mở Chrome fullscreen lúc login vẫn giết OTP screen (S7, 2026-08-06)

Thử nghiệm fix \"CDP-only\" (giữ TikTok foreground suốt flow): thêm `_restore_tiktok_foreground()` (helper `am start --activity-reorder-to-front -a MAIN -c LAUNCHER -p com.ss.android.ugc.trill` — reorder task cũ, KHÔNG launch flow mới) vào `_try_get_otp_browser`, khi inbox sẵn sàng thì reorder TikTok lên trước rồi đọc OTP qua `_try_get_otp_outlook_cdp` (tab nền) thay vì tìm trong Chrome UI. Verified 10/10 ad-hoc + pytest. **Kết quả run thật: 5/5 vẫn FINAL_BLOCKED** với cùng `OTP_SCREEN_NOT_PRESERVED` / `OTP screen unavailable after Recents recovery`.

**Kết luận hệ thống (đã xác nhận qua 4 run liên tiếp):** trên Samsung S7, **BẤT KỲ lúc nào mở Chrome/Gmail app fullscreen để login/inbox (dù ngắn, dù sau đó reorder TikTok về) cũng kill TikTok OTP activity** — vì phase login (nhập email/pass/cookie, vài chục giây) đủ lâu để Android giết activity nền. Fix CDP-only chỉ có tác dụng khi **Chrome ĐÃ login sẵn** (không cần mở lại).

**Hướng khả thi duy nhất (chưa implement, chờ user duyệt):**
1. **Pre-login Chrome trước khi chạy reg** — mở sẵn Outlook/Gmail web đã đăng nhập trên máy (1 lần, script riêng) → flow OTP chỉ CDP đọc tab nền, không bao giờ rời TikTok. Tận dụng CDP đã có, không cần credentials IMAP.
2. **IMAP đọc mail trực tiếp** — không cần Chrome/Gmail app, TikTok luôn foreground. Triệt để nhưng Gmail cần app password.
3. Chấp nhận giới hạn, xử lý thủ công.

**Chẩn đoán Chrome session hỏng — OAuth loop (máy 66, 2026-08-06):** khi CDP listing (`curl http://127.0.0.1:9223/json` sau `adb forward tcp:9223 localabstract:chrome_devtools_remote`) cho thấy **hàng chục tab `login.microsoftonline.com/...authorize`** → Chrome bị OAuth loop (không vào được inbox thật) → force-stop Chrome + mở lại Outlook 1 tab sạch trước khi retry. Luôn xem CDP listing trước khi kết luận \"CDP không đọc được OTP\" — có thể tab inbox không tồn tại hoặc bị loop.

## File quan trọng

- `references/merge-branch-to-main-workflow.md` — thứ tự merge branch→main (theo yêu cầu user) + pitfall git: add -A dính `.codex-work/` node_modules, pull --rebase fail giữa chừng → abort, patch-id phát hiện commit trùng, conflict ưu tiên bản main; **branch hygiene**: xác định nhánh chính qua origin/HEAD + rev-list counts, xóa branch master cũ (push --delete), closeout push đạt ahead/behind 0/0
- `references/avatar-smoke-and-lock-takeover.md` — chạy avatar smoke đúng (token `AVATAR-SMOKE`, env -i, -c không `--`), giành lock cross-consumer có evidence, fix AVATAR_UPLOAD_MENU_MISSING + AVATAR_PICKER_NO_MATCH
- `references/usb-popup-root-cause.md` — chuỗi root cause popup USB Samsung đầy đủ (timeline mtime, env dist-info dở, fix shell-probe)
- `references/wifi-check-after-reboot.md` — chuẩn đoán + rule check wifi trước live/sau reboot (bài học máy 74)
- `references/device-lock-protocol-and-core-health.md` — lock protocol v1 legacy không reclaim qua core (xử lý thủ công an toàn), checklist DEVICE_LOCKED, module `automation_core.outlook_health` (pattern google_health), test core bằng PYTHONPATH không editable-install
- `references/killed-batch-recovery.md` — phục hồi batch bị kill: checkpoint/lock stale/fingerprint stale/chạy lại đồng loạt + pitfall terminal timeout 600s kill launcher giữa batch (dùng background=true thay foreground)
- `references/tiktok-reg-otp-extraction-and-core-venv.md` — Tiktok_Reg: OTP extract bắt nhầm số trong email address (replay offline + hướng fix), core pin ≠ env chung → venv riêng + pitfall `flows`/PYTHONPATH, lệnh chạy runner chuẩn
- `references/tiktok-reg-recovery-20260806.md` — run recovery 2 lượt (10 máy + 6 máy): bảng signature/evidence từng STT, root cause chung (máy Gmail mất account trong AccountManager), fix OTP marker-node + Hotmail swipe + PHONE_VERIFY live probe, regression test `tests/test_gmail_otp_marker_node_fix.py`
- `references/tiktok-reg-transport-vpn-reboot-20260806.md` — uiautomator `Killed` EXIT=137 toàn farm (reboot là fix duy nhất), VPN sau reboot watcher không gán → tự `set_proxy()` từ vi_changer_runner, restore mail bị xóa nhầm từ backup + xóa Audit Pending sai, STT 30 `[04_add_account]` false-positive account-sheet, kết quả retry lần 3
- `references/tiktok-reg-mail-guard-and-farm-recovery.md` — MAIL-DIE GUARD (CẤM xóa mail sống: chỉ CAPTCHA-confirmed/DEAD/BLOCKED mới xóa; ALIVE/UNKNOWN giữ; restore mail bị xóa nhầm từ backup + xóa Audit Pending sai; test phải gọi caller), uiautomator `Killed` toàn farm → reboot + `set_proxy` sau reboot, OTP extract bắt nhầm số trong email (marker-node), venv recovery cô lập + PYTHONPATH thứ tự, PHONE_VERIFY ≠ mail die, Hotmail "Protect your account" ≠ pass/2FA sai
- `references/tiktok-reg-restore-mail-workflow.md` — quy trình khôi phục mail bị xóa nhầm (restore từ backup đúng vị trí + xóa Audit Pending sai + refresh manifest), pattern script `restore_sttXX_source.py`/`remove_audit_sttXX.py`, cách quét toàn bộ mail bị xóa nhầm từ backup hôm đó
- `docs/tiktok-ui-compatibility.md` — registry tất cả UI handler, user gọi là "Ui.md" (KHÔNG tạo file ui.md mới — chính file này); phải cập nhật mỗi lần sửa. Entry ID chuẩn: `COMPAT-<DOMAIN>-NNN` (RECENTS-001, AVATAR-004/005/006, CAPTION-001/002...)
- `reports/AUDIT_LOG.md` — audit log cho blocked/reviewed work
- `login_runner/account_reconcile.py` — reconcile orchestration
- `login_runner/account_inventory.py` — inventory + startup/popup handling
- `login_runner/live_adapter.py` — live login adapter (hỗ trợ UI mới + cũ)
- `login_runner/totp_provider.py` — TOTP challenge provider

