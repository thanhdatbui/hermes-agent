# 16/08: Swipe-recovery rule + 3-session + canary pitfalls

## Rule user: Lỗi lạ → swipe 2 cái thử (16/08)
User rule: **gặp bất kỳ lỗi gì lạ/không qua được → swipe 2 cái thử qua → vẫn lỗi mới báo manual**.
- Implement: `_swipe_recovery_on_stuck` trong `feed_swipe_smoke.py` (trước `_maybe_dismiss_add_phone_row`), gọi từ dismiss-add-phone fallback (line ~6515 khi `not dismiss.dismissed`).
- Bounded: 2 ADB `input swipe 540 1600 540 400 300` + recapture (`capture_calibration_attempt`) + reclassify (`detected_screen_from_attempt`).
- Chạy 1 lần/session (`_swipe_recovery_used` flag), fail-closed.
- KHÔNG swipe qua sensitive: login/login-overlay/verification/captcha/security/manual_challenge/unknown.
- Nếu detected là screen dùng được (for-you/following/friends/profile/home) → SUCCESS, tiếp tục session.
- Khi debug manual-needed do screen lạ: kiểm tra log có action `swipe_recovery_on_stuck` chưa; nếu chưa → chỗ return manual khác chưa gắn hook.

## Bug pre-existing: `device_lock_paths` không import — GIẢI QUYẾT BẰNG XOÁ HẾT LOCK (16/08)
- `multi_machine_feed_session.py` line ~207 `_target_lock_aliases` gọi `device_lock_paths(...)` nhưng file KHÔNG import → `NameError: name 'device_lock_paths' is not defined` khi chạy thật (tests mock nên không bắt).
- **User quyết định (16/08): XOÁ HẾT cơ chế device lock** trong multi-machine feed — không fix import. Đã xoá khỏi `multi_machine_feed_session.py` (~270 dòng): `_PriorTargetEvidence`, `_prior_target_evidence`, `_write_deferred_locked_child_artifacts`, `_write_recovery_handoff_evidence`, `_device_lock_root`, `_target_lock_aliases`, `_target_identity_state`, `_lock_release_proof`, `_verifier_success_proof`, `_classify_prior_handoff`, constants `_LOCK_HANDOFF_SCHEMA`/`_VERIFIED_SUCCESS`, và 2 điểm skip prior-evidence trong loop launch.
- **Hệ quả:** KHÔNG còn "skipped locked machine(s)" / DEFERRED_LOCKED / `recovery_lock_handoff.json` prior-evidence skip — máy fail lần trước TỰ chạy lại mỗi lần cron. Đừng tìm/cố fix các hàm này nữa.
- Test tương ứng `test_multi_machine_feed_session.py` cũng bỏ import + test `test_recovery_handoff_evidence_records_terminal_state`.
- Quy tắc lock cuối: **lock CHỈ khi user yêu cầu → giữ vĩnh viễn; chạy success → mới mở** (xem taadaa-farm-ops-rules §3).

## `--account-row-index` = nick thứ mấy TRONG máy
- `taikhoan_run_safe.xlsx` cấu trúc: cột `May` (máy), `Device ID`, `ID` (nick). Mỗi máy nhiều nick (máy 4 = rows 20-25, nick 1 = thuuy.thy ở row 20).
- `--account-row-index N` = nick thứ N của MÁY đó (1-based), KHÔNG phải row workbook.
- Sai row-index → runner chọn nhầm nick + serial khác (log thấy serial/username lạ).

## Log `device:6539271ed7` = serial BỊ CHE
- `mask_value(serial, prefix="device")` che serial trong log, chỉ hiện 8 ký tự cuối.
- `device:...` KHÔNG = emulator/ADB reverse. Đừng hoảng — đối chiếu workbook để xác nhận serial thật.

## Canary: handoff cũ — HẾT HIỆU LỰC sau khi xoá lock
- (Cũ:) Sau lần chạy manual-needed/fail, `recovery_lock_handoff.json` để lại trong artifact → lần chạy sau `_prior_target_evidence` → `deferred-locked` → "skipped locked machine(s)".
- (Mới 16/08:) **Toàn bộ cơ chế prior-evidence đã xoá** — không còn "skipped locked machine(s)" từ handoff. Nếu vẫn thấy "skipped locked machine(s)" → là lock thật user tạo trong `~/.codex/device-locks/` (DEFAULT_LOCK_ROOT), chỉ user mở.

## 3-session manifest (đã implement + commit 460096f)
- 3 phiên/ca, 9 phiên/ngày/máy; anchors 06:00/12:30/19:00; jitter ±20' phiên 1; block 1 clamp jitter ≥0 (anchor 06:00 = window start); pair_gap grid 5 (35-60); INTER_BLOCK (90,300); max_workers 30; cap 3 phiên/ngày (`success_timestamps` ≥3 → NOT_DUE); organic follow 6%; reactive phiên 2/3 = last_feed_success_at + random(35,60).
- Manifest validator yêu cầu **3 entries/block** (session_index 1,2,3) — script build canary phải tạo 3 entries (build_block_sessions 3-tuple), không dùng script 1-entry cũ.
- `manifest.py` validator: `required_keys` phải có `jitter_minutes`; `entry_ids` len 3; `session_slots` canonical so với slots jittered (không unjittered); inter-block gap so nominal (unjittered) slots.
- `models.py` SLOT_GRID_MINUTES 15→5.

## Chạy run_tiktok.py từ terminal (môi trường)
- `unset PYTHONPATH` trước khi chạy — PYTHONPATH có thể trỏ `D:/Taadaa/Tiktok-video/scripts` → resolve sai PIL (`ImportError: cannot import name '_imaging'` từ hermes venv).
- multi-machine-feed-session cần `--account-workbook` + `--account-row-index` (thiếu → config-error).

## Máy văng ra home khi mở TikTok → check `enabled=0` (DISABLED)
Triệu chứng: `am start` TikTok → `mCurrentFocus` vẫn là launcher sau 6-10s; `ps -A | grep trill` RỖNG; logcat KHÔNG có crash/FATAL. Máy 4 (16/08) chính là case này.
- **Check đầu tiên:** `dumpsys package com.ss.android.ugc.trill | grep -iE "enabled=|stopped="` → `enabled=0` = app bị DISABLED (do hệ thống/xiaowei/vô tình disable). Mở app sẽ bị Android từ chối im lặng → văng home ngay.
- **Fix:** `adb shell pm enable com.ss.android.ugc.trill` → "new state: enabled". Nếu vẫn văng sau khi enable → sang bước logcat (dưới).
- **Debug văng home (có crash/không crash):**
  1. `logcat -c` (clear) → `am start` → sleep 8-10 → `logcat -d | grep -iE 'trill|aweme|FATAL|AndroidRuntime|am_kill|lowmemorykiller|lmkd|am_crash|has died'`
  2. `ps -A | grep -i trill` sau 5s và 10s: process chết im lặng (không crash log) = nghi OOM/LMK (kiểm tra `cat /proc/meminfo` — MemFree thấp <500MB) hoặc app disabled.
  3. Nghi OOM: **force-stop + mở lại** (`am force-stop` → `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`), KHÔNG clear cache.
- Đừng vội kết luận "lỗi code mới" — kiểm tra trạng thái app/device trước (enabled, RAM, process).

## ⛔ CẤM TUYỆT ĐỐI `pm clear` / `pm clear --cache-only` trên máy thật (hard rule — user phạt nặng 16/08)
- **`pm clear --cache-only` làm TikTok mất resource assets → kẹt splash vĩnh viễn** (`Forest_ResourceFetcherChain: memoryError: cannot find cached buffer` trong logcat). `pm clear` (full) = **xoá sạch data → mất hết nick/account đã login trên máy**.
- Memory có rule "CẤM xóa 'Dữ liệu TikTok'" — vi phạm trong session này (chạy `pm clear --cache-only` khi máy 4 kẹt splash để "debug") làm user mất dữ liệu máy 4 + phản ứng cực mạnh. **KHÔNG BAO GIỜ clear cache/data app trên máy thật**, kể cả khi nghi OOM — chỉ force-stop + relaunch, hoặc reboot máy (B3).
- Nếu lỡ clear cache rồi: force-stop + mở lại có thể KHÔNG đủ (cache không tự rebuild đủ) — tình trạng kẹt splash kéo dài; báo user, đừng tự clear tiếp data.

## `am start` direct bị từ chối → dùng `monkey` LAUNCHER
- Một số máy (vd máy 4 sau khi disable/enable): `am start -n com.ss.android.ugc.trill/.main.MainActivity` → văng launcher, NHƯNG `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` mở được app (NewUserJourneyActivity/SplashActivity).
- Nếu `am start` văng home → thử monkey trước khi kết luận app hỏng.

## ATX-primary `get_focused_activity` — fix kẹt splash ảo (16/08, commit 1a33a14)
- **Triệu chứng:** session dừng manual-needed `capture-invalid`/`unknown`, `dumpsys window` báo `SplashActivity` dai dẳng — NHƯNG screencap thật cho thấy **feed đã render đầy đủ** (video, tab Đề xuất). TikTok không chuyển activity window (splash activity giữ focus) dù UI đã vào feed → code tin dumpsys = tưởng kẹt splash.
- **Bài học:** `dumpsys window mCurrentFocus` KHÔNG đáng tin để quyết "kẹt splash" trên TikTok — activity cũ có thể giữ window trong khi UI thật đã đổi. Luôn đối chiếu screencap/UI XML trước khi kết luận.
- **Fix (observe.py):** `get_focused_activity` giờ **ATX-primary** — gọi `automation_core.ui.capture_ui_xml(..., provisioning_policy=REQUIRE_PROVISIONED)` trước, parse `package=` từ XML trả về; dumpsys làm fallback. Kết quả: package thật từ XML (vd `com.ss.android.ugc.trill` thay vì SplashActivity). Test: `PYTHONPATH='D:\Taadaa\automation-core\src' python -B -m pytest tests/test_observe.py` (3 passed) — cần PYTHONPATH do PIL env issue khi chạy consumer test.
- Canary máy 6 sau fix: hết kẹt splash ảo, lướt 19 swipe success (swipe_13-19 log OK, gem popup handle chạy).

## ATX agent không có trên mọi máy
- Feed session dùng ATX agent (port 7912) để đọc UI; nhưng **không phải máy nào cũng cài/chạy ATX** (máy 4 không có process ATX).
- Trước khi dùng `adb forward tcp:7912` + curl dump: check `adb shell ps -A | grep -i atx`. Không có → `capture_ui_xml` (ATX-primary) tự fallback, hoặc đọc ui.xml từ artifact lần chạy gần nhất.
- `uiautomator dump` trên máy không có ATX có thể trả rỗng — đừng mất thời gian, fallback sang artifact/ảnh.

## Phân loại popup TikTok: core dismiss vs consumer pass (user rule 16/08)
- **Popup cấp quyền / gợi ý add số điện thoại** (permission, add-phone) → xử lý ở **automation-core** (dismiss dạng core): `automation_core/tiktok_popup.py` (location/contacts/notification permission, add_phone_number_vi, camera_mic sheet) + `automation_core/tiktok/benign_popup.py` (`detect_add_phone_popup`, `detect_profile_add_phone_prompt`).
- **Popup CTA mua hàng** ("Mua ngay", shop CTA xuất hiện khi lướt feed) → **pass ở repo consumer** (`feed_swipe_smoke.py` GemPhoneFarmBlindPopupRule `shop_cta_close` = `//node[@text="Mua ngay"]`).
- **Tên `gemphonefarm_blind_popup` là tên CŨ gây hiểu nhầm** — nó xử lý popup TikTok (Mua ngay, Chuyển đổi tài khoản, Đóng tất cả...), KHÔNG phải popup GemPhoneFarm. User: "để im cũng đc" — không cần đổi tên.
- Khi gặp popup lạ: phân loại theo 2 nhóm trên trước khi quyết sửa core hay consumer.

## Workflow: báo bức tranh tổng khi debug lâu + vào account switcher trước khi hỏi user
- User bực khi agent debug canary quá lâu mà quên trả lời "đang ở đâu trong kế hoạch": **mỗi vài bước debug, nhắc lại ngắn gọn "đang ở bước X của kế hoạch (plan → code → test → canary → farm), canary = thử 1 phiên 1 máy, chưa phải chạy 3 ca"**.
- Khi profile_preflight báo `profile account mismatch and profile username/display name anchor is unavailable`: **vào account switcher (mở TikTok → profile → menu) đọc nick thật đang login trên máy TRƯỚC khi hỏi user** — đừng hỏi "máy đang login nick gì" khi chưa tự kiểm tra (user sẽ hỏi lại "mày đã vào account switcher kiểm tra chưa").
- ui.xml của profile_preflight_identity_guard có thể chỉ chứa battery/clock (80%, 14:16) — username chưa render, đừng kết luận từ đó; cần ảnh screencap hoặc account switcher thật.

## Phân biệt profile NGƯỜI KHÁC vs profile chính chủ (tránh kết luận sai nick)
- Profile **người khác** (mở từ tìm kiếm/gợi ý): có nút quay lại `<-` góc trái trên + nút **"Nhắn tin"** (Message) + chuông 🔔 + chia sẻ, KHÔNG có "Sửa hồ sơ" / dấu ≡ cài đặt. Tap nhầm tab/avatar có thể rơi vào đây → tưởng máy login nick lạ.
- Profile **chính chủ**: có "Sửa hồ sơ" (Edit profile) + dấu 3 gạch cài đặt `≡`, không có nút quay lại.
- Khi profile hiện nick không khớp workbook: **tra cứu nick đó trong toàn bộ `taikhoan_run_safe.xlsx`** (vd `longtuong10` = row 347, máy 58) — nick có thể "lạc máy" (login trên máy khác với máy được gán). Báo user row/máy thật thay vì tự kết luận.

## Tap chính xác nút popup: dùng ATX XML bounds, KHÔNG đoán theo vision scale
- **Pitfall:** screencap có thể trả ảnh scale khác màn hình thật (vd 720×1280 trong khi màn hình 1080×1920) → tọa độ vision ước lượng NHÂN TỈ LỆ SAI → tap trật nhiều lần (popup contacts máy 6 16/08).
- **Cách đúng:** dùng `capture_ui_xml` (ATX) parse `bounds` của node có text cụ thể, tap TRUNG TÂM bounds:
  ```python
  re.findall(r'<node[^>]*text="Không cho phép"[^>]*bounds="(\[[^\"]+\])"', xml)
  # bounds [120,1156][539,1299] → tap (329, 1227)
  ```
- Nút "Không cho phép"/"TỪ CHỐI" trong popup contacts permission: bounds lấy từ XML là tọa độ thật (đã verify tap đúng 1 phát).
- Popup contacts permission text máy 6: "Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ..." — core rule `contacts_permission_vi` marker cũ `"cho phép tiktok truy cập vào danh bạ"` KHÔNG match (thiếu "tiktok" giữa câu). Đã sửa marker thành `("cho phép truy cập vào danh bạ", "kết nối với những người bạn biết")` trong `automation_core/tiktok_popup.py` (chưa verify merge).

## Onboarding "Chọn chủ đề bạn thích" — nút Bỏ qua + đừng tự ý clear
- Máy bị reset (data mất/đăng nhập mới) → TikTok mở ra `NewUserJourneyActivity` = onboarding "Chọn chủ đề bạn thích" (chọn topics). Màn này không phải feed — classifier có thể báo lạ/add-phone.
- Nút **"Bỏ qua"** ở đáy trái (ảnh 1080×1920: ~299,1835). Tap xong → `SplashActivity` → load feed (máy chậm có thể kẹt splash 30-60s+).
- Đây là màn hình yêu cầu thao tác tay qua SCRIPT (NO-MANUAL-TAP rule) — nhưng nếu canary dừng ở đây, báo user (máy cần login lại nick đúng) thay vì tự xử lý account.

## KHÔNG tự chế `--prepare-tiktok` / không tự thêm flag khi script chuẩn đã có bước
- Script `tiktok-luot nuoi acc` ĐÃ có sẵn bước prepare/clear app qua `core_prepare_app_for_automation` (automation-core startup) trong flow chuẩn — `--prepare-tiktok` là flag riêng, không bắt buộc, và việc tự thêm flag/đổi lệnh chạy canary so với lần chạy OK trước = tự chế (user phạt).
- Chạy canary GIỐNG HỆT lệnh đã chạy OK trước đó (máy 5/6 hôm qua: không prepare). Chỉ thêm flag khi user yêu cầu hoặc plan ghi rõ.
- `prepare_app_for_automation` chỉ force-stop + close recents + monkey launch + verify focus — KHÔNG clear data/cache (đừng đổ lỗi cho nó khi data mất).

## Follow hook (subprocess `run_follow.py`) — PHẢI chạy `-m` + `cwd` follow repo
- Hook `_run_follow_hook` (multi_machine_feed_session.py) gọi follow repo qua subprocess, KHÔNG import chéo.
- **Pitfall (16/08, canary máy 6):** chạy script path trực tiếp `python D:\Taadaa\tiktok-follow\follow_runner\run_follow.py` → `ModuleNotFoundError: No module named 'follow_runner'` — vì follow repo dùng import kiểu package (`from follow_runner.core.adapter import ...`), cần package root trong sys.path.
- **Fix đúng:** `python -m follow_runner.run_follow --machine N --config <path> --account-row-index R` với `cwd=D:\Taadaa\tiktok-follow` (subprocess `cwd=` param). Cả 2 điều kiện bắt buộc: cwd = repo follow + `-m` module (script path vẫn fail dù đúng cwd).
- `follow_result.json` ghi vào child artifact root dù fail (exit 1 → `status: failed`, `follow_failed: true`) — **fail follow KHÔNG dừng feed session** (đúng thiết kế). Canary success nhưng follow_result failed ≠ phiên hỏng; check import error trước.
- run_follow.py thật có thể chạy >180s (follow thật trên máy) — timeout hook mặc định 900s; đừng kết luận crash khi `python -m` chạy lâu.
- State 16/08: fix cwd + `-m` đã apply (commit 0fafc57) + **canary máy 6 re-run xác nhận**: hook chạy đúng (follow_result.json ghi đầy đủ, không còn ModuleNotFoundError), fail hợp lý `MANUAL_REVIEW: exact profile identity không khớp sau tap` khi máy login nick khác workbook → follow từ chối (đúng an toàn, không tự follow sai nick).

## Account switcher sheet → tự chọn nick row đúng (user correction 17/08)
- **User rule**: "3 nick kệ cha nó, mở lên tìm đúng nick đúng row thì chọn" — khi account switcher mở, flow PHẢI tự chọn nick đúng row, KHÔNG báo manual.
- Flow `feed_swipe_smoke.py` ĐÃ có cơ chế tự chọn: `_find_account_switch_option(xml, expected)` → `_tap_ui_element(action="tap_expected_account")` → `verify_selected_account`. Bị chặn TRƯỚC bởi classifier nên không tới được.
- **Bug classifier (máy 3, 17/08)**: `core/classifier.py::_is_account_switcher_sheet` đòi element `selected="true"` phải có `class` chứa `android.widget.button` — TikTok render nick active dạng **TextView** (`selected="true"`, class TextView) → `has_selected_account=False` → switcher không được nhận → rơi bucket khác → manual-needed.
- **Fix**: bỏ điều kiện class trong `_is_account_switcher_sheet` (consumer classifier, không đụng automation_core). Verify: `classify_tiktok_screen(ui.xml thật)` → `manual-needed:account-switcher` + `_is_legitimate_profile_account_switcher_xml(xml, expected)` = True.
- **Triệu chứng kèm**: sau tap anchor mở switcher, `verify_tiktok_focus` → `TikTok focus lost` (`detected_screen: com.android.systemui`) — do flow loay hoay khi switcher không được nhận. Fix classifier là đủ, không phải sửa focus logic.
- Muốn đọc nick đang active trong switcher từ XML: grep node có `selected="true"` gần text nick (row active có tick đỏ).
- Ví dụ máy 3: `taikhoan_run_safe.xlsx` row (máy 3): row1=trangtran168432, row2=ninhy05100, row3=lequynh2043; switcher đang active ninhy05100 (row 2) → máy login sai nick hoặc flow cần tự chuyển về row 1.

## TikTok bị `enabled=0` hàng loạt trên farm
- Nhiều máy (4, 5, 6) cùng lúc `enabled=0` — pattern farm, không phải lỗi code (code không có `pm disable`). Khả năng: Samsung auto-disable app ít dùng / xiaowei / trạng thái sẵn có.
- Check + `pm enable` trước khi kết luận; sau enable một số máy vẫn kẹt splash → reboot (B3) là cách đã chạy OK hôm qua.

