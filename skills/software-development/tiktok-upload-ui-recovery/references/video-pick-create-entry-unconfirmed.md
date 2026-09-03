# VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED — signature, ladder, evidence (2026-08-09)

## Signature
- Error code: `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`
- Message: "Recaptured surface did not prove a labelled bottom-centre create control"
- Xảy ra ở state VIDEO_PICK, TRƯỚC Post. `post_submission_state=null`, `post_verified=false` → retry an toàn, không rủi ro đăng trùng.
- Dính máy 35 / 46 (video 9) / 74 (video 7) — tất cả sau khi media push thành công (fingerprint `reserved`). File đã nằm trên máy nhưng chưa được chọn/post.

## Root cause (bằng chứng ladder live m74)
- Worker cần thấy create-entry có nhãn ở bottom-centre để mở picker; recapture sau bounded create-entry recovery không qua nổi gate semantic cũ → fail-closed đúng thiết kế nhưng máy kẹt.
- `mCurrentFocus` báo `SplashActivity` trong khi surface thật (feed/composer) đã render — window focus stale là false-negative ĐÃ BIẾT; dùng marker raw UI dump, KHÔNG kết luận từ dumpsys focus.

## Ladder đầy đủ ĐÃ chạy thành công (m74, serial ce061606c21e153d03)
Artifacts: `D:\CodexRuntime\tiktok-video\m74-ui-recovery-20260809T133622Z\` — captures/ 00..06 (mỗi lần .png + raw UI XML + dumpsys + manifest), actions/ 01_atx_kill.json 02_force_stop_monkey.json 03_coordinate_tap.json, REPORT.md.

1. ATX/uiautomator kill 1 lần → dump đọc được nhưng chưa có bằng chứng feed.
2. Đúng 1 cặp force-stop + `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` → feed VERIFIED: dump có tabs `Bạn bè`/`Đã follow`/`Đề xuất` (selected) + bottom nav `Trang chủ/Cửa hàng/Quay/Hộp thư/Hồ sơ`.
3. Soft reboot SKIP (feed OK sau tầng 2 — ladder dừng khi UI hồi phục, không reboot thừa).
4. Coordinate fallback (được user cho phép, đúng 1 lần):
   - `wm size`: Physical 1440x2560, **Override 1080x1920** → scale theo OVERRIDE.
   - Create-entry node: resource `o3c`, content-desc "Quay", bounds `[432,1794][648,1920]`, clickable=true, nav strip y 1794–1920.
   - Tap `input tap 540 1857` (x = override_w//2, y = nav strip center) rc=0 → mở composer.
   - Composer proof markers: resource-id `com.ss.android.ugc.trill:id/x7f` (mode row ẢNH/VĂN BẢN/AI SELF/CAMERA/MẪU/LIVE) + `tv_top_text` + "Thêm âm thanh". DỪNG ở đây, không tap tiếp, không Post.

## Handler invariant (đang implement 2026-08-09)
1. Chạy ladder hiện hành trước (ATX budget per signature → 1 force-stop/relaunch → soft reboot khi eligible).
2. CHỈ sau khi ladder cạn: coordinate fallback được phép — screenshot evidence + raw XML recapture, scale theo `wm size` override, tap ĐÚNG 1 lần.
3. XML sau tap phải thấy composer markers (x7f mode row / camera surface) → coi như confirmed, continue; không thấy → FINAL_BLOCKED, KHÔNG tap lần 2.
4. Cấm tap Post/Upload/Delete; cấm ở POST/verify states.

## Ops lessons
- Retry-safety gate: `post_submission_state=null` + `post_verified=false` = chưa gửi gì → retry an toàn. Luôn đọc lại report.json trước khi retry (§5/§7).
- Vision 401 → raw UI dump + screenshot là bằng chứng CHÍNH; đừng chặn ladder chờ vision.
- Fingerprint giữ `reserved` khi fail → run sau re-select đúng video đó (không đăng trùng vì chưa submit gì).
- Khi user chốt "fix máy này": KHÔNG dừng MANUAL_REVIEW vì rule "cấm tap mù" — rule đó chỉ gate tap TRƯỚC khi ladder cạn; sau ladder cạn coordinate fallback là BẮT BUỘC thử.
