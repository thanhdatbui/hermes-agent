# VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED — recovery & fix (2026-08-09)

## Symptom
Worker dừng trước Post tại `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` ("Recaptured surface did not prove a labelled bottom-centre create control"). Máy 35/39/46/74 cùng dính; batch 24 máy ít video fail 24/24. `post_submission_state=null`, `post_verified=false` → retry an toàn (chưa có bài đăng).

## Root causes (evidence m74, run `..._20260809_220330/execution.log`)
1. **Sai surface**: tại VIDEO_PICK máy đang ở trang **Hồ sơ** chứ không phải Feed (`Root surface confirmed with indicator: 'hồ sơ'`) — sau ACCOUNT_READY máy đứng ở profile. Profile không có nút create giữa navbar → visual gate reject (`dark=0.968`) → mọi semantic/resource selector (`view_bg2`, `cwr`, `upload_hot_area`, `myb`, `plus_icon`, text `+`/`Quay`...) miss.
2. **Coordinate fallback không bao giờ chạy (bug code)**: `_recover_video_pick_create_entry` chỉ gọi coordinate khi hàm được invoke **lần 2** (guard `video_pick_recovery_attempted`), nhưng call-site gọi recovery 1 lần rồi `return False` → tầng coordinate không bao giờ reachable.
   **Bài học**: khi thêm ladder→coordinate fallback, tầng coordinate phải chạy **trong cùng lần invoke** sau khi ladder cạn — đừng gate bằng "lần gọi thứ 2" vì call-site không gọi lần 2.

## Evidence create-entry đã verify live (m74, recovery tay 4 tầng)
- `wm size`: Physical 1440x2560, **Override 1080x1920** → dùng override.
- Node create: resource `o3c`, content-desc "Quay", bounds `[432,1794][648,1920]`, clickable, nav strip y 1794-1920.
- Tap `input tap 540 1857` (rc 0) → composer mở với markers `com.ss.android.ugc.trill:id/x7f` (hàng mode ẢNH/VĂN BẢN/AI SELF/CAMERA/MẪU/LIVE) + `tv_top_text` + "Thêm âm thanh".
- Artifacts: `D:\CodexRuntime\tiktok-video\m74-ui-recovery-20260809T133622Z\` (90 captures: 00_pre_atx … 06_after_create_tap, mỗi lần .png + raw UI XML + dumpsys + manifest; actions/ 01_atx_kill.json, 02_force_stop_monkey.json, 03_coordinate_tap.json; REPORT.md).
- Screenshot pixel analysis trong run fail: `video-pick-feed.png` / `before` / `recaptured` đều dark≈0.43-0.47 — ảnh tối nhưng không phải màn đen hoàn toàn; kết luận dựa vào UI dump marker, không tin visual một mình.

## Fix shape (đã dispatch)
- Trước khi tìm create-entry: đưa máy về **Feed** (root surface indicator phải là feed/home, không phải `hồ sơ`).
- Sau ladder cạn (ATX kill → một force-stop/relaunch → một soft reboot khi eligible), coordinate fallback **chạy ngay trong cùng lần invoke**: screenshot evidence trước, đúng 1 tap scale từ wm override, raw UI dump recapture sau; composer markers (`x7f`/`tv_top_text`) → confirmed; ngược lại FINAL_BLOCKED, không tap lần 2 cùng tọa độ, không bao giờ Post/Delete/payment/OTP/switch-account.
- Regression tests: fake adapter dump trả XML create button (bounds + content-desc) + dump sau tap trả composer markers; assert đúng 1 tap, tọa độ scale từ size; fail-closed khi recapture không ra composer. EOL: state_machine.py CRLF, test LF.

## Focused-test fixture contract and debugging pitfall

The Feed-first navigation path may call `adapter.tap(...)` directly for a bounded content-desc home node when `_tap_if_found` cannot match `content-desc`. Recovery test doubles must therefore provide `tap`, even if the test primarily asserts the create coordinate. A fixture that omits this method is a contract failure in the test double, not evidence that the production recovery should skip navigation.

When the same focused test fails repeatedly with the same traceback, stop rerunning unchanged. Read the failing line, compare the fake adapter with the production call contract, make one minimal fixture/code correction, then rerun the focused test before the full suite. Keep unrelated pre-existing worktree changes intact and do not reset them.

## Batch launcher gotcha (lần launch đầu fail exit 1, KHÔNG phải lỗi máy)
`run_tiktok_upload_batch.ps1 -AssignmentManifest <file>` **THROW** nếu thiếu `-WorkerId`:
```
AssignmentManifest và WorkerId phải được cung cấp đồng thời.
```
- `-WorkerId` phải bằng `owner_id` trong manifest (`AssignmentManifest.assert_owner(worker_id)`).
- Đọc log batch (`lowcount-*.log`) trước khi kết luận "máy lỗi" — exit 1 có thể là lỗi tham số launcher.

## Quy trình dọn lock trước batch (đã verify 24 máy)
- Quét `machine_*.lock.json` + `serial_*.lock.json` cho tập máy; verify pid chết bằng wmic (đừng tin `tasklist`); archive (không xóa) kèm backup + evidence JSON.
- Lock feed `tiktok-luot nuoi acc` với pid chết (vd 20888/60284/68180/31652/48364) cũng là stale → archive được, không đụng lock pid sống.
- Manifest format: `{"schema_version":1, "assignment_id":..., "owner_id":..., "reviewed_at":..., "resources":["machine:N",...]}`.
