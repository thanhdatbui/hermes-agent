# VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED — coordinate fallback handler evidence (2026-08-09)

Máy 35/46/74 cùng dừng trước Post với error `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
("Recaptured surface did not prove a labelled bottom-centre create control").
post_submission_state=null, post_verified=false → retry an toàn, không đăng trùng.

## Live evidence (m74, serial ce061606c21e153d03)

Artifacts: `D:\CodexRuntime\tiktok-video\m74-ui-recovery-20260809T133622Z\`
(90 captures: 00_pre_atx, 01_after_atx, 02_pre_force_stop, 03/04_after_force_stop_monkey
[feed verified], 05_pre_create_tap, 06_after_create_tap — mỗi lần .png + raw UI XML +
dumpsys + manifest; actions/ 01_atx_kill.json, 02_force_stop_monkey.json,
03_coordinate_tap.json; REPORT.md).

- **wm size**: Physical 1440x2560, Override 1080x1920 → dùng override W=1080, H=1920.
- **Create-entry node**: resource `o3c`, content-desc "Quay", bounds `[432,1794][648,1920]`,
  clickable=true, nằm trong nav strip y 1794–1920 (TabHost `o4_`).
- **Tap đã verify**: `input tap 540 1857` (x=W//2, y=nav_strip_center) rc 0 → mở composer.
- **Composer markers (xác nhận thành công)**: resource-id `com.ss.android.ugc.trill:id/x7f`
  (mode row ẢNH/VĂN BẢN/AI SELF/CAMERA/MẪU/LIVE) + `tv_top_text` + "Thêm âm thanh".
- mCurrentFocus vẫn báo SplashActivity sau tap = window focus stale đã biết, KHÔNG phải fail.

## Handler invariant (đã implement, full suite 371 passed)

Trong recovery path của video-pick create-entry unconfirmed:

1. Chạy ladder cũ trước: ATX kill budget theo signature → đúng 1 force-stop/relaunch →
   soft reboot khi authorized/eligible (giữ outcome gating sẵn có).
2. **Chỉ khi ladder cạn**: screenshot evidence yêu cầu TikTok foreground + bottom nav;
   xác nhận create-entry bằng semantic candidate hiện có HOẶC coordinate evidence-backed
   (content-desc "Quay"/bounds center trong bottom 8-12% + label, hoặc generic nav create
   x=W//2, y=nav center tính từ override size).
3. **Tap đúng 1 lần**; dump UI mới; XML có composer markers (`x7f` mode row / tv_top_text /
   "Tạo/Ảnh/VĂN BẢN/Quay") → entry confirmed, tiếp tục; ngược lại FINAL_BLOCKED kèm
   artifact, KHÔNG tap lần 2 cùng tọa độ.
4. Không bao giờ tap Post/upload/delete; không chạy ở POST/verify states.

## User rule 2026-08-09 (bắt buộc)

Sau ladder cạn, **coordinate fallback BẮT BUỘC thử** (tap 1 lần, evidence screenshot trước +
raw UI XML recapture sau, scale từ wm size override, cấm action nguy hiểm Post/Delete/payment/
OTP/switch-account). Blanket "cấm tap mù" KHÔNG được chặn recovery. Đã sweep rule cũ khỏi
`docs/tiktok-ui-compatibility.md` (5 chỗ) + `automation-core/docs/ui-compatibility-contract.md`
("no blind taps" = cấm tap khi chưa xác nhận màn, không phải cấm mọi lúc) + skill §14 tầng 4.

## Pitfall: worker delegation fail nhưng code hoàn chỉnh

Luna worker implement handler fail với "(no summary — did not produce a response)" sau
50 API calls / 42 phút. NHƯNG code nó để lại hoàn chỉnh: state_machine.py +267 dòng,
test +341 dòng, full suite 371 passed, py_compile OK, EOL chuẩn (SM CRLF, test LF),
git diff --check sạch. **Bài học: khi delegation trả status=failed không summary, ĐỪNG
re-dispatch ngay — verify working tree trước (compile + pytest + diff --check). Worker có
thể đã hoàn tất toàn bộ công việc và chỉ chết ở bước trả lời cuối.**

## Pitfall: đừng claim "đã chạy đủ ladder" khi log chỉ có 1 tầng

User bắt lỗi: nói "74 đã chạy ladder" trong khi execution.log chỉ có
`[OPEN_TIKTOK] Force-stop + relaunch 1/2`, KHÔNG có ATX kill, KHÔNG có reboot.
Trước khi báo cáo ladder đã chạy: grep execution.log worker thật
(`atx|force-stop|monkey|reboot|uiautomator`) rồi mới kết luận tầng nào đã thực thi.
