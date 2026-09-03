---
name: tiktok-feed-session
description: Chạy, test, debug và vận hành an toàn TikTok feed-session-smoke và multi-machine-feed-session trong repo tiktok-luot nuoi acc.
---

# TikTok Feed Session

## 🛑 BẮT BUỘC: QUY TRÌNH RECOVERY & XỬ LÝ ALERT [MÁY N] (User chốt 2026-09-02)

1. **CẤM CHỮA CHÁY TẠM THỜI QUA ADB:**
   - CẤM xem việc gõ lệnh `adb shell input` (vuốt màn hình, bấm nút) hay sửa `settings` bằng tay là "xong việc".
   - Mọi thao tác xử lý lỗi BẮT BUỘC phải dẫn đến **sửa code trong script (`python_runner` / `automation-core`)** để toàn bộ 80-160 máy tự động vượt qua khi chạy thật.
2. **LỆNH TRÍCH XUẤT HIỆN TRƯỜNG DUY NHẤT (CẤM GREP / CẤM QUÉT ĐĨA):**
   - Khi nhận alert `[MÁY N]`, chạy: `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - CẤM TUYỆT ĐỐI dùng `os.walk`, `glob(recursive=True)`, `find`, `grep -rn` quét diện rộng codebase hay ổ đĩa để tìm chuỗi lỗi / file log.
3. **CHU TRÌNH 5 BƯỚC RECOVERY CHUẨN:**
   - **B1 (Inspect):** `python D:/Taadaa/tools/inspect_machine.py <N>` để nắm màn hình kẹt, log lỗi, step dừng.
   - **B2 (Root Cause):** Mở đúng file flow phụ trách (`feed_swipe_smoke.py`, `device_prepare.py`, `benign_popup.py`) để xem vì sao script chưa tự phục hồi được.
   - **B3 (Patch Script):** Viết logic auto-recovery (tự phát hiện + tự vượt qua + relaunch/dismiss) vào script + viết focused test (<30s).
   - **B4 (Canary Test):** Chạy canary thực tế kiểm chứng script mới tự giải cứu được máy kẹt.
   - **B5 (Closeout):** Model Review (APPROVED) -> Commit -> Push master.

References:
- `references/before-swipe-launcher-focus-recovery.md` — Before-Swipe Launcher Focus Loss Recovery (Layer 1 in `_capture_before_swipe_with_startup_retry`, Layer 2 in `_feed_session_flow`).
- `references/contacts-settings-permission-registry-dismiss-20260902.md` — In-App Contacts Settings Permission Prompt Registry Dismissal (Case 75, M52).
- `references/anti-disk-scan-machine-inspection.md` — Anti-Disk-Scan Fast Inspection Tool (`inspect_machine.py`) & Screen Lock Fix.
- `references/samsung-screen-lock-timeout-and-direct-log-triage-20260902.md` — Samsung Screen Lock Timeout & Direct Log Triage (Case 72, M10).
- `references/switcher-anchor-pke-header-allowlist-20260902.md` — Header `:id/pke` & display name (Case 70, M61).
- `references/video-playback-options-sheet-and-swipe-duration.md` — Playback Options Sheet & Swipe Duration (Case 66).
- `references/launcher-focus-loss-recovery-triage.md` — Focus lost triage.
- `references/samsung-keyboard-dumpsys-and-launcher-recovery-triage.md` — Samsung Keypad dumpsys & launcher triage (Case 54).
- `references/status-bar-notification-and-sensitive-keyword-scoping.md` — Notification false-positive & keyword scoping (Case 55).
- `references/email-subscription-popup-verify-profile-20260902.md` — Email subscription popup at verify_profile causing navigation-failed (Case UI-FEED-EMAIL-01).
- `references/machine-diagnostic-direct-artifact-access-20260902.md` — **HARD RULE**: Cấm grep đệ quy, chỉ đọc artifact máy trực tiếp (shared with taadaa-farm-ops-rules).
- `references/swipe-up-tutorial-overlay-and-navigation-interception-triage.md` — In-feed swipe up tutorial overlay, pre-navigation clearing & profile drift recovery (Case 56).
- `references/watchdog-session-window-and-partial-cohort-reporting.md` — Telegram & proxy.
- `references/watchdog-session-multi-run-merge-and-boundary-gate.md` — Quy tắc merge multi-run, bảo toàn follow_failed/video upload và chặn chốt non khi runner đang chạy (Case 51).
- `references/daily-cooldown-flock-contract.md` — .flock Check-and-Reserve UUID.
- `references/feed-runner-lease-and-shift-isolation.md` — Feed live lease & Shift Isolation.
- `references/destructive-actions-denylist.md` — Cấm kill-server / pm clear.
- `references/fast-fail-closed-proxy-probe-20260828.md` — Fast TCP probe proxy.
- `references/profile-verification-screencap-retry-and-inbox-detection-20260827.md` — retry screencap 3 lần + wake screen và nhận diện chuẩn tab Inbox bằng selected="true" attributes tại bước đối soát profile.
- `references/watchdog-session-report-format-and-follow-hook-integration-20260827.md` — format báo cáo phiên chuẩn 27/08 + tích hợp kết quả Follow Hook vào báo cáo phiên.
- `references/upload-concurrency-and-batch-watchdog-budget-20260827.md` — upload concurrency = 20 worker + dynamic batch watchdog budget theo số lượng đợt xếp hàng (upload waves).
- `references/hard-outer-watchdog-and-upload-queue-timeout-pitfalls.md` — pitfall batch global deadline & nghẽn hàng đợi upload hook gây mass 75.0m timeout.
- `references/cron-cohort-respawn-and-log-reading-20260827.md` — Cron cohort respawn & log reading.
- `references/profile-verification-screencap-retry-and-inbox-guard-20260827.md` — Screencap retry & inbox guard.
- `references/location-dialog-cancel-handler-and-swipe-recovery-guard-20260827.md` — Location popup cancel handler & swipe recovery guard.
- `references/session-3-upload-hook-concurrency-and-target-binding-20260827.md` — Session 3 upload hook concurrency & target binding.
- `references/edit-name-subpage-auto-fill-registry-integration-20260827.md` — Edit name subpage auto-fill in benign popup registry.
- `references/account-switcher-edit-name-subpage-recovery-20260826.md` — Account switcher edit-name subpage recovery.
- `references/dynamic-2layer-upload-preflight.md` — Dynamic 2-layer upload preflight.
- `references/swipe-up-tutorial-gesture-and-profile-renav-triage.md` — Swipe-up tutorial overlay recovery (Case 56).
- `references/feed-workbook-vs-upload-workbook-rules.md` — phân biệt rõ Workbook Nuôi Feed (`taikhoan_run_safe.xlsx`) ↔ Workbook Đăng Video (`TikN.xlsx`), mở rộng hook upload cho Row 3 (`tik3.xlsx`), và quy tắc cấm nhầm lẫn giữa 2 loại dữ liệu (2026-08-25).
- `references/shift2-feed-upload-audit-20260825.md` — kết quả đối soát Ca 2 (Chiều) ngày 2026-08-25: chạy Row 3 (tik3.xlsx), hook upload tự động skip an toàn (upload-disabled-outside-row-1-2), và phân loại 27 máy không chạy (trống nick / offline / ViChanger VPN).
- `references/strict-post-verification-and-profile-grid-evidence.md` — Hard Gate bắt buộc kiểm tra report.json và Profile Grid thật trước khi xác nhận đăng video thành công; cấm sửa tay workbook và cấm báo cáo suy diễn (2026-08-25).
- `references/tiktok-location-permission-popup-dismiss.md` — xử lý popup yêu cầu quyền vị trí ('Xem nội dung phù hợp và địa điểm lân cận'): quy tắc bấm nút Hủy để đóng ngay lập tức, không xem là manual-needed làm dừng phiên (2026-08-25).
- `references/tiktok-rewards-age-verification-popup-handling.md` — chẩn đoán & xử lý modal chặn độ tuổi 18+ khi chạm trúng WebView sự kiện 'Phần thưởng TikTok' trên Feed; quy tắc dismiss an toàn bằng Hủy/BACK để quay về feed (2026-08-25).
- `references/end-of-shift-upload-and-buffer-time-rules.md` — đánh giá đăng video đồng loạt cuối phiên 3, quy tắc kiểm soát tải stagger 16 máy & buffer time tối thiểu 30-45 phút giữa các ca chống xung đột device lock / lệch nick (2026-08-25).
- `references/feed-upload-transition-atx-ram-recovery.md` — chẩn đoán & xử lý timeout 900s hook upload video cuối phiên 3 do cạn RAM làm chết ngầm ATX sau phiên lướt feed dài; quy trình force-stop + restart ATX trước khi upload (2026-08-25).
- `references/systemui-navigation-focus-loss-diagnosis.md` — chẩn đoán & xử lý lỗi profile verification navigation-failed do SystemUI chiếm focus sau khi tap điều hướng.
- `references/fast-swipe-sponsored-gate-test-fix.md` — fast-swipe sponsored gate production contract + ordered-event-capture pattern cho regression test fail do stub quá rộng (2026-08-25).
- `references/alert-claim-dedup-contract.md` — alert-claim at-most-once contract: atomic pre-send in-flight claim (tránh duplicate qua TTL/relaunch); session-key dùng scheduler identity ổn định chống traversal; 2 tầng ATX recovery (Tier 1 reset nội bộ / Tier 2 terminal fail-closed); anti-mock guard & outer-flow fail-closed test pattern cho `_feed_session_flow` (2026-08-25).
- `references/verify-profile-popup-dismiss-recovery.md` — xử lý popup 'Follow bạn bè của bạn' (contact_follow_suggestion): quy tắc bấm nút Follow 1–2 nick trước rồi mới đóng X, và áp dụng ở mọi giai đoạn (feed swipe, preflight, verify_profile) (2026-08-25).
- `references/follow-friends-popup-handling-20260825.md` — chi tiết cấu trúc popup 'Follow bạn bè của bạn' (nút chữ 'Follow', không phải 'Follow lại'), 3 lớp khóa an toàn không gian chống bấm nhầm nút Follow ngoài màn hình chính (2026-08-25).
- `references/follow-friends-popup-handling-rules-20260825.md` — chi tiết quy tắc popup 'Follow bạn bè của bạn': phân biệt nút 'Follow' (không phải 'Follow lại'), cơ chế 3 lớp khóa chống click nhầm Follow ngoài feed/profile, và xử lý toàn diện ở mọi giai đoạn (2026-08-25).

## Lessons from the 2026-08-24 closeout and cron incidents

- **Answer the operator's direct question first.** If asked which session is running, whether upload follows the final row, or why a batch failed, lead with the verified `Có/Không`, session number, or root cause. Do not bury the answer under history or implementation detail.
- **Never claim a farm fix is complete without fresh proof.** The operator expects Vietnamese status updates to be short and direct, but completion requires an exact diff, focused tests, syntax/diff verification, and a clear blocker if any gate is unavailable. If a worker is still running, report `chưa xong` rather than implying completion.
- **ATX/UI recovery must preserve foreground.** Do not use `monkey -p com.github.uiautomator`, shell `uiautomator dump`, or any recovery that launches the UiAutomator app/activity. The safe probe is the ATX agent's internal `POST /uiautomator`, followed by PID-scoped ATX JSON-RPC capture and fresh foreground verification. Keep this distinct from the backend stub: ATX may manage the stub without opening it as the foreground app.
- **Ordering invariant for fast-swipe/deep-inspect.** After a fast swipe reports a non-TikTok package, set a per-video `fast_swipe_focus_lost` guard and short-circuit `_sponsored_present` before any XML capture; let the existing recovery/terminal path decide the outcome first. Do not add a broad `not fast_swipe_enabled` guard: normal-focus deep-inspect must retain sponsored detection. Regression tests must assert both (a) focus-lost does not call sponsored capture and (b) normal-focus behavior remains enabled; terminal `ATX_SESSION_UNAVAILABLE` must propagate fail-closed.
- **Session reports must be emitted once per completed logical session, not per dispatch/sub-run.** A cron poller may observe multiple row runs or worker batches for one logical session; group by the canonical day/ca/session identity and persist an atomic sent/claim marker. Never use a raw `row-HHMMSS` run directory as the notification identity without checking whether it is a retry/relaunch.
- **Farm Alerts and session-summary notifications are separate routes.** A summary notification is not evidence that per-machine Farm Alert delivery happened. For each failed machine, preserve the actual failure reason and route it to the configured Farm Alerts producer; do not silently classify preflight/config failures as UI failures.
- **Treat `FEED_SESSION_MAX_SWIPES` as a hard invariant.** It must remain `<= SESSION_MAX_SWIPES_CAP` (currently 15). Before every live dispatch and after any concurrent commit/rebase, verify the loaded source constant and the runner command/config; add a focused regression test so a timeout or unrelated merge cannot revert it to 16. A passing wrapper is not enough if the live artifact still says `requires 1 <= --max-swipes <= 15`.
- **When a whole batch fails, aggregate exact `stop_reason` values from per-machine `summary.txt`/`log.jsonl` before naming a root cause.** Distinguish `config-error`, `blocked-vichanger-vpn`, lock decisions, timeout, focus loss, and unknown TikTok state. Do not call it an account failure or a UI failure from the batch headline alone.
- **Upload hook verification is independent.** “Feed session completed” does not prove upload ran; require an `upload-hook` start/end event plus upload result/post-verification evidence. If the hook is non-interactive, test it through the same non-TTY entrypoint used by the live runner.


## Khi dùng
Dùng khi cần chạy, kiểm thử, debug hoặc rà soát các flow `feed-session-smoke` và `multi-machine-feed-session`, đặc biệt các vấn đề về popup, Captcha/verification, feed swipe, like/follow, account preflight, recovery và device lock.

## Public TikTok URL collection qua app điện thoại
Dùng khi profile route web/yt-dlp bị CAPTCHA, 403 hoặc trả `entries=[]` và operator hỏi cách khác để cào hàng loạt. Luôn tách hai bài toán: **discovery/cào URL** và **download/tải MP4**. Direct URL downloader có thể còn hoạt động dù profile discovery hỏng; không dùng bằng chứng direct-download để kết luận profile collector đã chạy.

### Hiện trạng phải kiểm tra trước khi nói “đã có tool”
- `D:\\Taadaa\\tiktok-luot nuoi acc\\python_runner\\flows\\feed_swipe_smoke.py` hiện có feed detection, swipe, like/follow và lưu XML/screenshot/artifact; không mặc định có bước copy-link, đọc clipboard, `video_id` hoặc `share_url`.
- `detect_and_dismiss_share_sheet()` trong `benign_popup_registry.py` chỉ nhận diện Share Sheet rồi đóng bằng close/back; marker `Sao chép Liên kết`/`Copy link` không phải bằng chứng link đã được sao chép.
- Chỉ gọi là **phone collector** sau khi có code path thực sự: mở Share → bấm đúng `Sao chép Liên kết` → đọc clipboard → validate URL `/video/<id>` → dedup → ghi manifest. Không suy diễn từ việc feed swipe thành công.

### Hai route và trade-off
1. **Feed collector:** lướt feed, copy link mỗi video. Dễ tránh profile web block nhưng video đến từ nhiều kênh; không được dùng để ghép folder yêu cầu 30 video cùng source/channel.
2. **Profile collector:** mở profile trong app, cuộn grid, mở từng video, copy link, back về profile. Giữ được source/channel nhưng chậm, phụ thuộc selector/UI version và có thể gặp login/verification/CAPTCHA.

### Kiến trúc tích hợp đúng
`phone collector → public URL JSONL/manifest → existing direct resolver → MP4 validation/ffprobe → source ledger/state DB`.
Collector không được ghi thẳng vào `state.db`, workbook, `D:\\video goc` hoặc render output trong canary. Không tích hợp repo/route mới vào production chỉ vì command exit 0 hoặc wrapper báo success.

### Canary gate trước batch
Chạy tối đa một máy/account được chỉ định, không bypass CAPTCHA/puzzle/security:
- lấy ít nhất 5 URL thật từ **cùng một profile**;
- mọi URL có `/video/<id>` hợp lệ, không trùng và không phải deep-link lỗi;
- tải thử ít nhất 3/5 URL, file là MP4 hợp lệ và `ffprobe` đọc được duration;
- có manifest/report/artifact cho số URL, số download, kích thước và lỗi;
- xác nhận collector không làm mất lock, không chạm credential/cookie/token và không mutate production state.

Chỉ sau khi canary đạt mới nâng thành 30 URL/profile. Feed-only URL collection có thể là nguồn phụ để discovery, nhưng không được che thiếu nguồn bằng cách trộn feed với profile. Chi tiết evidence/reproduction nằm ở `references/phone-url-collection-canary.md`.

## STOP GATE cho máy live
- **Trần Worker & Đánh giá Hạ tầng (40 Workers so với 30)**:
  - Khi nâng `MAX_WORKERS` từ 30 lên 40, hạ tầng ADB daemon (port 5037), USB bus và Device Lock hoạt động hoàn toàn ổn định (0 lỗi transport lost, 0 lỗi lock conflict) nhờ cơ chế stagger ngẫu nhiên 2–8s.
  - Lỗi ATX (`ATX_SESSION_UNAVAILABLE`) không phải do tải máy chủ hay số lượng worker, mà do LMK (Low Memory Killer) trên từng thiết bị Android cũ khi TikTok chạy dài. Khắc phục bằng cơ chế dọn RAM + restart ATX trước khi chuyển bước.

- **Đăng video đồng loạt & Buffer Time giữa các ca (Chốt 2026-08-25)**:
  - Đăng video đồng loạt ở cuối phiên 3 rất tốt cho trust nick (lướt nuôi tương tác rồi mới đăng).
  - Khoảng cách giữa đợt đăng video ca trước và giờ bắt đầu ca sau tối thiểu phải đạt **30–45 phút**.
  - Nếu cách giờ cron ca sau dưới 30 phút: **TUYỆT ĐỐI CẤM CHẠY BÙ UPLOAD** để tránh xung đột device lock (`SKIPPED_LOCKED`) và loạn tài khoản giữa 2 ca. Thỉnh thoảng 1 nick lỡ nhịp 1 ngày không sao, ưu tiên giữ sạch ca cron kế tiếp.

- Không tự sửa code, chạy lại, probe ADB hoặc thao tác tay trên máy live khi user chưa yêu cầu rõ.
- Khi máy live lỗi: chụp màn hình thật tại hiện trường, giữ nguyên trạng thái, báo máy + nguyên nhân quan sát được và dừng chờ chỉ đạo.
- Không dùng ảnh Home sau cleanup làm bằng chứng cho lỗi xảy ra trước đó.
- Không can thiệp máy lock chéo; giữ lock trong lúc recovery/fix và unlock ngay khi hoàn tất theo policy farm.
- Không ghi credential, token, password hoặc dữ liệu workbook nhạy cảm vào log, test fixture hay báo cáo.
- **Giữ nguyên hiện trường lỗi:** CẤM tự động force-stop TikTok và về Home khi gặp lỗi runtime/blocker (`_cleanup_close_all_on_error = False`). Máy phải giữ nguyên app và màn hình lỗi tại thời điểm dừng để screencap banner đỏ và phục vụ triage. Chỉ sau 2h TTL mà không được can thiệp thủ công, reaper cron mới đưa máy về Home và thu hồi lock.

## Scoped row policy changes
Khi operator bật lại follow/upload sau tạm dừng toàn farm: gate theo physical `account_row_index` trong từng hook (row 1/2 đi tiếp, row 3+ ghi `status=skipped`). Xem `references/scoped-row-follow-upload-reenable-20260823.md`.

## Concurrency and session-completion planning
Khi operator hỏi tăng `max_workers` vì nhiều máy timeout hoặc không đủ 3 phiên/ca:
1. Đọc execution path thật trước khi tư vấn: Hermes runner cadence, active-manifest due window, launcher parameters, `max_workers` default/override, and `ThreadPoolExecutor` behavior. Không giả định runner gọi thêm máy mỗi 5 phút nếu scheduler thực tế chạy mỗi 15 phút; watcher offsets không phải feed workers.
2. Phân biệt hai vấn đề: (a) hàng chờ/wave capacity — tăng worker có thể giảm số wave; (b) per-device latency — ATX/ADB/XML/recovery timeout trên từng máy, tăng worker không làm một máy đọc XML nhanh hơn và có thể làm shared pressure tăng.
3. Chỉ đổi cap sau khi có tải đo bằng đúng production path: ATX session (không thay bằng `uiautomator dump`), mở TikTok + chờ load + nhiều vòng XML/read/swipe, dùng serial-scoped ports. Mốc đã biết: 20 an toàn, 30 đã đo full-session không lỗi, 40 bắt đầu có lỗi nhẹ; không suy ra 35/40 an toàn nếu chưa đo.
4. Nếu operator **đã chỉ đạo rõ chạy 40 để so sánh thực tế**, không cần chặn bằng canary tổng hợp riêng: lấy log 30-worker đã chạy làm baseline, đổi **các launch tương lai** sang 40, giữ nguyên process 30 đang chạy, rồi theo dõi đến hết khung vận hành được yêu cầu. Đây là A/B theo cửa sổ thực tế, không phải khẳng định trước rằng 40 an toàn.
5. Khi đọc baseline/comparison, chỉ dùng nhóm hạ tầng để phán cap: đếm riêng ADB transport/`adb command timed out`, ATX unavailable/capture timeout, và `max_duration_seconds exceeded`. Loại khỏi verdict worker-cap các lỗi VPN/ViChanger, account/login, popup/manual-needed, follow/upload, classifier, logger/artifact; báo các nhóm đó riêng. Ưu tiên số **máy/batch bị ảnh hưởng**, event count chỉ là chỉ số phụ vì một payload có thể lặp cùng lỗi nhiều lần.
6. Trước khi báo “đã tăng”, phải patch đúng cả launcher default và flow fallback (nếu cả hai tồn tại), rồi compile/config-test. Kiểm tra command line process để xác nhận batch đang chạy dùng cap nào; không gán cap mới cho process cũ.
7. Báo cáo operator ngắn: cadence thực tế, cap baseline/cap mới, số ADB/ATX/max-duration theo máy, completed sessions/wave completion, và blocker phân biệt rõ. Không đưa bảng số liệu khô nếu user chỉ hỏi chiến thuật; chỉ nêu số quan trọng phục vụ quyết định.
8. Không suy ra số liệu tải từ memory, test cũ, hoặc một reference chưa được đối chiếu với log hiện tại. Nếu chưa có evidence 30-vs-40 cùng workload, nói rõ `UNPROVEN`; không tự bịa tỷ lệ/lỗi để biện minh cho cap.
9. Khi operator báo “ca tối không thấy cron”, kiểm tra riêng ba lớp: (a) scheduler metadata/last_run/`already running — skipping`, (b) live runner lease và PID, (c) artifact-root/run manifest mới nhất. `last_status=ok` hoặc cron output `silent` chỉ chứng minh script exit/không có stdout, không chứng minh đã spawn batch. Nếu lease còn sống hoặc runner process chồng lấn, không kill/reclaim máy chỉ để tạo ca mới; xác định PID, start time, expiry và artifact trước.
Reference: `references/concurrency-cap-and-timeout-triage-20260823.md` và `references/cron-lease-and-scheduler-overlap.md`.

## Quy trình chuẩn
1. **Chốt scope:** xác định repo, flow, máy live hay fixture/test; đọc AGENTS/PROJECT_RULES và kiểm tra `git status` trước khi sửa.
2. **Tìm call chain:** lần theo classifier → safety → popup dispatcher → flow handler. Không grep toàn ổ đĩa; ưu tiên `git grep`, symbol search và đọc quanh call site.
3. **Xác định classifier precedence:** detector cụ thể phải chạy trước marker tổng quát. Popup có selector/close-X hợp lệ phải đi qua typed handler; marker không có selector an toàn phải fail-closed.
4. **Chọn đúng phạm vi false-positive:** nếu user nói bỏ hẳn một cơ chế (ví dụ signup/registration → login-overlay), gỡ keyword, output label, safety mapping, recovery guards và detector/dismisser chỉ phục vụ cơ chế đó; không chỉ thêm bypass cho một loại ad. Giữ login thật, lockscreen, captcha/verification và popup có rule riêng.
5. **Sửa nhỏ nhất:** không xóa toàn bộ safety để xử lý false-positive. Không restore cả file về HEAD nếu worktree đã có thay đổi của user; preserve và inspect diff trước. Sau mỗi patch kiểm tra `git diff --stat`, `git diff --check` và `git grep` các symbol/label cũ; không dùng replace-all với chuỗi quá ngắn trong file lớn.
6. **Test trước live:** thêm fixture cho trạng thái recoverable và trạng thái blocked; test cả action selector, re-capture sau action và terminal behavior. Test fixture phải phản ánh đúng yêu cầu cuối cùng, không giữ assertion cho label/cơ chế đã bị xóa.
7. **Verify:** chạy test tập trung, test flow liên quan, compile/lint/diff check; dùng `PYTHONPATH=<repo>;<repo>/python_runner` khi chạy toàn suite để các test import `python_runner` đúng. Tách lỗi môi trường/import hoặc lỗi pre-existing khỏi regression mới; không chạy live/device nếu user chỉ yêu cầu code fix.
8. **Commit/push:** chỉ khi user yêu cầu; stage explicit paths, pull/rebase trước commit và push, xác minh local SHA = remote SHA, rồi báo rõ các test pass và blocker còn lại.
9. **Báo cáo ngắn:** mục đích, file/logic đã đổi, kết quả test, blocker; không kể workflow nội bộ dài dòng.

## Captcha và verification: safety boundary
### Captcha có close-X
Captcha puzzle có X đóng được là trạng thái recoverable, không phải lỗi fatal. Classifier phải nhận diện bằng evidence UI đủ mạnh và route sang popup path hiện hữu (`manual-needed:popup` hoặc equivalent), để `detect_tiktok_popup_action()` / `dismiss_verify_dialog()` chọn đúng selector và đóng X. Sau khi tap bắt buộc capture lại UI; chỉ coi là recovered nếu marker biến mất và màn hình sau đó hợp lệ.

Đặc biệt với drag-piece Captcha:
- `verify-bar-close` là banner-close do GemPhoneFarm inject, không mặc nhiên là X của puzzle.
- Puzzle close-X phải được tìm bằng detector chuyên biệt, loại trừ `verify-bar-close`.
- Không tap tọa độ mù và không coi việc tap thành công là bằng chứng đã thoát Captcha.

### Captcha không có close-X
Giữ nguyên `manual-needed:manual_challenge`/`manual-needed:verification` và safety stop. Không dùng generic close detector để “cố” đóng. Nếu handler buộc phải restart/relaunch theo policy hiện hữu, vẫn phải re-capture và giữ artifact trước cleanup.

### Không mở rộng detector tổng quát
Không route mọi màn có chữ `xác minh`, `verify`, `Đóng` hoặc `captcha` sang generic popup, vì có thể làm sai:
- quick-security popup;
- verify-email prompt;
- OTP/password/input screen;
- account/login/security dialog;
- dialog không có close-X hợp lệ.

Detector-specific classification phải giữ precedence và test regression cho các màn trên.

### False-positive từ huy hiệu tích xanh (Verified Badge)
Node `content-desc="Huy hiệu đã xác minh"` (hoặc `verified badge`, `tài khoản đã xác minh`) trên profile hoặc feed của tài khoản tích xanh (KOL, nghệ sĩ, brand) chứa chuỗi con `xác minh`.
- Rule `manual_challenge_terms` trong classifier và `blocker_terms` trong switcher sheet bắt buộc phải loại trừ các cụm từ verified badge (`_VERIFIED_BADGE_TERMS`).
- Tránh việc điều hướng trúng trang profile tích xanh làm classifier bắt nhầm thành `manual-needed:verification` và dừng phiên sai.

## Safety-Critical UI detector contract
Khi detector quyết định gọi `BACK`, tap hoặc điều hướng, classifier là **safety boundary** chứ không chỉ là UX logic.

1. Tách **ownership evidence** khỏi **transient evidence**:
   - Ownership: resource/container Story-specific hoặc `EditText` chứa direct marker tiếng Việt (`nhắn tin cho`, `gửi tin nhắn cho`) loại trừ `_DM_EXCLUSION_TERMS` (như `message_input`, `chat_room`, `im_title_bar`). Không chỉ dựa vào resource ID cứng (`story_reply_input`) vì TikTok live có thể dùng id động/chung (`input_box`, `e_4`).
   - Transient: input đang focus, keyboard, reaction tray hoặc control overlay.
   - Không dùng keyboard toàn cây, generic text (`Reply to`, `Send a message`) hoặc emoji caption để chứng minh ownership.
2. Correlate mọi evidence trong một bounded scope: dùng common parent gần nhất của marker + input + tray; không ghép node rời rạc dưới XML root hoặc host container rộng.
3. Fail-closed khi XML/OCR mơ hồ. OCR generic không đủ để dispatch `BACK` vì wording có thể xuất hiện ở DM/share/comment.
4. Pre-action và post-action là hai predicate khác nhau. Pre-action xác minh target; residual check sau `BACK` chỉ được giữ nếu cùng Story anchor/scope còn tồn tại.
5. Reaction evidence phải là tray resource/control thật hoặc nhóm control có cấu trúc; một hoặc hai emoji trong caption không phải Quick Reaction.
6. Keyboard evidence phải gắn với Story input đang `focused=true`; nếu có foreground input khác focus thì không dùng keyboard toàn cục cho Story.
7. **Live Canary trước khi đóng phiên:** Mọi bản vá lỗi popup/feed kẹt bắt buộc phải chạy live canary thực tế trên target bị lỗi (`run-feed-session.ps1 -Machines <id> -Row <row> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run`) để xác nhận pass thực tế trước khi chốt phiên.

### Regression matrix bắt buộc
- Story Reply có anchor + input focus + keyboard: match.
- Story Quick Reaction có tray resource, kể cả tray là sibling bounded của composer: match.
- DM/share/comment generic + keyboard: không match.
- Story background + input foreground khác đang focus: không match.
- Caption chứa emoji nhưng không có tray/control: không match.
- Residual sau BACK khi Story anchor mất: không tiếp tục BACK lần hai.
- XML malformed/empty hoặc OCR-only wording mơ hồ: fail-closed.

Chi tiết fixture và pattern scope: `references/safety-critical-ui-detectors.md`.

## Popup recovery contract
Một popup dismiss chỉ hợp lệ khi có đủ:
1. XML/UI evidence xác định loại popup và selector;
2. action typed, bounded và đúng selector;
3. after-capture thành công;
4. package/focus và screen sau action hợp lệ;
5. result row được ghi rõ `popup_type`, `popup_dismiss_action`, `popup_dismissed`, `popup_dismiss_reason`, `safety_status`.

Nếu action fail hoặc marker còn lại: giữ `manual-needed`, không tự biến thành success. Với lỗi fatal, chụp raw screen trước `force-stop`, `HOME`, cleanup hoặc banner overlay; raw artifact và Telegram artifact nên tách nhau.

### One-off live: account-security update popup
When the user explicitly asks to dismiss the TikTok popup `Tài khoản của bạn cần được cập nhật`, perform only the named secondary action `Để sau`; never select `Liên kết số điện thoại hoặc email` or change account/security settings.

Required sequence:
1. Resolve the target machine and serial from the authoritative machine/account mapping before touching ADB; do not infer the target from a Telegram screenshot alone.
2. Capture a fresh screenshot for visual confirmation, then capture fresh ATX XML. Require the exact popup title and exact clickable `Để sau` node in the same capture. Do not use guessed coordinates.
3. Use the verified node bounds and an ATX JSON-RPC `click` (not blind shell tap) on that exact node. If the ATX process/forward is needed, discover the exact `com.github.uiautomator` process by parsed columns, excluding `.test`; reuse the target serial's existing dynamic forward when present. Never clear all forwards on a live farm.
4. Wait briefly and re-capture ATX XML. Success requires the popup title and `Để sau` marker to be absent; otherwise fail closed and preserve the screen.
5. Report only target serial, typed action, ATX acknowledgement, and post-action marker status; do not claim success from the click response alone.

Session-specific evidence and the robust PID/forward parsing pattern are in `references/account-security-update-popup.md`.

## Popup request disambiguation: live action vs script/code handling
The user may ask either for a one-off live action or for the automation behavior to be encoded. Parse the latest wording literally; a screenshot of a live machine does not by itself authorize a live tap.

- If the request explicitly says to tap/click/handle a named machine live (for example, “gặp này bấm follow lại 1,2 người rồi đóng”), perform only the named target action, with ATX/XML evidence and post-action recapture.
- If the request says **“handle script”**, “xử lý trong script”, “sửa code”, “fix lỗi”, or points to a recurring alert/runtime exception, treat it as a **code-fix request**. Do not tap the live device unless live execution is separately and explicitly requested.
- For code-fix requests, trace the actual call chain (classifier → popup dispatcher/registry → consumer handler → shared core if applicable), then add a fixture/regression test for the exact popup/error path before patching. A symbol defined in one module is not available to another consumer module unless explicitly imported; verify module import/export boundaries and execute the failing path, not only a grep.
- If both live handling and code-fix are requested, do the smallest target-scoped live action plus the code change; report them separately. Never present a manual live repair as proof that the automation is fixed.

Incident detail and regression shape: `references/script-popup-handler-incident.md`.

## Popup “Follow bạn bè của bạn”: distinguish live action vs code-fix request
The user may ask either for a one-off live action or for the automation behavior to be encoded. Do not infer one from the other:

- If the request is explicitly live/manual (for example, “gặp này bấm follow lại 1,2 người rồi đóng”), perform only the named target action, with ATX/XML evidence and post-action recapture.
- If the user reports a recurring alert/error and says “xử lý lỗi này”, “sửa code”, or later asks why code was not changed, treat the request as a **code-fix request**. Inspect the actual call chain (classifier → popup dispatcher/registry → consumer handler → shared core if applicable), add regression tests, and do not stop after manually repairing one live device.
- If both live handling and code-fix are requested, do the smallest target-scoped live action plus the code change; report them separately. Never present a manual live repair as proof that the automation is fixed.

### Required automation contract for this popup
1. **Detection & Priority:** Detect the typed popup using title keywords ("Follow bạn bè của bạn" / "Follow your friends") + actionable button ("Follow lại" / "Follow back"). Evaluate two-phase follow rules *before* close-only rules, but keep other safety/permission rules prioritized.
2. **Follow Boundedness:** Tap **at most two** exact `Follow lại`/`Follow back` nodes. After each tap, recapture fresh XML and verify button state transition or popup dismissal; never re-tap the same stale element or tap a third row.
3. **Semantic Close & Containment:** Find the close control strictly via semantic attributes (`content-desc="Đóng"` / `"Close"` / `"✕"` / `"X"`). Constrain search geometry to the header bounds of the detected dialog to avoid tapping background/unrelated close buttons.
4. **Fail-closed & No tab/back fallback:** Do not switch tabs or press BACK as a fallback for this popup modal. If close tap fails or post-close verification shows popup is still present, return `dismissed=False` with an explicit reason.
5. **Multi-layer Coverage:** Maintain consistency between the shared `automation-core` (`src/automation_core/tiktok_popup.py`) and the consumer flow (`python_runner/flows/benign_popup.py`). Ensure both pass their respective regression suites before release.

### One-off live procedure
1. Capture UI XML by ATX before action; confirm the exact popup.
2. Choose only 1 or 2 rows as requested; after each click recapture and verify `Follow lại` changed to `Đã follow` (or equivalent).
3. Stop at the requested count; do not use the popup to follow a third person.
4. Recapture, find the real close node (`content-desc="Đóng"`/`id/e63`), click via ATX bounds, and recapture again.
5. Report the exact number followed and whether the popup marker disappeared. A live result does not replace the code-fix path above.

## Rotation-preparation timeout
- `settings put system accelerometer_rotation 0` + `settings put system user_rotation 0` are the canonical writes — sufficient, never hang.
- **NEVER add `content insert --uri content://settings/system`** to the rotation helper. It hangs on Samsung S7 / OneUI (ADB timeout 15 s), propagates uncaught out of `ensure_portrait_rotation`, and kills the child session even when TikTok is on a healthy feed. Confirmed removed from both files (2026-08-23).
- Alert signature: `adb command timed out` on `shell content insert ... accelerometer_rotation` while machine screenshot shows TikTok feed tab (Đề xuất) — healthy. This is a prep-step failure, NOT a feed/account/CAPTCHA error.
- When patching, always fix **both** `python_runner/flows/device_prepare.py::ensure_portrait_rotation` AND `automation-core/src/automation_core/startup.py::lock_portrait_rotation` together — they share the same logic.
- Do not rerun a live target merely to validate this offline diagnosis. Verify with `test_device_prepare.py` (consumer) + `test_startup.py` / `test_device_readiness.py` (core).
- Full diagnosis checklist and confirmed fix details: `references/rotation-preparation-timeout.md`.

## Fast Swipe and Deep Inspect Interleave Architecture
Để chống cạn kiệt deadline 600s (`run plan max_duration_seconds exceeded before navigate profile`) và mô phỏng chính xác hành vi người thật trên Galaxy S7:
1. **Phân loại 2 chế độ vuốt:**
   - **Fast Swipe (Lướt nhanh ~70%):** Xem 2.0s – 5.0s, gửi lệnh ADB swipe trực tiếp, KHÔNG gọi ATX dump XML và KHÔNG chụp ảnh. Vẫn tăng `swipe_count` và được tính đầy đủ vào `total_swipes_completed` khi tổng kết phiên.
   - **Lightweight Focus Guard (<0.2s):** Sau mỗi Fast Swipe, kiểm tra nhanh `get_focused_activity(ctx)` qua dumpsys. Nếu mất focus TikTok hoặc phát hiện activity popup/crash ngoài dự kiến, lập tức escalate `is_deep_inspect = True` để dọn dẹp thay vì quẹt mù.
   - **Deep Inspect (Kiểm tra sâu ~30%):** Chạy full `_capture_step` (ATX XML dump, screenshot, popup recovery ladder, keyboard cleanup). Tương tác Like chỉ xét ở Deep Inspect với tỷ lệ nâng lên 20% (bù tương đương ~10% toàn phiên).
2. **Chu kỳ xen kẽ & Bắt buộc ở biên:**
   - Sau ngẫu nhiên 2 – 4 video Fast Swipe (`random.randint(2, 4)`), thực hiện 1 video Deep Inspect.
   - **Ép buộc Deep Inspect:** Video 1 (Baseline / startup), Video cuối cùng (`swipe_count == selected_total_videos`), khi đổi tab feed (`for-you` <-> `following`), và bước đối soát `verify_profile`.
   - Nâng tổng video toàn phiên lên 12 – 16 video trong khi rút ngắn thời gian toàn phiên từ 28–30 phút xuống ~3 – 4 phút/máy.
   - Hạ `DEFAULT_DEVICE_TIMEOUT_SECONDS` từ 1800s xuống 600s (10 phút) để ngắt sớm các máy bị treo thật mà vẫn dư buffer cho phiên bình thường.
Reference: `references/fast-swipe-interleaved-deep-inspect-20260824.md`.

## Runtime version and timeout triage
When the user asks whether a live machine has received a code change, do not infer runtime provenance from the current worktree or the alert screenshot alone. Verify all three layers:

1. **Live process:** read the actual process command line, executable/interpreter, repository/working-directory arguments, artifact-root argument, and process creation time. The command line is the runtime source-of-truth for which launcher is currently executing.
2. **Target artifact:** read the exact machine-scoped `log.jsonl` from that run. Prefer an explicit runtime configuration event (for example `requested_min_total_videos`, `requested_max_total_videos`, `selected_total_videos`, timeout/deadline values) over source inspection. Resolve the machine and account from the same log; do not map from a Telegram screenshot alone.
3. **Source chronology:** compare the live process start time with the commit/change time and inspect the actual launch path. A commit present in the repo is not proof that a process started before or after it loaded that code; if the process was launched before the change, mark runtime version `UNPROVEN` unless the log contains configuration evidence.

For feed-session timeout reports, separate the session target from the wall-clock budget. The 10–14 video cap can be active while the run still times out because the same deadline includes startup/preflight, profile navigation/verification, screenshot/XML capture, keyboard cleanup, popup probes/recapture, swipe watch delays, and final navigation. Quantify the timeline from the target log before attributing the timeout to video count. If the target log ends before the reported timeout event, report `timeout not yet confirmed` and distinguish the observed last step from the user's alert summary.

Report concise facts with `confirmed`, `excluded`, and `unproven` labels. Never claim the old target (for example 10–18) is still running when the exact target log records the new bounds; never claim the timeout root cause from source constants alone. Session-specific evidence examples: `references/runtime-version-and-timeout-triage.md`.

## Session deadline start contract (preflight excluded)
Per-device feed-session timeout budget starts at the child-flow boundary, not at batch start:
1. In `python_runner/flows/multi_machine_feed_session.py::_run_child`, `child_config["_deadline_monotonic"] = time.monotonic() + timeout_seconds` must exist ONLY in the preflight-success branch: after `_validate_child_adb` returns SUCCESS and `prepare_tiktok_for_smoke` returns SUCCESS, on the line immediately before `feed_session_smoke(child_ctx)`.
2. Validation/prepare wall time must NOT be deducted from the 1500 s budget (`DEFAULT_DEVICE_TIMEOUT_SECONDS`); if either preflight fails, no deadline key is assigned at all.
3. Consumers stay untouched: `core/deadline.py::ensure_run_plan_deadline` and the feed_swipe_smoke watch-delay check read `_deadline_monotonic` whenever present — do not change them for this contract.
4. **Slow-device timeout pitfall:** Even with preflight excluded (taking ~20–30s), slow devices (e.g. Galaxy S7) spend ~90–110s per video cycle primarily on `capture_screenshot` (~50%) and `dump_ui_xml` (~20%). When assigned high random video targets (13–14 videos), the swipe loop alone (~13 × 100s = 1300s + post-swipe navigation) can still exceed the 1500s budget by several seconds. Triage must decompose `log.jsonl` into screenshot/XML vs watch-time duration.
5. Regression tests: `MultiMachineFeedSessionTests::test_session_deadline_starts_only_after_validation_and_prepare` and `::test_no_session_deadline_when_prepare_preflight_fails` in `python_runner/tests/test_multi_machine_feed_session.py`; keep green alongside `test_child_honors_per_device_deadline_and_finalizes_summary` (preserves post-`feed_session_smoke` timeout behavior).

Pitfall: never assert inside a mocked `prepare_tiktok_for_smoke`/`feed_session_smoke` side_effect whose FAIL result you expect — production's generic exception handler swallows the AssertionError into an expected `failed` row and the test passes vacuously while the bug still exists. Record what the mock saw into an external `observed` dict; assert outside the patched block. To attribute unrelated full-file failures on a dirty worktree, rerun suspects in a throwaway pristine copy (`git worktree add "D:\\Taadaa\\_tmp" HEAD`; pass Windows-style quoted paths to git worktree — MSYS `/d/...` paths make git create the tree at a wrong location), then remove it. Detail + verification transcript: `references/session-deadline-preflight-deferral-20260823.md`.

## Public-profile classifier false-positive guard

A TikTok public/visited profile opened from a suggestion card may not expose the selected bottom `Hồ sơ`/`Profile` tab or the `view_profile` container. Do not classify it as `login/account` merely because its UI contains account-related copy such as `Tài khoản được đề xuất`, `Bạn bè với...`, or profile statistics.

### Precedence & structural header binding
1. **Login Precedence:** Must run AFTER authoritative login checks (`has_sensitive_marker()`, `detect_save_login_popup()`, `_is_account_switcher_sheet()`, `login_terms`) so true login/credential dialogs are never bypassed by background profile elements.
2. **Display Name + Handle Anchor:** Require a non-empty display name immediately above `@username` ($0 < \Delta Y \le 120\text{px}$) with horizontal bounds overlap in the same package (`com.ss.android.ugc.trill`).
3. **Continuous Stats Row with Numbers:** At least 2 stat categories (follower, following/`Đã follow`, likes/`Thích`) having numeric digits, aligned on the same horizontal row ($\Delta Y \le 140\text{px}$, gap $\le 120\text{px}$).
4. **Dual Profile Actions with Clickable Verification:** Visited public profiles render both `Follow` (or `Đã follow`/`Đang follow`) and `Nhắn tin`/`Message` (`clickable="true"`). Requiring $\ge 2$ distinct profile action controls positioned directly below the stats row ($stat\_bottom \le Y \le stat\_bottom + 180\text{px}$) prevents misclassifying compact suggestion cards or feed captions (which only have 1 `Follow` button).

Do not perform a global unbound string rejection for "password"/"sign in" inside the helper; relying on login precedence before the helper prevents caption text from breaking valid profile detection.

Regression contract:
- Add a fixture matching the public-profile shape before changing classifier code and verify it is RED first.
- Assert the public profile becomes `profile` with `manual_needed=False` and safety `ok`.
- Assert a real login screen and a feed login prompt remain `manual-needed:login`.
- Assert a suggestion card with single `Follow` button does NOT get classified as `profile`.
- Run the focused classifier and profile/login feed-session tests; separate unrelated pre-existing dirty-worktree failures from this regression.

Detailed fixture shape and session evidence: `references/public-profile-login-false-positive.md`.

## Offline recurring-alert debugging: exact evidence + deadline budget

For repeated `TikTok focus lost` incidents, distinguish the failing seam before reviewing a fix: post-swipe launcher recovery, notification-shade/profile-navigation preflight, and baseline startup preparation are separate call chains. A recovery added to one seam does not cover the others. Use `references/focus-loss-preflight-recovery-coverage-gap-20260823.md` for the exact evidence chain, provenance checks, and regression-attribution gate.

When a recurring `multi-machine-feed-session` alert is a code-fix request, do not touch the live device. First identify the exact run/machine/account/step from `log.jsonl`, then open the exact attempt's `ui.xml` and matching screenshot. Treat classifier fields and directory names as metadata until the files are actually read.

For feed-tab failures, distinguish these cases:

- **Confirmed valid feed, wrong requested tab:** XML and screenshot show a real TikTok video feed, but the selected tab differs from the expected tab. Add recovery only at the post-popup/post-navigation boundary that owns the expected tab; mark the row degraded/continued and record `feed_drift_from`/`feed_drift_to`.
- **Confirmed deadline starvation:** a later capture hits `max_duration_seconds` after a prior valid capture, while a popup/recovery loop has spent repeated capture/retry time. Trace timestamps and count the loop cost. If the caller already supplies exact XML, make initial-miss probing non-retrying for that boundary rather than weakening the global verifier.
- **Missing or malformed evidence:** remain failed/manual-needed; never accept the feed from `detected`, `xml_available`, or a stale screenshot alone.

Regression tests must cover both the positive safe-tab recovery and the fail-closed no-XML case, plus an assertion that the post-swipe popup checkpoint does not retry initial misses. Run the focused slice immediately after edits; report any broader dirty-worktree failures separately and do not widen the fix to unrelated worker/lock tests without authorization.

Detailed replay pattern and evidence fields: `references/feed-alert-evidence-and-deadline-budget.md`.

Nested capture metadata recovery lesson and offline regression shape: `references/focus-loss-nested-capture-recovery-20260824.md`.

### Reviewing landed fix candidates: retry-flag opt-in + popup-drift recovery
When closeout-reviewing implementations of the two fix classes above, verify the safety envelope survived:

1. **Retry flag stays opt-in:** `retry_after_initial_miss` must default `True` on every checkpoint layer (`_gem_blind_probe_rule_for_checkpoint` → `_run_gemphonefarm_blind_popup_checkpoint` → `_maybe_run_gemphonefarm_blind_popup_checkpoint`); grep every call site — only the boundary that owns the supplied exact XML may opt out. The initial-miss guard must return the supplied XML immediately (no sleep, no recapture); all other checkpoints keep the old behavior.
2. **Drift recovery is fail-closed:** accept only `status=failed` + `reason="feed not confirmed"` + `safety_status=ok` + detected top tab in `FEED_TYPES` differing from expected + XML evidence (`xml_available` or latest-attempt `xml_path`). Relabel DEGRADED with `popup_feed_tab_drift_recovered` and `feed_drift_from/to`. Call-site ordering matters: run recovery before verify-trap-dismiss and BACK-recheck stages so they inherit the corrected `current_feed_type` in their own expected-feed labels.
3. **Required regressions:** (a) kwarg-threading assertion — mock the checkpoint runner and assert `call_args.kwargs["retry_after_initial_miss"] is False`; (b) positive drift recovery asserting DEGRADED + marker fields; (c) fail-closed no-XML case keeping the row `failed`.

Read-only review discipline for this repo: syntax-check dirty files with `python -c "import ast; ast.parse(...)"` (or `python -B`) instead of `compileall`/plain pytest so no `__pycache__` appears in a review-only worktree; capture `git status --porcelain` before and after and require identical output. Candidate evidence and exact wiring: `references/popup-drift-retry-flag-candidate-review-20260823.md`.

## Capture producer/consumer compatibility & XML normalization
- Profile capture gates must support both modern metadata (`xml_path`, `screenshot_path`, `status=complete`) and legacy metadata (`artifact_path` only). Derive exact file paths from a legacy directory, then validate the actual XML/PNG files before accepting; never trust metadata alone.
- **XML Line Ending & Whitespace Pitfall:** Khi đối soát `ui.xml` lưu trên đĩa với chuỗi `xml_text` trong bộ nhớ (`_profile_capture_artifact_is_complete`), bắt buộc so khớp sau khi chuẩn hóa dòng (`line.strip()` và bỏ dòng trống). Tuyệt đối không dùng so khớp chuỗi thô `persisted_xml == xml_text` vì khác biệt ngắt dòng (`\r\n` vs `\n`) giữa ATX/ADB và file disk sẽ gây false positive `ui.xml does not match the parsed capture`, làm tất cả các máy fail oan thành `capture-artifact-incomplete`.
- Keep the detailed incident, validation order, and regression matrix in `references/profile-capture-artifact-contract.md`.

## Exact-capture ownership and popup retry budget
When a checkpoint receives the exact XML already captured by its owning boundary, an initial detector miss is evidence of absence in that capture—not permission to spend another ATX capture budget. At baseline and profile-preflight, pass `retry_after_initial_miss=False`; the helper must return the supplied XML without sleeping or calling `_capture_xml_text` again. Preserve retries for checkpoints without an owning exact XML, and always keep a fresh post-action recapture after a popup action. This prevents a secondary `ATX_SESSION_UNAVAILABLE` from masking the original loading/manual-needed state. Evidence and regression recipe: `references/exact-capture-popup-retry-budget.md`.

## Artifact-backed LIVE feed misclassification
When a recurring alert says `unknown TikTok state`, do not infer an unknown screen from the alert screenshot or terminal status. Replay the exact attempt artifact first. A TikTok screen with all of the following is a valid feed state, not an unknown popup:

- TikTok package/focus is present;
- a selected top feed tab such as `Đề xuất`/For You is present;
- Home/`Trang chủ` is selected; and
- LIVE evidence such as `LIVE`, `Nhấn để xem LIVE`, or `Đang LIVE` is present.

Classify this as the selected feed type (normally `for-you`) before generic popup/unknown handling. Keep genuine live-room invite overlays and live product drawers on their typed popup paths; do not broaden the LIVE rule from a single `LIVE` marker alone. Add an artifact-backed regression that reads the exact `ui.xml` and asserts the classifier result and `manual_needed=False`. The replay recipe and evidence checklist are in `references/live-feed-artifact-replay.md`.

### Contextual Home-feed header variant
The classic LIVE-feed test is insufficient when the alert's header uses `LIVE`, `Cộng đồng`, a location label, and `Đã follow`. For this newer layout, require selected `Trang chủ`, TikTok ViewPager, and the bounded `:id/twc` header before bypassing the live-room popup detector. Add a red-first minimal fixture for the exact shape, then run focused classifier/popup/feed-session tests. Replay details and the regression recipe are in `references/contextual-home-feed-live-misclassification.md`.

### Explicitly authorized, target-scoped live canary after a code fix
A code-fix request does not automatically authorize live execution, but an explicit latest user instruction that says live execution is allowed to validate the fix does. When that authorization is present, perform a bounded canary rather than stopping at offline tests or treating a wrapper exit code as proof:

1. **Lock the scope:** use only the named machine and its authoritative machine/serial mapping; do not infer the target from an alert screenshot. Check ADB online state, TikTok package presence, active lock state, and the pre-run dirty baseline. Do not read credentials or unnecessary workbook values.
2. **Bound the action:** run the smallest production path that exercises the fix, normally `feed-session-smoke` with at most 1–3 swipes. Do not expand to other machines, full-suite tests, follow/like/upload, blind retries, ADB restart, or `pm clear`. Avoid `--prepare-tiktok` unless the user requested it or preflight evidence requires the narrowly permitted startup action.
3. **Capture before and after:** persist a fresh preflight screenshot/focus record. After the run, inspect `summary.txt`/manifest, the target `log.jsonl`, and the exact same-attempt `ui.xml` + `screen.png`; a `success` wrapper result alone is insufficient.
4. **Classifier acceptance:** require target-scoped feed records with `detected_screen=for-you` (or the expected feed), `manual_needed=false`, safety `ok`, and zero `unknown TikTok state` records. A typed popup may occur only if its bounded handler records safety `ok`, performs the permitted dismiss action, and a fresh post-action capture returns to a known feed. Require the requested swipe count to be completed.
5. **Closeout:** verify the lock is absent from the live lock root after completion; do not confuse historical backup/quarantine lock files with an active lock. Report only purpose, result, exact evidence paths, transient popup/blocker facts, and excluded/unproven findings. Stop after canary acceptance; do not claim the fix is fleet-wide from one target.

Detailed command/result shape and evidence checklist: `references/live-canary-after-fix.md`.

## Fresh-anchor recovery after BACK in account-switcher flow:

When the first switch-anchor tap leaves Profile visible and the bounded recovery sends `BACK` to dismiss a possible overlay/keyboard, do not immediately reuse the original `UIElement`. TikTok can re-layout the Profile header after BACK, making the old element a stale coordinate or the display-name body rather than the current account-switcher arrow.

Required bounded sequence:
1. Preserve the pre-action artifact and classify the first post-tap capture; do not infer that the switcher opened from the tap return code.
2. Send the existing, policy-approved `BACK` recovery once.
3. Capture fresh Profile XML after BACK and reject it if it is already a switcher or titleless switcher.
4. Parse the fresh XML and resolve a new semantic switch anchor with the same provider-specific guards used by the initial path.
5. Retry the anchor at most once, then capture fresh XML again. Accept recovery only when switcher evidence is present; otherwise retain `manual-needed:account-switcher-not-open` and preserve the scene.
6. If the fresh capture is malformed/unavailable, fail closed; using the previously verified anchor is only a bounded fallback and must never become a broad coordinate/keyword search.

Regression must prove that the fresh anchor's bounds are used and the stale anchor is not tapped. Keep the existing missing-account, login/add-account, verification, and sensitive-popup tests unchanged.

Reference: `references/account-switcher-fresh-anchor-after-back.md`.

## Pitfalls
- A recurring alert can require both a code-path fix and a target-scoped live validation; do not confuse a manual repair with a fleet-wide fix.
- Keep typed popup detection ahead of generic close-only detection, and preserve fail-closed behavior for login, OTP, security, and unknown states.
- The shared core may pass while the consumer registry is stale; verify both paths.
- Do not claim code fixed without fresh focused tests or live fixed without target-scoped recapture evidence.
- For post-feed hooks, treat feed success as an intermediate milestone. Keep the canonical wrapper alive until its terminal result; inspect `follow_result.json`/hook logs/final manifest and report feed, follow, upload, and wrapper statuses separately. Do not launch a duplicate run or kill the wrapper merely because the feed child passed. If a hook is still running, report `chưa xong`; if it reaches `MANUAL_REVIEW`/`TIMEOUT`/script error, preserve the feed evidence and report that blocker separately.

## Test matrix minimum
- Typed popup actions use bounded taps, fresh recapture, and semantic close controls.
- Missing selector, missing capture, residual marker, or malformed evidence remains fail-closed/manual-needed.

See `references/full-flow-downstream-hook-completion.md` for the full-flow completion and downstream-hook evidence contract.

## Test matrix tối thiểu
- Captcha puzzle + real close-X → popup recoverable, đúng selector, after-capture feed/focus hợp lệ.
- Captcha text + chỉ `verify-bar-close` → vẫn blocked; không chọn banner-close làm puzzle X.
- Verification/quick-security/verify-email có rule riêng → không bị generic Captcha route làm thay đổi classifier.
- Captcha/verification marker biến mất sau re-check → tiếp tục phiên.
- Marker còn lại hoặc close action unavailable → manual-needed/fatal theo policy.
- Feed/session flow → row summary và `ManualReasonGuard` không dừng nhầm sau recovery.

## Scope disambiguation: focus-lost vs GET_IP/VPN alerts

Treat `TikTok focus lost` and `ViChanger GET_IP failed` as independent failure signatures even when they appear in the same alert stream or screenshot. Do not use one as the root cause of the other, and do not widen a focus/profile incident into VPN/proxy/core work without target-scoped evidence.

For a recurring `TikTok focus lost` / profile-navigation failure:
1. Trace the actual consumer call chain and identify the navigation seam (`tap_navigation_target` → caller guard/profile verification).
2. A successful ADB tap is not UI success proof. Check foreground package/activity before the tap **and again after the tap**.
3. If post-tap focus is not the configured TikTok package (for example `com.android.systemui`/Recent Apps or Launcher), fail closed immediately, log `verify_tiktok_focus_after_navigation`, preserve the blocker scene, and do not parse stale XML or identity fields.
4. Add a regression fixture where pre-tap focus is TikTok, the tap returns OK, and post-tap focus is SystemUI/Recent Apps; assert navigation failure and the exact reason.
5. Verify the seam is actually imported/called by `feed_swipe_smoke`/`multi-machine-feed-session`; do not stop at a helper-only test.

For `ViChanger GET_IP failed after 3 retries`, keep it a separate investigation: compare the exact broadcast argv with the foreground-receiver contract, verify source → artifact → consumer pin, and add an exact-command regression before changing retry/recovery/VPN policy. Contract and repro offline: `references/vichanger-get-ip-broadcast-foreground.md`.

## Shared ViChanger GET_IP timeout contract

Khi gặp `ViChanger GET_IP failed after 3 retries` kèm timeout lặp lại ở `adb ... am broadcast ... .AdbCaller`, không tăng retry một cách máy móc. So sánh exact broadcast command với contract foreground, xác minh core source/artifact version, rồi thêm regression assertion cho toàn bộ argv trước khi sửa recovery/VPN policy. Contract và repro offline: `references/vichanger-get-ip-broadcast-foreground.md`.

## Lệnh kiểm tra tham khảo
Từ repo consumer:
```bash
python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_classifier.py python_runner/tests/test_benign_popup.py python_runner/tests/test_safety.py
python -B -m pytest -q -p no:cacheprovider python_runner/tests/test_feed_swipe_smoke.py python_runner/tests/test_feed_session_smoke.py -k 'captcha or verification or popup_dismiss or baseline'
python -B -m compileall -q python_runner/core/classifier.py python_runner/flows/feed_swipe_smoke.py python_runner/flows/benign_popup.py
git diff --check
git status --short
```

Khi fixture hoặc tên test khác, thay lệnh bằng test selector thực tế; không báo “đã pass” nếu chưa có output mới.

## Artifacts và alert
- Alert phải giữ ảnh nguyên bản tại thời điểm phát hiện lỗi.
- Không chụp alert sau khi worker đã force-stop TikTok hoặc đưa máy về Home.
- Nếu lần chạy cũ chỉ còn ảnh Home, nói rõ không thể phục hồi ảnh Captcha gốc; không suy diễn từ ảnh Home.
- Lỗi live phải báo `[MÁY XX]`, artifact path/ảnh thật nếu có và trạng thái lock.

### One alert per machine per feed session
- Trong cùng một phiên, mỗi máy chỉ được phát **một** Telegram alert dừng phiên; retry, cron relaunch, worker exception và hard-watchdog timeout không được gửi alert thứ hai cho cùng máy.
- Dedupe phải chịu được process restart: không dùng biến memory hoặc UUID của từng run. Tạo session key ổn định từ logical day + ca/phiên (hoặc metadata slot/row timestamp đã chuẩn hóa), rồi claim theo `session_key + machine`.
- Claim phải được ghi atomically kiểu `O_CREAT|O_EXCL` vào runtime state dùng chung của logical day, đặt cao hơn từng thư mục `row-HHMMSS`; lần đầu claim thành công mới được gọi `send_farm_machine_alert`, claim trùng thì bỏ qua.
- Máy khác trong cùng phiên vẫn được alert; cùng máy ở phiên kế tiếp được alert lại đúng một lần. `reported_sessions` của watchdog chỉ dedupe báo cáo tổng kết, không thay thế producer-alert dedupe.
- Khi sửa call-chain, bọc **mọi** nhánh producer bằng cùng claim helper, tối thiểu gồm final child failure/manual-needed và hard outer watchdog timeout. Regression phải bao phủ hai run folder khác nhau trong cùng phiên, máy khác, và phiên kế tiếp.
- Không báo “đã hết spam” chỉ vì focused test pass: chạy full test file, `py_compile`, `git diff --check`, rồi tách baseline failure không liên quan khỏi regression mới.
- Chi tiết reproduction và claim-layout: `references/alert-dedupe-one-per-machine-session.md`.

### Preserve-scene cross-component invariant
`GIỮ HIỆN TRƯỜNG` is a cross-component invariant, not merely a feed-session cleanup flag. When a blocker must stop at the failure point, a later Launcher/Home screenshot is not proof that local cleanup ran:

1. Read the target-scoped JSONL around the terminal failure and verify `cleanup_close_all=skipped`, `preserve_blocker_screen=true`, and `preserve_blocker_screen` as the skip reason/error.
2. Compare the last verified in-flow package/screen with the later alert screenshot; distinguish TikTok's Home/For You tab from Android Launcher/Home.
3. Enumerate independent Home/force-stop actors in the actual execution tree: TTL/dead-owner reaper, recovery hard-stop, timeout/follow/upload hooks, cache jobs, and wrapper finalizers. Search both semantic calls and raw `keyevent 3`/`KEYCODE_HOME`.
4. Correlate timestamp, machine, serial, lock owner, and TTL. Mark each candidate `confirmed`, `excluded`, or `unproven`; do not blame local cleanup when its own log proves it was skipped.
5. In live work, capture evidence and stop. Do not rerun, probe, or patch the target without explicit user authorization. Keep the report short: exact error, last in-flow state, cleanup evidence, external candidates, and remaining uncertainty.

Detailed case evidence: `references/preserve-scene-cross-component-debugging.md`.

### Global log + UI XML evidence gate — all repo / all script
This gate applies to every script, flow, worker, recovery, scheduler, popup, login, upload, follow, feed, test fixture, and repo-level UI investigation—not only feed/profile verification.

**Cross-repository rule:** This is a global evidence workflow, not a rule limited to the TikTok consumer repo. When working in another repository, load the class-level `ui-evidence-first` skill as well and apply the same gate there. Do not claim that a repo-local `PROJECT_RULES.md` alone propagates to other repositories.

**Closeout/review rule:** A code-review `REJECT` is a hard stop. Fix every high/medium finding, rerun affected tests and compile/diff checks, then obtain a fresh review of the exact candidate tree. Do not commit or push while findings remain unresolved. Keep unrelated pre-existing dirty files unstaged and preserve the pre-task worktree baseline.

**Exact-tree review rule:** Before sending a diff to a reviewer, determine whether the candidate is staged, unstaged, already committed by a parallel worker, or mixed. Use `git diff HEAD -- <allowlist>` for the complete current candidate; use `git diff --cached` only for an intentionally staged candidate; never use only unstaged `git diff` when code may already be staged or committed. If the reviewer output says implementation is absent but the selected diff contained only docs, treat that as a review-input failure, not an approval or a code finding: regenerate the exact diff and rerun the review.

**Reviewer side — candidates move under concurrent writers:** an empty `git diff <paths>` while files are still dirty means they were staged → read `git diff --cached`; if HEAD moves mid-review (writer commits), rebind the verdict to the new SHA (`git show <sha> --stat`, compare per-file ± counts to the reviewed diff, pull and review only delta hunks, marker-check via `git grep -c <symbol> <sha> -- <path>`) and rerun focused tests on the final bytes before reporting; a failing run that raced a since-reverted transient mutation is not a regression — re-verify clean-vs-SHA and rerun. Working git-bash invocation: `PYTHONPATH=".;/d/Taadaa/tiktok-luot nuoi acc;/d/Taadaa/tiktok-luot nuoi acc/python_runner" python -B -m pytest -q -p no:cacheprovider ...`. Full timeline, heuristics, and commands: `references/closeout-review-concurrent-writer-20260823.md`.

**Concurrent-worker closeout rule:** Background workers can commit or alter the worktree without the foreground turn noticing. After every worker/background task and before any closeout claim, re-read `git status --short`, `git log -1`, `git rev-parse HEAD`, and `git rev-parse origin/<branch>`. Verify the commit's file list and SHA directly; do not create a duplicate commit or report a push based on an old status snapshot. If unrelated files are dirty, preserve them and report them as blockers/out-of-scope rather than staging broad `git add .`.

**Test-fixture rule:** Tests that mock `_capture_xml_text` must either create a complete exact XML+screenshot artifact or explicitly mock the artifact validator with a documented reason. Production code must never weaken the validator merely to satisfy legacy fixtures. Add regressions for missing paths, stale metadata, malformed XML, retry-path artifact replacement, and `xml_available=true` without real files; all must fail closed as `capture_artifact_missing`/`unproven`.

Session-specific review findings and verification pattern: `references/profile-verification-review-gate.md`.

Before any UI conclusion or recovery action:
1. Identify the exact run, target machine/device, account scope, timestamp, and artifact root; read `log.jsonl` around the failure, including the preceding and following events.
2. Resolve and open the exact `ui.xml` for the exact attempt. A directory path, `xml_available=true`, parser field, or folder name is not proof that XML was read.
3. Open the matching `screen.png`/screenshot from the same attempt. A later Home/Launcher image is not evidence of the earlier screen.
4. Compare XML + screenshot with the pre-action capture, last valid capture, and manifest/recovery metadata. Label every finding `confirmed`, `excluded`, or `unproven`.
5. If XML/screenshot is missing, truncated, malformed, path-invalid, or timestamp-mismatched, stop with `capture_artifact_missing`/`unproven`; never infer from `texts[0]`, one marker, stale capture, or terminal image.
6. Before tap/swipe/BACK/force-stop/HOME/recovery, read available evidence; after the action, recapture XML + screenshot and require a verified post-condition.

Implementation requirement: every script that captures UI for an error/blocker/mismatch must persist the exact XML and screenshot in the exact attempt artifact before parsing identity/classifying or cleaning up. `xml_available=true` is valid only when the exact XML exists and artifact status is complete. If the gate is not satisfied, do not conclude root cause or widen recovery/cleanup scope.

### Profile verification: mandatory artifact-first triage and identity evidence
Before making any conclusion about a profile mismatch, the agent MUST inspect the target-scoped JSONL and then open the exact final-attempt artifacts named by that log. Do not infer from `artifact_path` directory names or from a later Home screenshot.

### Code-fix regression pattern: import boundaries + fail-closed profile identity
When a recurring alert combines an undefined popup symbol with `profile verification navigation failed: TikTok focus lost`, treat it as two independently testable paths:

1. **Consumer import boundary:** locate the symbol definition and verify the failing consumer explicitly imports it; a symbol imported by a shared classifier/core module is not visible in `flows/<consumer>.py`. Reproduce the consumer handler path, not only a repository-wide grep.
2. **Navigation evidence:** after tapping Profile, require the same-capture selected `Hồ sơ`/`Profile` tab marker before parsing identity. Match the expected account only against the normalized username anchor from that Profile-confirmed XML; never let an arbitrary `@handle` or a display-name candidate self-prove navigation.
3. **Retry safety:** bounded lag retries must preserve the same Profile-marker requirement. Remove fallback retries that accept a username without the navigation anchor; otherwise `TikTok focus lost` can be masked as a successful identity match.
4. **Fixture contract:** regression XML fixtures must include the production anchor (`selected=true`, exact tab text, and representative bounds) whenever they expect success. Fixtures missing that anchor should assert manual-needed/fail-closed, not force production code to accept weaker evidence.
5. **Test diagnosis:** if a focused test fails after tightening evidence, inspect the exact failing test and call sequence. Update stale fixtures/assertions minimally when they encode the old unsafe behavior; do not weaken the production predicate merely to preserve an old call count or username field.

Focused reproduction, fixture shapes, and verification commands: `references/profile-verification-identity-and-import-regression-20260823.md`.

This is a hard workflow gate, not an optional check. A prior miss in this incident class came from reading parser output and artifact-directory metadata without opening the final XML tree; the resulting `Message` value was mistaken for account evidence. When the user corrects the agent to read the log/XML, treat that as a permanent process correction: acknowledge it, perform the evidence read immediately, and preserve the rule in this skill.

For this incident class, report concise Vietnamese facts: exact paths, timestamps, XML anchors/bounds/selected state, confirmed/excluded/unproven findings, and the next code change. Do not claim an artifact was inspected unless the file was actually opened; do not bury the finding under a long workflow explanation.

Required read order:
1. Read the target run `log.jsonl` around the terminal `verify_profile` event, including the immediately following cleanup event.
2. Resolve the exact `xml_path`/`screenshot_path`; if the log gives only a directory, enumerate it and locate `ui.xml` and `screen.png`.
3. Read the final-attempt XML tree and inspect the matching screenshot before stating which screen/account was present.
4. Compare that final capture with the last known-good preflight/profile XML and the last in-flow screen. Record evidence as `confirmed`, `excluded`, or `unproven`.
5. If the expected XML or screenshot is absent, report `capture_artifact_missing`/`unproven`; never fill the gap with a parser field such as `Message`, a stale capture, or a later Launcher screenshot.

The implementation contract: every profile verification capture must persist exact `ui.xml` and `screen.png`; `xml_available=true` is valid only when both files exist and status is complete.
Screencap on Android/Samsung may return 12-byte null when screen is asleep or framebuffer is locked: `_persist_profile_capture_artifacts` must retry 3 times with screen wake (`dumpsys power` + `input keyevent 224`).
Detecting Inbox/Message must use `_is_inbox_tab_selected_from_xml` (`selected="true"`), never scanning broad text across the screen.
Detailed reproduction and screencap/inbox invariant: `references/profile-verification-screencap-retry-and-inbox-guard-20260827.md` and `references/profile-verification-anchor-and-preserve-scene.md`.

### Phân biệt trigger lỗi với trạng thái cuối hiện trường
- `reason="verification marker detected"` là nhãn do classifier/safety map tạo ra; nó chỉ chứng minh **đã từng có marker ở bước phát hiện**, không chứng minh marker còn hiện trên ảnh cuối.
- Khi alert gắn verification nhưng ảnh hiện trường là Android Home/Launcher, phân loại terminal là **mất TikTok foreground / focus lost sau detection**. Không gọi đó là Captcha đang hiển thị và không suy đoán VPN chỉ từ biểu tượng status bar.
- Điều tra theo thứ tự: (1) ảnh/XML ngay tại detection, (2) focus package/activity và action sau detection, (3) ảnh terminal cuối. Chỉ kết luận Captcha/verification nếu evidence ở bước (1) hoặc (2) còn marker thật.
- **False-positive từ chữ "xác minh" trong Verified Badge:** Khi điều tra XML lỗi `verification marker detected`, luôn kiểm tra xem node có phải là icon/badge tích xanh (`content-desc="Huy hiệu đã xác minh"`, `@jsol.dreams`, verified brand/KOL profile) hay không trước khi kết luận nick bị dính challenge xác minh.
- Nếu chỉ còn ảnh Home, báo rõ mức chứng cứ: `trigger=verification marker` nhưng `terminal_state=launcher`; nguyên nhân crash/force-stop/cleanup chỉ là hypothesis cho tới khi có log hoặc capture trung gian.
- Tham chiếu quy trình và mẫu báo cáo: `references/alert-trigger-vs-terminal-state.md`.

## Account-switcher creator header rejection & fresh anchor recovery
Khi resolve switch anchor trong `verify_and_switch_profile` / `_find_sticky_profile_header`:
1. **Chặn tap nhầm Profile/Creator:** Khi identity đã biết, nếu node anchor là một `@handle` khác với username hiện tại, hoặc text generic không có identity/resource semantic, bắt buộc trả về `None` (fail-closed). Tuyệt đối không để `@creator_user` trở thành switch anchor.
2. **Recapture anchor sau `BACK`:** Khi gửi `BACK` để hạ overlay/keyboard, phải recapture XML tươi và resolve lại `retry_anchor` mới thay vì bấm mù vào tọa độ cũ.
Reference: `references/account-switcher-creator-header-rejection-20260824.md` và `references/account-switcher-fresh-anchor-after-back.md`.

## Tài liệu hỗ trợ
- `references/sponsored-check-atx-session-unavailable-20260824.md`: Chẩn đoán và quy trình khôi phục nhanh lỗi `capture-invalid: ATX_SESSION_UNAVAILABLE` tại bước `sponsored_check` do UiAutomator stub bị OOM ngắt ngầm khi màn hình TikTok feed vẫn bình thường.
- `references/powershell-process-launch-time-vs-commit-time-triage-20260824.md`: Quy trình đối soát mốc thời gian chụp màn hình/taskbar clock vs git commit timestamp để giải thích hiện tượng tiến trình PowerShell cũ vẫn chạy trong RAM sau khi đã sửa code.
- `references/account-switcher-drawer-launcher-crash-recovery-20260824.md`: Cơ chế nhận diện và tự động relaunch TikTok + re-navigate Profile khi app bị crash văng về Launcher trong lúc mở drawer đổi tài khoản (Account Switcher).
- `references/watchdog-session-cadence-and-max-swipes-cap-20260824.md`: Quy chuẩn watchdog báo cáo gom theo 3 Phiên/Ca (chống spam từng sub-batch 15p), giải quyết triệt để lỗi lệch hằng số FEED_SESSION_MAX_SWIPES = 15 vs runner cap 15, và tính lượt vuốt Fast Swipe vào tổng swipe.
- `references/upload-hook-tik-workbook-mapping-and-config-requirement-20260824.md`: Nguyên tắc mapping 1-1 giữa ca nuôi và workbook Tik (Row 1->Tik1, Row 2->Tik2...), yêu cầu bắt buộc file config.example.yaml trong repo Tiktok-video, và phân biệt alert thiết bị vs config-error.
- `references/all-repo-fail-closed-vpn-preflight-standardization-20260824.md`: Chuẩn hóa bắt buộc check VPN (require_android_vpn) fail-closed trên toàn bộ các repo automation farm (Tiktok-video, tiktok-luot nuoi acc, follow, login, f2a, reg, gmail, hotmail...).
- `references/profile-guard-launcher-focus-recovery-20260824.md`: Cơ chế tự động hồi phục launcher focus loss (relaunch TikTok + re-navigate profile) ngay trong `_maybe_handle_profile_add_phone_guard` khi TikTok bị crash văng về Launcher lúc mở menu đổi tài khoản trên thiết bị S7.
- `references/profile-switcher-launcher-crash-unknown-state-20260824.md`: Phân tích lỗi crash về Launcher khi mở menu đổi tài khoản TikTok trên Galaxy S7, dẫn đến classifier gán nhầm 'unknown TikTok state' thay vì kích hoạt launcher auto-relaunch recovery.
- `references/feed-session-post-run-watchdog-report-20260824.md`: Kiến trúc watchdog báo cáo kết quả phiên nuôi TikTok (chỉ máy success/fail) và quy trình kiểm tra tiến độ/đợt sóng (wave) trong các ca nuôi tự động.
- `references/activity-unavailable-webview-back-recovery-20260824.md`: Cơ chế nhận diện popup/webview 'Hoạt động không có sẵn' (Activity not available) và quy tắc bắt buộc dùng KEYCODE_BACK thay vì tap nút OK để thoát triệt để về Feed video.
- `references/in-feed-friend-suggestion-and-repost-matcher-20260824.md`: Phân tích lỗi dừng phiên do thẻ gợi ý bạn bè in-feed (Bạn bè với / Follow lại), fix false-match của repost_sheet_close với `:id/title` tác giả, và chuẩn hóa exact attribute xpath cho `find_by_gem_xpath`.
- `references/fast-swipe-deep-inspect-cadence-and-deadline.md`: Thiết kế cơ chế lướt nhanh (Fast Swipe 3-6s không XML) xen kẽ kiểm tra sâu (Deep Inspect 20s có dump XML) ngẫu nhiên 2-4 video để tối ưu hành vi người thật, bù tỷ lệ Like 35% tại nhịp XML và triệt tiêu lỗi max_duration_seconds exceeded.
- `references/in-feed-ad-popup-terms-false-positive-20260824.md`: Phân tích lỗi false-positive `unexpected popup/dialog marker detected` do từ khóa "Đóng" trong `popup_terms` của classifier bắt nhầm video quảng cáo in-feed, và lý do safety guard dừng phiên trước khi swipe recovery kịp chạy.
- `references/infeed-ad-popup-marker-false-positive-20260824.md`: Phân tích lỗi false positive `manual-needed:popup` do chữ "Đóng"/"Tìm hiểu thêm" trên video quảng cáo in-feed kích hoạt classifier và dừng phiên trước khi swipe recovery kịp chạy; nguyên tắc cấm suy diễn gesture bị chặn khi chưa có evidence.
- `references/max-duration-before-navigate-profile-triage-20260824.md`: Chẩn đoán và xử lý lỗi 'run plan max_duration_seconds exceeded before navigate profile' do cạn kiệt deadline 1800s khi kết thúc chuỗi vuốt video trên máy Galaxy S7.
- `references/in-feed-friend-suggestion-card-follow-back-20260824.md`: Phân tích và xử lý lỗi dừng phiên do thẻ gợi ý bạn bè in-feed ('Bạn bè với...', 'Follow lại') bị classify nhầm thành modal popup và rule repost_sheet_close bắt nhầm :id/title.
- `references/interactive-ad-modal-swipe-interception-20260824.md`: Phân tích nguyên nhân Interactive In-feed Ad Modal (Tìm hiểu thêm + Đóng) chặn cử chỉ vuốt dọc (gesture interception), cơ chế cứu kẹt _swipe_recovery_on_stuck thất bại do modal không trôi và bẫy 2 lần liên tiếp ManualReasonGuard.
- `references/in-feed-friend-suggestion-card-misclassification.md`: Phân tích lỗi dừng phiên false positive do thẻ đề xuất bạn bè in-feed ("Bạn bè với...", nút "Không quan tâm"/"Follow lại") bị classifier và XPath repost_sheet bắt nhầm thành popup kẹt.
- `references/contact-suggestion-caption-subword-misclick-20260824.md`: Chẩn đoán lỗi bắt nhầm feed For You thành popup gợi ý follow do từ khóa 'đề xuất', bấm nhầm vào caption 'đóng gói' do trùng từ 'đóng', và quy tắc ưu tiên lướt qua thẻ quảng cáo CTA thay vì tìm nút đóng.
- `references/swipe-recovery-focused-package-and-usable-screens.md`: Quy tắc fail-closed cho `_swipe_recovery_on_stuck`, bắt buộc whitelist `usable_screens` (`*FEED_TYPES`, `home`, `profile`) và đối chiếu `focused_package == tiktok_package` để chặn nhận nhầm app ngoài (Danh bạ/Dialer) là đã qua kẹt.
- `references/hard-outer-watchdog-upload-hook-buffer-20260824.md`: Phân tích lỗi false-abort hard outer watchdog timeout (15.1m > 15.0m) do hạ trần timeout thiết bị xuống 600s không đủ buffer cho upload hook (tối đa 15 phút), và quy chuẩn khôi phục DEFAULT_DEVICE_TIMEOUT_SECONDS = 1500s (watchdog 30 phút).
- `references/hard-outer-watchdog-queue-time-false-alarm-20260824.md`: Phân tích lỗi false-alarm `hard outer watchdog timeout exceeded` do tính thời gian chờ hàng đợi ThreadPoolExecutor (max_workers 40 trên 72 máy) thay vì thời gian chạy thực, và giải pháp worker_wrapper ghi nhận start_mono khi worker bắt đầu chạy.
- `references/swipe-recovery-third-party-app-focus-guard-20260824.md`: Phân tích và khắc phục lỗi `_swipe_recovery_on_stuck` false positive gán success khi đang ở app thứ 3 (như Danh bạ/Dialer), bắt buộc whitelist usable feed và kiểm tra package TikTok.
- `references/threadpool-queue-stagger-watchdog-false-fail-20260824.md`: Chẩn đoán và xử lý lỗi false-fail `hard outer watchdog timeout exceeded` do mốc `time.monotonic()` tính từ lúc đưa job vào hàng đợi `ThreadPoolExecutor` thay vì lúc worker con thực sự thực thi, khiến các máy wave 2 bị tính oan thời gian xếp hàng.
- `references/launcher-recovery-profile-reset-and-feed-confirmed-20260824.md`: Bằng chứng Preflight switch tài khoản thành công 100% (XML + Screenshot), hiện tượng session rollback về tài khoản mặc định (Slot 1) khi bị force-stop/relaunch giữa phiên trên TikTok Android, và fix bug đối số row vs attempt trong _is_feed_confirmed.
- `references/account-update-prompt-dismiss-contract-20260824.md`: Xử lý lỗi TypeError `_row_from_attempt() got an unexpected keyword argument 'artifact_prefix'` khi dismiss popup cập nhật tài khoản (account_update_prompt) và chuẩn hóa hợp đồng gọi _row_from_attempt / partial log.
- `references/organic-feed-follow-rate-disable-and-trust-recovery-20260824.md`: Phân tích nguyên nhân nhả follow hàng loạt, quy tắc reset cooldown phạt 5-7 ngày của TikTok, tắt 0% DEFAULT_FEED_FOLLOW_RATES trên toàn bộ các feed và quy trình hồi phục trust score qua đăng video.
- `references/contact-suggestion-caption-misclick-recovery-20260824.md`: Xử lý lỗi bắt nhầm feed For You (tab Đề xuất) thành contact_follow_suggestion popup, chống bấm nhầm vào caption video (từ 'đóng gói' vs 'đóng') và quy tắc vuốt lướt qua CTA quảng cáo.
- `references/swipe-recovery-third-party-focus-loss-20260824.md`: Chẩn đoán lỗi dừng phiên 'swipe recovery passed stuck screen' do app ngoài (Danh bạ/Dialer/Outlook) cướp focus làm swipe recovery đánh giá nhầm trạng thái qua màn kẹt khi thiếu kiểm tra focus package.
- `references/cron-upload-collision-and-watchdog-architecture-20260823.md`: Xung đột giữa cron feed và manual batch upload, kiến trúc watchdog 2 lớp chống treo (hard timeout 30' per-device + runner lease auto-reap 90') và fix entrypoint upload hook scripts.tiktok_workflow.
- `references/cross-repo-upload-hook-and-outer-watchdog-20260823.md`: khắc phục lỗi gọi module upload `scripts.tiktok_workflow` trong `tiktok-video` và chi tiết kiến trúc 2 lớp watchdog chống treo batch/lease.
- `references/batch-outer-watchdog-and-lease-reap-architecture-20260823.md`: kiến trúc 2 lớp chống treo cron feed (hard outer watchdog 30 phút từng future trong ThreadPoolExecutor + auto-reap stale runner lease sau 90 phút).
- `references/feed-session-keyboard-capture-overhead-and-timeout.md`: Chẩn đoán hiện tượng lặp lại capture_screenshot/dump_ui_xml do XiaoWei keyboard false positive (mInputShown=true) dẫn đến cạn kiệt deadline 1500s.
- `references/navigation-launcher-focus-auto-relaunch-20260823.md`: cơ chế tự động relaunch TikTok khi gặp Launcher focus loss trong bước điều hướng/preflight và lý do cấm reboot định kỳ trước mỗi phiên.
- `references/navigation-tap-post-focus-fail-closed-20260823.md`: nguyên tắc fail-closed kiểm tra focus sau tap navigation, và lý do kỹ thuật cấm tự ý force-stop/relaunch ở hàm tap cấp thấp.
- `references/xwkeyboard-false-positive-and-video-budget-adjustment-20260823.md`: xử lý lỗi XiaoWei keyboard (`com.android.xwkeyboard`) dumpsys false-positive gây lặp chụp ảnh/dump XML sau mỗi swipe và điều chỉnh budget 8–11 video / timeout 1800s.
- `references/auto-fill-name-nickname-recovery-20260823.md`: quy trình tự động phát hiện `+ Thêm tên` trên Profile, gọi `social_reg_v1.fill_name` đặt tên hiển thị từ email và re-capture tiếp tục lướt feed.
- `references/profile-verification-scrolled-grid-mismatch-20260823.md`: phân tích lỗi false alarm profile mismatch do màn hình Hồ sơ bị cuộn xuống lưới video làm ẩn node @username và giải pháp re-tap tab/scroll up.
- `references/account-switcher-not-open-diagnosis.md`: chẩn đoán và xử lý lỗi `account-switcher-not-open` do nick active sẵn và màn hình Profile cuộn khuất header @username trước khi preflight.
- `references/captcha-close-x-recovery.md`: incident pattern, classifier precedence, fixture pair và safety boundary cho Captcha có/không có close-X.
- `references/tiktok-end-of-day-cache-clear-and-cron-isolation-20260823.md`: quy tắc dọn cache TikTok an toàn qua Deep Link (`snssdk1180://clean_cache`) / Widget Home, cấm pm clear, và lịch cron 04:00 AM.
- `references/storage-management-overlay-recovery-20260823.md`: cơ chế tự động thoát màn hình 'Giải phóng dung lượng' (Snssdk clean_cache / Storage management overlay) về Trang chủ bằng KEYCODE_BACK trong Benign Popup Registry.
- `references/story-quick-reaction-keyboard-overlay-recovery-20260823.md`: cơ chế tự động phân loại `story_reply_terms` sang `manual-needed:popup` và hạ bàn phím/thoát quick reaction overlay về Feed qua `KEYCODE_BACK` 2 lần trong Benign Popup Registry (Priority 76).
- `references/story-quick-reply-keyboard-feed-stuck-20260823.md`: chẩn đoán và quy trình thoát kẹt khi gặp overlay Story Quick Reaction / Nhắn tin nhanh bung bàn phím ảo che khuất feed.
- `references/uiautomator-monkey-focus-loss-feed-stuck-20260823.md`: phân tích nguyên nhân `reset_atx_agent` gọi monkey kích hoạt `com.github.uiautomator.MainActivity` lên foreground gây mất focus TikTok và kẹt swipe recovery.
- `references/uiautomator-background-start-denied-cascade-20260823.md`: phân tích lỗi dây chuyền từ ATX 502/empty hierarchy rơi xuống shell uiautomator dump bị OOM kill 137 và kích hoạt recovery ladder cũ `am startservice` background denied.
- `references/tiktok-focus-lost-oom-ram-vs-worker-triage-20260823.md`: phân tích bản chất OOM RAM khi lướt feed trên S7 vs dọn cache ROM định kỳ, và phân biệt tải worker PC vs thiết bị.
- `references/tiktok-focus-lost-launcher-recovery-20260822.md`: chẩn đoán và khắc phục lỗi `TikTok focus lost` khi app bị văng về màn hình Launcher trên thiết bị Samsung Galaxy S7.
- `references/prepare-tiktok-focus-retry-launch-20260822.md`: phân tích và xử lý lỗi `prepare-tiktok failed to focus TikTok after launch` bằng cơ chế retry monkey launch.
- `references/third-party-app-focus-loss-profile-mismatch-20260822.md`: chẩn đoán lỗi false alarm `profile account mismatch and profile username/display name anchor is unavailable` do app thứ 3 (như Outlook) bất ngờ chiếm focus đè lên TikTok profile.
- `references/atx-session-unavailable-swallowed-focus-lost-20260823.md`: lỗi `ATX_SESSION_UNAVAILABLE` bị `return None` thay vì raise trong `dump_current_ui` → flow tiếp tục → phantom "TikTok focus lost"; cách phân biệt với UIAutomator/launcher pattern; fix commit 52a8bc9.

## Pitfalls
- **`UIElement.bounds` vs `parse_bounds` và Chuỗi Action Fallback trong Popup Dismisser:**
  - Trong `automation_core.ui`, `UIElement.bounds` đã là tuple `(left, top, right, bottom)` và `UIElement.center` là tuple `(cx, cy)`. Nếu truyền `el.bounds` vào `parse_bounds(val)` (hàm mong đợi string `"[x1,y1][x2,y2]"`) sẽ gây `TypeError: expected string or bytes-like object, got 'tuple'` làm handler dismiss bị crash và fallback sang Back key hoặc fail. Bắt buộc ưu tiên đọc trực tiếp `el.center`.
  - **Pitfall `DeviceContext` không có `ctx.tap` & `_perform_click_target` helper**: Đối tượng `ctx` (`DeviceContext`) trong runner chứa `ctx.adb` (gọi `ctx.adb.shell(["input", "tap", str(cx), str(cy)])`), không có sẵn phương thức `ctx.tap()`. Cần dùng helper `_perform_click_target(ctx, tap_pt)` để wrap an toàn try-except từng kênh (kiểm tra `callable` + kết quả trả về không False) theo thứ tự: `ctx.tap` ➔ `ctx.adb.shell(["input", "tap", ...])` ➔ `ctx.actions.tap` ➔ fallback `send_device_back_key(ctx)`. Không được gán `action_performed = True` khi chưa có kênh nào tap thành công.
  - **Hỗ trợ toàn diện các định dạng bounds**: Luôn kiểm tra lần lượt: `el.center` ➔ bounds dạng tuple/list `(l, t, r, b)` ➔ bounds dạng string `"[l,t][r,b]"` qua `parse_bounds()` để tương thích với tất cả các parser UIElement/XML.

  ```python
  def _perform_click_target(ctx: Any, tap_pt: tuple[int, int]) -> bool:
      """Helper thực hiện tap theo thứ tự ưu tiên các channel trên context và trả về True nếu tap thành công."""
      if hasattr(ctx, "tap") and callable(ctx.tap):
          try:
              res = ctx.tap(tap_pt[0], tap_pt[1])
              if res is not False:
                  return True
          except Exception:
              pass
      if hasattr(ctx, "adb") and hasattr(ctx.adb, "shell") and callable(ctx.adb.shell):
          try:
              res = ctx.adb.shell(["input", "tap", str(tap_pt[0]), str(tap_pt[1])])
              if getattr(res, "ok", True):
                  return True
          except Exception:
              pass
      if hasattr(ctx, "actions") and hasattr(ctx.actions, "tap") and callable(ctx.actions.tap):
          try:
              res = ctx.actions.tap(tap_pt[0], tap_pt[1])
              if res is not False:
                  return True
          except Exception:
              pass
      return False
  ```
- **Launcher Focus Recovery tại Profile Guard:** Khi TikTok bị văng về Launcher (`com.sec.android.app.launcher`) lúc mở menu đổi nick hoặc duyệt identity, `_maybe_handle_profile_add_phone_guard` tự động relaunch và re-navigate về Hồ sơ. Sau relaunch, **bắt buộc kiểm tra `detected_screen == "profile"`** trước khi trả `dismissed` để flow tiếp tục switch nick an toàn; tuyệt đối không chấp nhận các màn hình feed/home khác làm sai lệch tọa độ switch anchor tiếp theo.
- **`FEED_SESSION_MAX_SWIPES` vs `SESSION_MAX_SWIPES_CAP` misalignment:** Hằng số `FEED_SESSION_MAX_SWIPES` trong `multi_machine_feed_session.py` bắt buộc phải $\le 15$ (khớp với `SESSION_MAX_SWIPES_CAP = 15` trong `run_tiktok.py` và `feed_swipe_smoke.py`). Nếu đặt $> 15$ (ví dụ 16), runner sẽ fail-closed ngay tại validation với lỗi `feed-session-smoke requires 1 <= --max-swipes <= 15`, làm fail `config-error` hàng loạt máy ngay khi khởi động. Chú ý các lần merge/rebase code từ worker khác không được vô tình ghi đè lại hằng số 16.
- **Upload Hook `config.example.yaml` Fallback Requirement:** Khi kích hoạt upload hook sau phiên cuối của ca (`_run_upload_hook`), repo `D:\Taadaa\Tiktok-video` bắt buộc phải có `config.example.yaml` (hoặc `config-machine-<m>.yaml`). Nếu thiếu file cấu hình mẫu này, subprocess upload runner (`scripts.tiktok_workflow`) sẽ exit code 1 với lỗi `Config error: Config file not found: ...\config.example.yaml` và làm toàn bộ lượt upload bị fail.
- **Quy tắc Nuôi Row nào Đăng Video Tik đó & Chu kỳ Ca:** Hệ thống map tự động 1-1 giữa ca nuôi và workbook upload: Ca nuôi Row 1 -> upload `Tik1.xlsx`, Row 2 -> `Tik2.xlsx`, Row 3 -> `tik3.xlsx`, Row 4 -> `Tik4.xlsx`. Mỗi ca gồm 3 phiên lướt feed; chỉ khi kết thúc Phiên 3/3 (phiên cuối ca) thì hệ thống mới kích hoạt upload video, các phiên 1 và 2 trước đó chỉ thuần lướt nuôi acc.
- **Phân biệt Lỗi Config vs Lỗi Thiết bị trong Báo cáo Fail:** Khi có máy báo fail trong summary/watchdog nhưng không thấy bắn ảnh alert về nhóm `Farm Alerts`: cần kiểm tra xem lỗi xảy ra ở bước nào. Nếu lỗi là `config-error` (như lệch max-swipes, thiếu config.example.yaml) thì tiến trình bị chặn trước khi kết nối thiết bị nên không có ảnh UI alert; alert bắn ảnh màn hình chỉ kích hoạt khi máy đã tương tác trực tiếp với app TikTok trên thiết bị thật.
- **Quy tắc chu kỳ báo cáo Watchdog Nuôi Acc (Cron):** Farm nuôi chạy chuẩn 3 Ca/ngày, 3 Phiên/Ca. Script watchdog báo cáo Telegram (`feed_session_watchdog.py`) bắt buộc gom kết quả toàn bộ máy theo từng **Phiên hoàn tất** (`Ca X - Phiên Y/3`) và chỉ gửi đúng 1 thông báo tổng kết khi kết thúc phiên. Tuyệt đối KHÔNG gửi theo từng tick runner 15 phút hoặc từng sub-batch nhỏ gây spam chat.
- **Fast Swipe (Lướt nhanh không dump XML) vẫn tính vào tổng swipe:** Các lượt vuốt nhanh (2–4 video không dump XML) vẫn tăng biến đếm `swipe_count` đều đặn trong vòng lặp và được gom đầy đủ vào `total_swipes_completed` / `actual_swipe_count` khi `aggregate_feed_swipe_results()` tổng kết phiên.
- **Chuẩn hóa Check VPN Fail-Closed All-Repo:** Toàn bộ các repo automation (`tiktok-luot nuoi acc`, `Tiktok-video`, `tiktok-follow`, `tiktok-log-in`, `tiktok-add-bao-mat-f2a`, `Tiktok_Reg`, `Hotmail`, `register gmail`, `add mail khoi phuc`) đều bắt buộc thực hiện kiểm tra `require_android_vpn(required=True)` trước khi chạm vào app hoặc thực hiện đăng bài/thao tác mạng. Nếu mất VPN $\rightarrow$ fail-closed ngay lập tức (không chạy mạng trực tiếp/IP máy thật).
- **Chống Trùng Lịch Nuôi Acc vs Reg Gmail/TikTok Ban Đêm (00:00):** Cơ chế Device Lock (`machine_X.lock.json` dưới `.codex/device-locks`) bảo vệ chống giẫm chân chéo giữa các batch khác nhau. Khi batch Reg chạy lúc 00:00, nó tự động bỏ qua (skip) các máy đang bận chạy ca nuôi/upload video mà không cướp máy hay đè tiến trình.
- **TikTok In-Feed Suggestion Cards vs Bare Resource-ID:** Khi bắt thẻ gợi ý bạn bè (`follow_back_suggestion`), chỉ match exact `text` hoặc `content-desc` mang nghĩa Follow (`Follow lại`, `Follow back`, `Theo dõi lại`). Tuyệt đối không dùng bare resource-id (như `:id/ct3`) đứng độc lập vì ID obfuscated có thể bị tái sử dụng trên các button/modal khác và gây false-positive tap mù.
- **Repost Sheet Close Locale & Single-Pass:** Rule `repost_sheet_close` bắt buộc phải match exact text/content-desc đa ngôn ngữ (`Bài đăng lại`, `Repost`, `Reposts`), cấm dùng bare resource-id `:id/title` (trùng tên tác giả video feed), và bắt buộc đặt `loop=False` để không tap nhầm nút Close của các container nền bên dưới.
- **In-feed Ad `Đóng`/`Tìm hiểu thêm` False Positive:** Từ khóa generic như `"Đóng"` / `"Close"` trong `popup_terms` của classifier sẽ bắt nhầm các video quảng cáo/thẻ tương tác in-feed và gán nhãn `manual-needed:popup`. Khi đó `ManualReasonGuard` kích hoạt dừng khẩn cấp trước khi `_swipe_recovery_on_stuck` kịp thử vuốt qua. Tuyệt đối không suy đoán gesture vuốt bị chặn nếu log chưa chứng minh có lệnh swipe thất bại. Khi có tab Feed (*Đề xuất/Bạn bè/Đã follow*), phải loại bỏ `_close_terms` khỏi `popup_terms` để phân loại về `for-you`/`sponsored` và lướt tiếp bình thường.
- **`ThreadPoolExecutor` Queue Latency vs Hard Outer Watchdog:** Khi chạy batch nhiều máy với `max_workers < len(machines)`, các máy đợt 2+ phải xếp hàng chờ trong hàng đợi. Nếu mốc `time.monotonic()` tính từ lúc `executor.submit()`, thời gian xếp hàng sẽ bị cộng dồn vào thời gian chạy gây false-fail `hard outer watchdog timeout exceeded` khi máy đang lướt feed bình thường. Bắt buộc dùng `worker_wrapper` để ghi nhận `start_mono` ngay khi worker con bắt đầu chạy thực tế trên thread và chỉ tính timeout khi worker đã active.
- **`_is_feed_confirmed` và `detected_screen_from_attempt` argument shape:** `_capture_step()` trả về dictionary cấp `row` (chứa `status`, `detected`, `attempts=[...]`). Các helper như `_is_feed_confirmed()` và `detected_screen_from_attempt()` mong đợi `attempt` dict (chứa `detected_screen`, `image_selected_top_tab`, `home_selected`). Khi kiểm tra kết quả từ `_capture_step` (như trong `_recover_post_swipe_launcher_focus`), bắt buộc phải đọc từ `recaptured.get("attempts")[-1]` hoặc hỗ trợ cả 2 cấp để tránh false-negative recovery khiến log ghi nhận `feed not confirmed after launcher recovery` sai.
- **Mid-session Relaunch Account Rollback:** Khi TikTok bị `force-stop` và launch lại qua `monkey` giữa phiên (ví dụ do launcher focus recovery), app có thể rollback về tài khoản mặc định (Slot 1) nếu SharedPreferences/SQLite chưa flush kịp session phụ vừa switch ở preflight. Bất kỳ cơ chế force-stop nào giữa phiên đều phải kiểm tra lại profile identity trước khi tiếp tục chuỗi swipe.
- **Nested focus package in capture `extra`:** `_is_launcher_focus_loss` (và các safety/classification helper tương tự) bắt buộc phải đọc `focus_package`/`focused_package` từ cả top-level dict VÀ `extra` sub-dict (`row.get("extra", {})`). Các capture attempt từ `_capture_step` đóng gói focus vào `extra`, nếu helper chỉ đọc top-level sẽ bị bỏ sót trạng thái `com.sec.android.app.launcher` hoặc `com.android.systemui`, khiến auto-relaunch bị bỏ qua và flow fail oan `TikTok focus lost`.
- **`com.android.xwkeyboard` daemon dumpsys false-positive:** Daemon bàn phím XiaoWei trên các box/máy farm luôn trả về `mInputShown=true` trong `dumpsys input_method` dù không có bàn phím UI. Điều này kích hoạt `keyboard_cleanup` ở 100% video, làm nhân đôi/ba số lần chụp ảnh và dump XML gây nghẽn kéo dài phiên quá 25 phút. Đã xử lý bằng cách bỏ qua `xwkeyboard` trong `parse_input_method_state` tại `automation-core`.
- **`ATX_SESSION_UNAVAILABLE` bị nuốt trong `dump_current_ui`:** Nếu exception này không nằm trong `terminal_recovery`, code `return None` và flow tiếp tục lên step tiếp theo (ví dụ `tap_profile`) trong khi ATX đã chết → khoảng trống ~2 phút trong log → "TikTok focus lost" oan. Fix: thêm `exc.code == "ATX_SESSION_UNAVAILABLE"` vào điều kiện `terminal_recovery` trong `feed_swipe_smoke.py`. **Dấu hiệu nhận diện:** khoảng trống lớn (>1 phút) trong log + `ATX_SESSION_UNAVAILABLE result=skipped` ngay trước khoảng trống + ảnh hiện trường là TikTok feed bình thường (không phải launcher hay UIAutomator). Xem `references/atx-session-unavailable-swallowed-focus-lost-20260823.md`.
- **ATX Stub "Already Started" Pitfall & Fast Swipe Launcher Escalation (`sponsored_check`):** Chi tiết lỗi `atx-agent curl POST /uiautomator` trả về `Already started <nil>` nhưng không thực sự spawn lại process stub `com.github.uiautomator` (cần trigger bằng `monkey -p com.github.uiautomator 1`), kết hợp với bug thứ tự gọi `_sponsored_present` dump XML ngay khi vừa rơi xuống Deep Inspect từ Launcher làm nổ `ATX_SESSION_UNAVAILABLE`. Chi tiết: `references/atx-stub-already-started-and-fast-swipe-launcher-collision-20260824.md`.
- Sửa classifier nhưng quên flow branch vẫn coi `manual-needed:verification` là block.
- **Authoritative Machine-Serial Mapping Location:** Nguồn mapping chuẩn máy và serial trên farm Taadaa là `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (dùng hàm `load_feed_session_accounts(wb, machines, row_index)` từ `core.feed_session_workbook`), không tìm kiếm ở các file cấu hình rời rạc hay yêu cầu user cung cấp lại khi cần target live máy.
- Đổi tên screen/reason làm hỏng test và downstream summary ngoài scope.
- Dùng generic `detect_verification_dismiss()` quá sớm khiến quick-security hoặc verify-email bị phân loại sai.
- Đọc artifact sau cleanup rồi kết luận đó là màn hình nguyên nhân.
- Tự chạy multi-machine sau khi patch chỉ vì test local pass.
- **Nested config `None` trap:** `mapping.get("section", {}).get("key")` vẫn nổ nếu `section` tồn tại nhưng có giá trị `None`. Trước khi đọc config trong batch/child flow, chuẩn hóa từng section bằng `section = mapping.get("section"); section = section if isinstance(section, dict) else {}` hoặc helper typed tương đương. Thêm regression test với `safety: None` và `timeouts: None`; test phải chứng minh flow trả về config/manual result thay vì làm mất target với `'NoneType' object has no attribute 'get'`. Bao phủ parent preflight, child-context construction và mọi hook đọc cùng config.
- **JsonlLogger keyword `result` requirement:** Mọi lệnh gọi `ctx.logger.log(...)` / `logger.log(...)` bắt buộc phải có keyword `result="..."` (kể cả trong block `except Exception:`). Tuyệt đối không được bỏ sót `result` trong các nhánh `except` / error-handling, nếu không `JsonlLogger.log()` sẽ quăng `TypeError: missing 1 required keyword-only argument: 'result'` làm crash dừng phiên oan toàn bộ máy.
- **Trùng lặp hàm giữa các module/helper:** Trong `social_reg_v1.py` và các consumer scripts, chú ý không định nghĩa trùng lặp hàm (như `make_tiktok_nickname_candidates`) gây ghi đè logic cũ lên hàm chuẩn mới. Khi import helper giữa các repo (`Tiktok_Reg` <-> `tiktok-luot nuoi acc`), kiểm tra sự đồng nhất của parameter và behavior.
- **`_row_from_attempt` keyword argument contract:** Hàm `_row_from_attempt()` trong `feed_swipe_smoke.py` nhận keyword-only: `step`, `action`, `expected`, `swipe_count`, `attempt`, `expected_package`, `require_feed`. Tuyệt đối không truyền `artifact_prefix` vào `_row_from_attempt()` (phải truyền `expected_package=str(ctx.config.get("tiktok_package", ...))`). Truyền sai keyword argument gây `TypeError` crash runtime dừng phiên feed hàng loạt máy.
- Khi alert chỉ có exception text mà thiếu traceback, không khẳng định được dòng gây lỗi từ ảnh. Lần theo toàn call chain, tìm mọi nested `.get()` ở execution path, rồi tạo repro offline trước khi sửa; không rerun live chỉ để “xem có hết không”.

### Config normalization regression pattern
For `multi-machine-feed-session` and similar batch flows, treat YAML/JSON sections as untrusted input even when the top-level config is a dict. A present-but-null section is distinct from a missing section under Python `dict.get(default)`. Normalize before chained access, keep the behavior fail-closed, and preserve per-machine artifacts/status rows. The focused regression should exercise the same entrypoint that emitted the alert, not only the helper in isolation. See `references/nested-config-none-regression.md`.

**Boundary-first checklist:** inspect the whole path `CLI/config loader → merged config → DeviceContext → batch preflight → child context → hooks`; a flow-local guard is insufficient if the entrypoint or context dereferences the same section first. Test `safety: null` and `timeouts: null` at both the CLI/context boundary and direct flow/child construction. After worker edits, re-check `git status`, `git diff --name-only`, and the pre-task dirty baseline before reporting completion; never let a fix or worker overwrite unrelated user changes. Separate pre-existing test failures from the new regression and report both counts.

See `references/nested-config-none-regression.md` for the offline reproduction and verification recipe.
