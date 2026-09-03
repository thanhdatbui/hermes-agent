## 14b. Live recovery after stale handoff + transient UI-dump stall (verified 2026-08-09)

When a single machine is explicitly authorized for live recovery and its upload worker is in `handoff`, use this bounded sequence before any retry:

1. Bind the target from both lock aliases (`machine_<N>.lock.json` and `serial_<serial>.lock.json`). Verify the recorded PID is genuinely absent with a command-line-aware process check and verify that no replacement `tiktok_workflow` worker for the same machine is running. Do not reclaim an active watcher/scheduler lock. If the stale lock is owned by this consumer, archive both aliases plus redacted evidence before moving them.
2. Preserve a pre-action screenshot, UI-dump stdout/stderr, and a timestamped probe artifact **before every state-changing recovery step**. A screenshot is diagnostic evidence, not proof that the worker will pass its own startup path.
3. Apply the per-signature ladder exactly once per tier: ATX/uiautomator cleanup -> one force-stop + `monkey` launch -> one authorized/eligible soft reboot -> one post-boot `monkey` launch if needed. After each tier, recapture and verify the feed; stop immediately when feed evidence is valid.
4. A soft reboot is eligible only after the target is unowned, the device is connected, and post-boot verification can require `sys.boot_completed=1`, a changed readiness `boot_id`, `proxy_ready`, `tun0` with an address, and a live ViChanger PID. The Samsung `sec_debug/recovery_cause` warning alone is not a failed reboot; the post-boot gates decide.
5. Run the direct single-machine worker only after those gates pass, in its own bounded process/log. Never bundle multiple direct workers in one shell. The worker's final report, not the process exit alone, is the success verifier.
6. If the worker visually confirms the feed but later fails at `DISMISS_POPUPS` with `UI_DUMP_FAILED`/`uiautomator_idle_state_error`, and `post_submission_state=null` plus `post_verified=false`, classify it as **no upload occurred**. Do not infer success from a later read-only dump that happens to recover, and do not create a third retry for the same signature. Keep the handoff lock and artifacts for escalation.

> Reusable checklist and evidence shape: `references/live-recovery-handoff-retry.md`.

## 14c. m74 create-entry coordinate evidence — ladder đầy đủ 4 tầng (verify 2026-08-09)

> Chi tiết + evidence paths: `references/m74-create-entry-coordinate-ladder.md`.

Chạy ladder 4 tầng cho m74 (serial ce061606c21e153d03, TikTok 46.2.3 — máy trước đó fail
`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`) theo user request, kèm coordinate fallback được ủy quyền:

- **Lock**: 2 alias `machine_74` + `serial_ce061606c21e153d03` đều `tiktok-upload/handoff`
  owner_active=false, pid 46708 dead (wmic "No Instance(s) Available" + tasklist no match) → archive cả 2
  + evidence (`backup_m74_recovery_20260809T135448Z` + `evidence_m74_recovery_20260809T1355*.json`).
- **Tầng 1 (ATX kill)**: `pkill -9 -f uiautomator` rc=1 (không có process) là BÌNH THƯỜNG, không phải
  fail; `uiautomator quit` in usage text nhưng rc 0 — vô hại. Dump đọc được nhưng chưa có bằng chứng
  feed → đi tiếp.
- **Tầng 2 (force-stop + monkey, 1 cặp)**: feed THẬT verified (dump 69,983 B: tabs Bạn bè/Đã follow/
  Đề xuất selected + bottom nav Trang chủ `o3g`/Cửa hàng `ejz`/**Quay `o3c`**/Hộp thư `o3h`/Hồ sơ `o3i`).
  mCurrentFocus vẫn `SplashActivity` = stale window focus (đúng §14), không phải fail.
- **Tầng 3 (soft reboot)**: BỎ QUA vì feed đã hợp lệ sau tầng 2 — skip-by-evidence (KHÔNG phải
  "không được phép"). **Điều này KHÔNG kết thúc ladder**: coordinate fallback vẫn chạy vì mục tiêu
  riêng của nó (chứng minh create-entry) chưa đạt — feed valid ≠ create-entry proven.
- **Tầng 4 (coordinate fallback, ủy quyền, ĐÚNG 1 tap)**: `wm size` = Physical 1440x2560 /
  Override 1080x1920 → **scale theo OVERRIDE**. Node basis: `o3c` content-desc "Quay" bounds
  `[432,1794][648,1920]` clickable=true → `input tap 540 1857` (x=1080//2, y=nav strip 1794..1920 center)
  RC 0 → **create-entry PROVEN**: mở camera composer — mode tabs `x7f` texts "ẢNH"(selected)/"VĂN BẢN"/
  "AI SELF"/"CAMERA"(selected)/"MẪU"/"LIVE", durations 10 phút/60s/15s, tools Lật/Flash/Hẹn giờ/Bố cục/
  Tỷ lệ/Làm đẹp, "Thêm âm thanh" (`tv_top_text`), "Menu thả xuống" (`yg4`), thumbnail thư viện.
  STOP trạng thái an toàn — không tap thêm, không post.
- **Evidence-preservation recipe (dùng lại được cho mọi ladder run)**: dir timestamped
  `m74-ui-recovery-<ts>/` với `captures/` (mỗi action: .png + raw UI XML + dumpsys + manifest JSON
  utc/rc, **TRƯỚC và SAU mỗi action**) + `actions/` (log từng lệnh + rc) + `REPORT.md`. Dump XML luôn
  dùng path remote MỚI (`rm -f` trước khi dump) để tránh đọc XML cũ/stale.
- Khi `vision_analyze` primary trả 401 (đã xảy ra 2026-08-09) → fallback vision phụ trợ + dump UI làm
  bằng chứng máy đọc được chính; ghi limitation vào REPORT.

## Mandatory live feed-CTA recovery and coordinate fallback (2026-08-09)

Khi operator đã cho phép recovery và exact TikTok `Mua ngay` được xác nhận:

1. Không dừng ở patch/unit test/script. Phải chạy bounded live handler trên đúng target trong cùng task, rồi đọc artifact + recapture + per-machine ledger/lock handoff.
2. CTA semantics là **`Mua ngay` → một bounded swipe trước**; node `Đóng` không phải precondition. Sau swipe phải recapture. Nếu exact `Mua ngay` còn, mới dùng `close_element` động từ XML hiện tại và tap đúng node `Đóng`; không tap `Mua ngay`, không hardcode resource-id obfuscated (`hvm`, `hwh`, `hwn`, ...).
3. Nếu XML capture hỏng, không suy ra popup từ exit code. Chạy ladder theo failure signature, mỗi tầng tối đa một lần: ATX/uiautomator cleanup → một force-stop + monkey relaunch TikTok → một soft reboot khi authorized/eligible. Sau mỗi tầng phải recapture/check feed; lỗi signature mới thì tính ladder lại từ đầu.
4. Sau ladder cạn, **feed swipe** được phép dùng coordinate fallback vì là hành động bounded, rủi ro thấp hơn tap CTA, nhưng chỉ khi screenshot classifier xác nhận TikTok feed/For You, package/focus đúng và không có login/OTP/captcha/payment/Post/system-dialog marker. Screenshot splash/loading/launcher/không phân loại được ⇒ không swipe.
5. Coordinate fallback chỉ chạy một lần, dùng display-size/portrait evidence, ghi command + pre/post screenshot/artifact, recapture bắt buộc và fail-closed nếu không xác minh feed. Không dùng fallback cho tap nguy hiểm hoặc để che lỗi handler.
6. Live proof phải ghi per-machine: `SUCCESS` chỉ khi handler/recapture/ledger/lock handoff chứng minh; `FINAL_BLOCKED`/`MANUAL_REVIEW` phải nêu failure signature và artifact. Batch exit code 0/2 không thay thế per-machine proof.
7. Báo cáo cho user bằng tiếng Việt ngắn gọn; nếu runner in tiếng Anh thì dịch ngay các dòng status, không đẩy nguyên block log tiếng Anh.

Chi tiết evidence shape và regression recipe: `references/live-feed-cta-recovery.md`.

