---
name: tiktok-feed-session-management
description: Skills for managing TikTok feed session, tab distribution, watchdog reporting, and farm sync operations
platforms: [windows, linux]
tags: [tiktok, feed-session, watchdog, farm-automation, tab-switching]
version: 1.0.0
author: Hermes Agent
---

## Watchdog Upload Status Taxonomy & Triage
When interpreting upload metrics in `feed_session_watchdog` reports (e.g. `Đang dưỡng sinh`, `Khác`, `Hết video/Cần cào`):
- `Đang dưỡng sinh`: Normal organic rest policy (~33% farm), no upload/follow attempted.
- `Khác`: Safe-skips; most commonly `missing_account_id` because column C (`ID`) in `Tik<row>.xlsx` is empty (`None`), or cooling/age gates. Inspect the target `Tik<row>.xlsx` directly.
- `Hết video/Cần cào`: `video_not_rendered` where `next_video.mp4` is missing or 0 bytes under `media_root/folder_video`.
- See `references/watchdog-feed-upload-status-taxonomy.md` for complete gate logic and recovery actions.
- See `references/watchdog-report-formatting-and-dual-sync.md` for dual-location deploy sync, report block refactor pitfalls, and AST regression tests.
- See `references/watchdog-follow-reconcile-and-cluster-triage.md` for:
  * Mandatory per-machine follow breakdown (never report aggregate-only `+20 Khớp 100%` when individual machines differ).
  * Categorized feed follow tiers and naming conventions (Hồi phục 1 & Hồi phục 2, released follow categories, and dashboard KPI card interactivity & active highlight invariant).
  * Categorized feed failure reporting (always split USB/ADB drop vs Wi-Fi/Proxy drop vs App error; never report a monolithic `Fail (N)` list).
  * Cross-cluster video path and Remote Execution rules (Admin storage is local to Admin-PC; never inspect Admin path locally on Kibe).
  * Anti-false-claim closeout discipline (never report a fix as completed if it was unstaged/dropped to satisfy closeout review).
- See `references/unconditional-dismiss-feed-follow-suggestions.md` for invariant blocking all follow actions on in-feed suggestion cards and popups (unconditional dismiss "Không quan tâm").
- See `references/farm-cron-schedule-stagger-and-persona-cadence.md` for 160-machine parallel schedule, alternating day cohorts, 64-minute screen-on budget, and micro jitter safety invariants.
- See `references/strict-slot-sync-and-on-demand-reg-drift.md` for strict slot mapping rules, on-demand reg provisioning invariants, and preventing silent fallback slot-drift bugs in `sync-safe-workbook.py`.
- See `references/feed-session-shift-budget-and-hardware-limits.md` for hard caps on feed sessions per shift (max 1 session/nick/ca), Samsung S7 hardware thermal/battery budgets, timeline 24h collision triage, and diminishing returns on session frequency.
- See `references/in-feed-follow-suggestion-unconditional-dismiss.md` for unconditional dismiss of in-feed follow suggestions and friend popups (no blind follows).

## Admin remote-media upload and canary evidence
When an Admin cluster's video source lives on `admin-farm`, do not run local Kibe `Path.is_file()` checks or copy/share the media. Dispatch the Admin workflow over SSH with the Admin runtime/config/workbook/source root; keep Kibe machines on the local path. For a bounded canary, wake an idle sleeping device through the runner's startup path instead of refusing the run, and verify the result from the remote `execution.log`, `report.json`, and pre-teardown `VERIFY_POST` screenshots. See `references/admin-remote-media-canary-evidence-20261006.md`.


## Durable reporting and cross-session follow lessons
- Never silently omit a configured cluster when it has no artifact; report `completed`, `skipped`, `not-started/no-artifact`, or `blocked/failed` explicitly with bounded evidence.
- For disputed windows, compare runner state, safe-workbook valid-account count, expected cluster artifact path, and `summary.txt`/`run_manifest.json` before interpreting the watchdog message.
- Keep feed execution separate from cross-follow release: a machine released in one session may still feed in the next; subtraction of its natural follows is a reconciliation adjustment, not proof of a second release.
- See `references/admin-cluster-visibility-and-cross-session-follow.md` for the validated evidence recipe and report contract.
- See `references/anti-double-penalty-and-transient-workbook-lock-recovery.md` for anti-double-penalty follow cooldown rules, workbook lock retry, and watchdog cluster visibility invariants.

- **Tài liệu tham khảo chuyên sâu (`references/`):**
  - `references/anti-double-penalty-and-modulo-slot-gap-hazard.md`: Bẫy trừ follow lặp phiên khi chưa khóa follow rate sau cooldown, bẫy lỗ hổng slot modulo-8 làm Admin thiếu nick Row 3 và cơ chế cấm watchdog nuốt im lặng cụm rỗng (2026-10-05).
  - `references/dual-cluster-preflight-reg-bu-and-watchdog-visibility.md`: Quy chuẩn Preflight Reg bù tự động đa cụm Kibe ↔ Admin, cạm bẫy sys.path thiếu tools/ trong ensure_row_accounts.py và cơ chế ẩn cụm rỗng của feed_session_watchdog.py (2026-10-04).
  - `references/deep-follow-rate-empirical-test-and-closeout-invariants.md`: Kiểm chứng thực nghiệm Monte Carlo khi hạ tỷ lệ follow tự nhiên và pitfall ký tự '>' trong closeout gate --text (2026-10-04).
  - `references/minimalist-rate-reduction-vs-overengineering-20261004.md`: Kỷ luật tối thiểu hóa can thiệp code: "Giảm tỉ lệ là được rồi, đừng chế cháo thêm phức tạp" (2026-10-04).
  - `references/natural-follow-deep-inspect-budget-hazard-and-reconcile.md`: Cadence follow tự nhiên 20% Deep Inspect, nguy cơ cắn budget follow chéo và đối soát 2 pha (2026-10-04).
  - `references/case186-natural-follow-watch-time-gate-and-watchdog-telemetry.md`: Watch Time Gate 8-12s và telemetry watchdog (2026-09-23).
  - `references/internal-vs-natural-follow-telemetry-isolation.md`: Tách biệt telemetry chéo vs tự nhiên.
  - `references/per-account-organic-rest-math-and-design.md`: Thiết kế và xác suất nghỉ dưỡng sinh 1/3.

## Missing report / wrong session-key triage

When the operator says a scheduled session report is missing, do not infer success from the watchdog's exit code. Verify cron metadata, manual stdout, claim-state keys, and current-day run artifacts in that order. Exit code 0 with empty stdout can be an intentional silent skip. A current-day `ca4_phien*` claim while the expected morning `ca1_phien1` key is absent is a state/window/parser anomaly, not evidence that the morning report was delivered. Use `references/session-report-missing-triage.md` for the concise evidence format and decision tree.

## One-message-per-session reporting invariant

Each completed `caN_phienM` must be delivered as its own Telegram message. Do not aggregate multiple session payloads with `print("\\n\\n".join(messages))`: cron `no_agent` treats stdout as one delivery unit, so adjacent session headers become one long message and the later header can be missed.
To enforce this invariant strictly:
1. **Loop Break on First Session**: In `main()`, once a session message is formatted and claimed in state, immediately `break` out of the session and date loops. Deliver only `print(messages[0])`. Any subsequent pending sessions are naturally claimed and delivered in independent messages on the next cron ticks (5 minutes apart).
2. **Session-Aware Runner Busy**: Do not let host-wide `is_feed_runner_active()` block completed prior sessions. Use session-aware inspection (`is_cluster_session_busy`): if the session window has passed (`now_hm >= win["end"]`), the session's run manifest has `end_time`, and a subsequent run exists, treat `runner_busy` as False for that session so it delivers immediately rather than waiting for the next session to finish.

Use `references/session-aware-runner-busy-and-single-delivery-gate.md` for the complete root cause analysis and patch contract, `references/session-report-missing-triage.md` for missing-report checks, and `references/watchdog-duplicate-and-merged-session-pitfalls.md` for merged-session reproduction and delivery-layer diagnosis.

References:
- `references/account-boost-posting-cadence-and-organic-rest-bypass.md` — Cơ chế tăng tần suất đăng 48h cho nick cắn đề xuất (BOOST state), bypass ngày nghỉ dưỡng sinh upload, và tiêu chí hold window 5 ngày.
- `references/fast-run-inspection-and-windows-process-triage.md` — Fast O(1) run manifest inspection (tránh recursive glob / GUARD_DANGEROUS_ROOT), timeout guard trên Windows terminal, và pitfall psutil timeout trên 56-core host.
- `references/tiktok-dashboard-delta-ui-formatting-and-invariants.md` — Chuẩn hiển thị Delta âm/dương Dashboard, rolling window chống co cụm nick sau 0h đêm (1.042 nick), triage lỗi mạng 1 nick làm méo mó Delta toàn farm, quy tắc phân loại Đề Xuất vs Tiềm Năng (Mutual Exclusivity Invariant), và tách bạch chu kỳ quét Web vs tiến độ ca nuôi bot trên thẻ Following (Time-Window Decoupling).
- `references/internal-vs-natural-follow-telemetry-isolation.md` — Lệch thống kê follow nội bộ vs follow tự nhiên giữa feed_session_watchdog và tiktok_dashboard.
- `references/watchdog-natural-follow-released-deduction.md` — Contract tự động trừ lượt follow tự nhiên của các nick bị nhả/drop follow trong feed_session_watchdog.py (calculate_session_natural_follows).
- `references/watchdog-farm-alert-threshold-calibration.md` — Hiệu chỉnh ngưỡng kích hoạt Farm Alert lỗi hàng loạt (>= 8 máy ~ 10% farm), chống báo động giả khi chỉ lỗi cá biệt 1-3 máy.
- `references/idempotent-session-account-actions-reconciliation.md` — Cơ chế chống cộng dồn lặp x3 (Idempotent Two-Tier Ledger) cho reconcile_cluster_following qua bảng trung gian session_account_actions.
- `references/can-report-session-runner-busy-guard-and-canary-reconcile.md` — Guard `runner_busy` đầu hàm `can_report_session` chống chốt phiên sớm khi đang chạy follow/upload & cơ chế canary đối soát following qua TikTok Web scraper DB.
- `references/per-account-organic-rest-math-and-design.md` — Chuyển đổi mô hình Dưỡng sinh từ Modulo 6 toàn farm sang xúc xắc độc lập từng nick (Per-Account Organic Rest), bảo toàn chính xác tỷ lệ 1/3 (~33.33%) bằng deterministic MD5 hash.
- `references/follow-hook-watchdog-race-false-alert-guard.md` — Xử lý race condition khi Feed watchdog ép chốt phiên dở dang lúc runner đang bận, chống báo ảo "Follow Hook Lỗi UI/Script" khi thiếu file follow_result.
- `references/case166-phien-1-upload-hardcode-fix.md` — Case 166: Phiên 1 tự động đăng video do hardcode `-AllowUploadHook` trong wrapper cron `tiktok_runner.py` & quy trình đồng bộ sang Deploy/OneDrive.
- `references/case165-empty-feed-fallback-and-direct-probe.md` — Case 165: Màn hình gợi ý rỗng tab Bạn bè/Following, fallback về Đề xuất & quy tắc test probe trực diện (chống xà quằn batch runner).
- `references/empty-feed-fallback-and-tab-like-tuning.md` — Xử lý màn hình Bạn bè / Following rỗng (chưa follow ai) tự động fallback For You & mở rộng selector nút Like + telemetry.
- `references/empty-friends-following-feed-like-triage.md` — Root cause tỉ lệ like Bạn bè/Following thấp do kẹt màn hình gợi ý rỗng (không có video) & giải pháp fix sau dice.
- `references/watchdog-classification-fix.md`
- `references/watchdog-module-counts-passthrough.md` — Contract Module 1/2 counts passthrough (2 anchors, focused check <30s, rg/MSYS pitfall).
- `references/case171-session-start-micro-jitter.md` — Case 171: Micro-Jitter khởi động phiên (60s-180s) trong run-feed-session.ps1 xóa chữ ký giờ cứng mà không làm gãy Watchdog / Silent window.
- `references/case172-continuous-behavior-rates.md` — Case 172: Chuyển dịch sang phân phối mềm liên tục cho For You Like (5-12%) và Comment Peek (8-16%) phá vỡ chữ ký quần thể đồng nhất.
- `references/case175-humanized-finger-swipe-and-thumb-arc.md` — Case 175: Vuốt ngón tay sinh học (Thumb Arc Drift 240-400ms), nới ngưỡng skew |dx|>45px và loại bỏ bẫy over-engineering đo nhiệt độ máy farm.
- `references/case175-humanized-thumb-arc-swipe-and-health-telemetry.md` — Case 175: Vuốt ngón tay sinh học (Humanized Thumb Arc Swipe: duration 240-400ms, drift -35..+15px, Y 1330-1410 -> 430-510) & quy chuẩn Telemetry sức khỏe thực chiến (loại bỏ bẫy đo nhiệt độ/RAM bóp quota farm).
- `references/case175-humanized-thumb-arc-swipe.md` — Chi tiết thực thi code surgery Case 175: 3 anchors trong feed_swipe_smoke.py, kết quả 1000/1000 mẫu simulation pass và commit master 9f34aa1.
- `references/case176-profile-view-telemetry-and-zero-view-jail.md` — Case 176: Telemetry sức khỏe tài khoản (bóc tách latest_views từ Profile XML ở y>=850, loại trừ header/ghim), quy tắc 0-View Jail thực chiến Cách B (chống phạt oan video flop lẻ, chỉ phạt khi 2 video liên tiếp 0-view >24h) & cơ chế tự động ép nghỉ dưỡng sinh Deep Organic Rest 72h.
- `references/case177-auto-advance-regex-delimiter-drift.md` — Case 177: Lỗi false-failure `post_verification_failed` do lệch delimiter regex `new_video_number=` (gạch dưới) vs stdout thực tế `new video_number=` (khoảng trắng) khi child auto-advance video đã đăng.
- `references/case170-feed-runner-session-index-upload-gate.md` — Case 170: Gating -AllowUploadHook trong tiktok_runner.py theo session_index == 2 (Phiên 2 mới được đăng video, Phiên 1 chỉ lướt feed thuần).
- `references/feed-fail-classifier-triage-patterns.md` — Phân loại root cause fail, false positive Search Landing do EditText ẩn trên Feed, và quy trình triage nhanh 4 nhóm theo quota/stop_reason từ báo cáo watchdog.
- `references/transient-adb-socket-saturation-and-stale-lock-triage.md` — Rớt ADB ảo do nghẽn socket multi-worker & cơ chế lock mồ côi (preserve_blocker_screen).
- `references/feed-tab-like-rate-triage.md` — Phân tích nguyên nhân tỉ lệ like tab Bạn bè / Following hiển thị ~10-15% trên Watchdog sau Case 178 (Fast Swipe đa tab) & Case 184 (mẫu số gộp Fast Swipe).
- `references/dynamic-interaction-rates-like-comment-peek.md` — Động hóa dải tương tác Like (For You 5-12%) và Comment Peek (8-16%) theo phân phối mềm liên tục.
- `references/reporting-standards.md` — Tiêu chuẩn báo cáo tiến trình watchdog/batch (bắt buộc đủ mẫu số Đã đạt/Tổng số acc %, cấm thuật ngữ trừu tượng "Lũy kế" gây lú lẫn, chỉ báo nick lệch trong khối đối soát - cấm spam nick khớp, chống báo ảo 100% khi chưa gán nick, alias tương thích Admin-Kibe & quy trình sync 3 vị trí).
- `references/macro-cycle-and-cross-follow-scheduling.md` — Quy chuẩn lịch điều phối macro chu kỳ 6 ngày (xoay tua 4 acc/ngày + ngày dưỡng sinh nghỉ follow), định luật follow chéo nội bộ (3-4 tháng/lứa 1k), móng 10 video, budget chuẩn 10-20 follow/phiên, và cơ chế tự động mở lại follow khi hết hạn cooldown.
- `references/watchdog-organic-rest-reporting-format.md` — Tiêu chuẩn format báo cáo Telegram cho Watchdog: hiển thị khối Chế độ Dưỡng Sinh (Organic Rest ~33%) và phân loại chi tiết các nhóm bỏ qua (Dưỡng sinh, Chưa đủ 10 video, Chưa có render video).
- `references/case175-176-biometric-thumb-arc-and-zero-view-telemetry.md` — Case 175 & 176: Vuốt ngón tay sinh học (Thumb Arc Drift 240-400ms), Telemetry bóc tách view Profile XML chống 0-View Jail (Deep Rest 3 ngày cho 2 video 0-view liên tiếp >24h), và kỷ luật Pre-Write Gate chống Memory Leakage.
- `references/sol-audit-anti-fraud-fleet-correlation.md` — Đánh giá thẩm định từ Sol 5.6 (:20129) về rủi ro Anti-Bot/Anti-Fraud: Scorecard 55–65/100, bóc tách điểm nghẽn Fleet-Level Correlation (160 máy Galaxy S7 cùng ROM/framework) và định hướng context-aware.
- `references/humanized-touch-kinematics-and-health-telemetry.md` — Chuẩn hóa động học vuốt ngón tay (Humanized Finger Swipe: duration 220-420ms, thumb arc drift) & Telemetry sức khỏe tài khoản thực chiến (0-view, follow nhả, kích hoạt Deep Rest 3 ngày; cấm bóp farm vì nhiệt độ phần cứng).
- `references/comment-peek-xml-fallback-and-watchdog-upload-breakdown.md` — Lazy XML Loading cho Comment Peek trên Deep Inspect Videos, bóc tách 4 nhóm Bỏ qua Upload trên Watchdog (tránh gom nhãn Khác), và cạm bẫy duplicate argparse khiến toàn farm crash upload.
- `references/tiktok-feed-and-upload-hook-pitfalls.md` — Cạm bẫy argparse conflicting option string, in-memory raw_xml drop, và bóc tách skip reason trên watchdog.
- `references/watchdog-duplicate-and-merged-session-pitfalls.md` — Cạm bẫy báo cáo sớm khi chưa đủ 80 máy, gửi lặp phiên do chưa claim state, và lỗi gộp nhiều phiên vào 1 payload text làm trôi mất header phiên sau.
- `references/cross-workflow-empty-row-and-stale-lock-triage.md` — Quy trình điều tra O(1) lỗi lướt feed diện rộng: Hiệu ứng dây chuyền hàng trống (Empty Row Config-Error), kẹt trần 8 nick Switcher và stale device locks.
- `references/cache-cleanup-cron-feed-conflict-triage.md` — Xung đột chí mạng giữa Cron dọn cache (end-of-day-clear-tiktok-cache) bắn phá toàn farm và ca nuôi feed ban đêm (Ca 4).
- `references/watchdog-upload-progress-and-skip-breakdown-standard.md` — Tiêu chuẩn báo cáo tiến độ Upload trên Watchdog: mẫu số máy đủ điều kiện, video number lũy kế M<M>(v<N>), và bóc tách 100% danh sách máy bỏ qua (chống gom cục nhãn Khác).
- `references/session-aware-runner-busy-and-single-delivery-gate.md` — Khắc phục lỗi watchdog gom gộp 2 phiên vào 1 tin nhắn Telegram và không báo ngay: cơ chế session-aware runner busy & ngắt vòng lặp bảo đảm mỗi tick chỉ gửi 1 phiên.
- `references/case178-fast-swipe-multi-tab-and-calibrated-like-rates.md` — Case 178: Mở Fast Swipe cho cả tab Bạn bè & Following, cân chỉnh tỉ lệ like bù trừ và fix Dead-man hook cho delegate_task.
- `references/case179-watchdog-feed-counts-tab-like-percentage-fix.md` — Case 179: Vá lỗi thiếu bóc tách dict feed_counts và merge tích lũy trong feed_session_watchdog.py khiến tỷ lệ % like theo từng tab hiển thị ảo 0.0%.
- `references/case180-friends-empty-feed-denominator-leakage.md` — Case 180: Khắc phục rò rỉ mẫu số màn hình gợi ý rỗng tab Bạn bè (Friends) vào feed_counts và mở rộng từ khóa fallback danh bạ/Facebook.
- `references/case180-empty-friends-feed-denominator-leak-fix.md` — Case 180: Loại bỏ hoàn toàn màn hình gợi ý rỗng / danh bạ ra khỏi mẫu số feed_counts và mở rộng từ khóa fallback Friends/Following.
- `references/case180-friends-feed-like-rate-triage-and-sample-size.md` — Case 180: Bóc tách nguyên nhân tỉ lệ thả tim tab Bạn bè tụt sâu (~8%) trên báo cáo Watchdog (mẫu số video Friends nhỏ + nick rỗng màn hình gợi ý).
- `references/case193-already-liked-denominator-exclusion.md` — Case 193: Loại trừ video already_liked ra khỏi mẫu số tính tỷ lệ like tab Bạn bè / Following trên Watchdog (valid_swipes = max(likes, swipes - already_liked)).
- `references/natural-follow-gating-reconciliation-and-ratio-analysis.md` — Gating follow tự nhiên khóa cứng 0% ngày dưỡng sinh, gom cào Web đối soát natural follow post-session, và giải mã lệch tỷ lệ mẫu số co cụm (2026-10-04).

## 1. Bug: Fast Swipe Nuốt Nhịp Đếm Chuyển Tab (`feed_swipe_smoke.py`)

**Vấn đề:** Biến đếm `videos_until_tab_decision` chỉ được trừ ở nhánh Deep Inspect (`videos_until_tab_decision -= 1`). Nhánh Fast Swipe (chiếm ~70% video) gọi `continue` mà quên trừ biến đếm, khiến biến đếm không bao giờ về `<= 0` và tab không bao giờ được chuyển. Kết quả: Toàn bộ máy kẹt 100% ở tab Đề xuất, tab Bạn bè và Following có 0 lượt xem/tim.

**Giải pháp:** Thêm `videos_until_tab_decision -= 1` ngay trước `continue` trong nhánh Fast Swipe (dòng 21446). Hai nhánh (Deep Inspect và Fast Swipe) đều phải tiêu tốn biến đếm để kích hoạt `_weighted_feed_choice` đúng cách.

**Vị trí áp dụng:**
- `python_runner/flows/feed_swipe_smoke.py` - dòng sau `videos_until_deep_inspect -= 1`

**Kiểm chứng:**
- Live canary trên Máy 3 (Row 7) với `--feed-distribution {"for-you": 0.0, "following": 0.5, "friends": 0.5}`: Máy nhận diện và bấm chuyển tab Following thành công (`switch_following_4_navigation_confirm`, confidence 0.9).
- Replay watchdog trên dữ liệu Ca 4: Tách đúng 45 máy trống slot ra khỏi 15 máy lỗi thật, thống kê 57 tim / 391 video (14.6%).

## 2. Watchdog: Phân Loại Máy Trống Slot Khác Lỗi Thực Tế (Cập Nhật 2026-09-13)

**Vấn đề:** Watchdog cũ gom mọi status `!= success` vào danh sách `Fail`, bao gồm cả 45 máy Row 7 chưa có nick trong file cấu hình (`account row 7 is empty (no username), skipping`). Điều này làm phình to danh sách Fail từ 16 máy thật lên 61 máy (kể cả trống slot), khiến người vận hành không phân biệt lỗi thực tế vs thiếu tài khoản.

**Giải pháp:**  
- Phân loại riêng `Trống slot/chưa có nick` ra khỏi danh sách `Fail`  
- Gán trạng thái `skipped-empty` khi lý do chứa `is empty (no username)`  
- Bóc tách `feed_counts` theo 3 tab: `for-you`, `friends`, `following`  
- Thống kê tổng: `like_counts: X tim / Y video (Z%) [Đề xuất: A | Bạn bè: B | Following: C]`  
- **Thêm: Phân loại MANUAL_REVIEW có lý do "không có video" thành `fl_skipped` (safe-skip) thay vì `fl_error`**  
- Merge likes/swipes chỉ thêm vào result khi có trong prev/new (tránh inject default 0)  

**Vị trí áp dụng:**  
- `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` (đã đưa vào repo)  
- `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`  

**Kiểm chứng:**  
- Unit test `test_feed_session_watchdog.py`: 4/4 test pass (merge_machine_result, can_report_session boundary cases)  
- Data replay Ca 4: 20 Success, 15 Fail, 45 Trống slot; 57 tim / 391 video (14.6%)  
- **Fix verification: 20 máy anchor thiếu video chuyển từ ERROR → SKIPPED, giảm lỗi từ 34→14, tăng bỏ qua từ 40→60**

## 3. Cron Sync: Fail-Closed Keyword Sync (`hermes_taikhoan_sync_cron.py`)

**Vấn đề:** Bước đồng bộ Keyword chạy với `check=False` nhưng không kiểm tra `returncode`. Nếu sync Tik thất bại, cron vẫn có thể chạy `sync_all_tik_keywords.py` và ghi dữ liệu vào workbook trạng thái chưa đồng bộ/drift, trái với mục tiêu fail-closed.

**Giải pháp:**
- Bước sync keyword (`1b`) chỉ chạy **sau khi** sync Tik (`1`) thành công (dùng early-return `if failed`).
- Nếu sync keyword lỗi: ghi log warning qua `try/except`, **không** set `failed = True`, **không** làm vỡ luồng sync chính.
- Timeout 300s hợp lý cho tác vụ đồng bộ.

**Vị trí áp dụng:**
- `scripts/hermes_taikhoan_sync_cron.py` (đã cập nhật trong repo)

**Kiểm chứng:**
- `py_compile` pass 100% trên `tiktok_runner.py` và `ensure_row_accounts.py`
- Reviewer verdict: VERDICT: APPROVED

## 4. Mapping Tik7/Tik8 Đồng Bộ

**Vấn đề:** File cấu hình chỉ hỗ trợ Tik1..Tik6, nhưng farm đang mở rộng lên 8 tài khoản (Tik1..Tik8). Khi file không có Tik7/Tik8, các script lặp qua danh sách sẽ bỏ qua an toàn nhưng dữ liệu mapping bị thiếu, gây drift phiên nhầm cột/quy đổi.

**Giải pháp:**
- `scripts/sync-safe-workbook.py`: Thêm `"Tik7.xlsx", "Tik8.xlsx"` vào tuple `TIK_FILE_NAMES`
- `scripts/sync-tik-workbooks.py`: Thêm `"Tik7.xlsx": 7, "Tik8.xlsx": 8` vào dict `TIK_SLOT_MAP`
- Đồng bộ ở `hermes_taikhoan_sync_cron.py`: logic `TIK_NAMES` tuple bây giờ dài 8 phần tử

**Vị trí áp dụng:**
- `scripts/sync-safe-workbook.py`
- `scripts/sync-tik-workbooks.py`
- `scripts/hermes_taikhoan_sync_cron.py`

## 5. Canary Test with Forced Feed Distribution

**Mục đích:** Kiểm chứng cơ chế chuyển tab khi biến đếm về 0.
- Dùng `--recovery-test-swipes 4` giới hạn số swipe test.
- Dùng `--feed-distribution {"for-you": 0.0, "following": 0.5, "friends": 0.5}` ép tab Following.
- Kết quả: Máy 3 chuyển tab thành công, `feed_counts = {"for-you": 1, "following": 1, "friends": 0}`.

**Câu lệnh mẫu:**
```bash
python "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
  --mode multi-machine-feed-session \
  --machines 3 \
  --account-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
  --account-row-index 7 \
  --max-workers 1 \
  --config "D:/Taadaa/tiktok-luot nuoi acc/python_runner/config.example.yaml" \
  --artifact-root "D:/Taadaa/runtime/kibe/live/test_canary_tab_m3_force" \
  --allow-navigation-only \
  --allow-feed-swipe \
  --session-index 2 \
  --allow-benign-popup-dismiss \
  --prepare-tiktok \
  --recovery-test-swipes 4 \
  --feed-distribution "{\"for-you\": 0.0, \"following\": 0.5, \"friends\": 0.5}"
```

## 6. Case 156 (13/09/2026): Khắc Phục Bug Fast Swipe Nuốt Nhịp Đếm Chuyển Tab & Bổ Sung Bóc Tách Thả Tim Theo Tab Trên Watchdog

**Vị trí áp dụng:** `python_runner/flows/feed_swipe_smoke.py`, `scripts/sync-safe-workbook.py`, `scripts/sync-tik-workbooks.py`, `scripts/hermes_taikhoan_sync_cron.py`, `scripts/feed_session_watchdog.py`, `docs/farm-automation-cases.md`.

**Hiện tượng:** Toàn bộ 80 máy kẹt 100% ở tab Đề xuất, thiếu thống kê thả tim.

**Nguyên nhân cốt lõi:**
1. Trong `feed_swipe_smoke.py`, biến đếm nhịp chuyển tab `videos_until_tab_decision` chỉ được trừ ở nhánh Deep Inspect. Nhánh Fast Swipe quên trừ biến đếm.
2. Watchdog cũ gom chung 45 máy trống slot Row 7 vào danh sách `Fail`.

**Giải pháp chuẩn (Case Fix):**
1. Thêm `videos_until_tab_decision -= 1` vào nhánh Fast Swipe (`feed_swipe_smoke.py`).
2. Đồng bộ mapping Tik7/Tik8 (`sync-safe-workbook.py`, `sync-tik-workbooks.py`, `hermes_taikhoan_sync_cron.py`).
3. Cập nhật watchdog: phân loại riêng máy `Trống slot/chưa có nick`, tích lũy `likes`/`swipes`, bóc tách thống kê theo từng tab (`feed_session_watchdog.py`).
4. Ghi nhận vào `docs/farm-automation-cases.md` (Case 156).

**Kiểm thử & Verification:**
- Live Canary Máy 3 (Row 7) ép chuyển tab `{"for-you": 0.0, "following": 0.5, "friends": 0.5}`: Máy chuyển tab Following thành công.
- Replay watchdog trên dữ liệu Ca 4: Tách đúng 45 máy trống slot ra khỏi 15 máy lỗi thật.
- Focused pytest: `test_feed_session_watchdog.py` pass 100% các unit test logic merge.
- Reviewer 9Router `:20129` model `review`: VERDICT: APPROVED.

## 7. Patch Contract: Fix Tỉ Lệ Like & Selector Nút Like (`feed_swipe_smoke.py`)

**Vị trí:** `python_runner/flows/feed_swipe_smoke.py`

**3 Anchors cốt lõi:**
1. **Anchor 1 (Like Rates Config - ~dòng 680):**
   - Đảm bảo `DEFAULT_FEED_LIKE_RATES` cấu hình phù hợp (`FEED_TYPE_FOLLOWING: 50`, `FEED_TYPE_FRIENDS: 80` hoặc theo yêu cầu ca nuôi).
2. **Anchor 2 (Selector Nút Like & Telemetry Logging - ~dòng 13593):**
   - **Selector mở rộng:** Bỏ phụ thuộc cứng vào `element.attrib.get("clickable") == "true"` (do TikTok bọc trong FrameLayout không clickable).
   - Bổ sung matching pattern: `("thích" in desc_lower and "lượt thích" in desc_lower)` hoặc `("like" in desc_lower and "likes" in desc_lower)`.
   - **Xóa bỏ Fail-Silent:** Thay vì âm thầm `return False`, ghi log telemetry `action="like_video", result="skipped"` với error rõ ràng (`already_liked`, `button_not_found`) để phân biệt xúc xắc tạch vs UI thiếu element.
3. **Anchor 3 (Post-Swipe Drift & Empty Suggestions Recovery - ~dòng 21666):**
   - Kiểm tra hiện tượng tab Bạn bè / Following không có video mà hiển thị màn hình gợi ý kết bạn ("Hãy follow bạn bè", "Tác giả nổi bật").
   - Kích hoạt recovery đưa về `FEED_TYPE_FOR_YOU` an toàn để không kẹt vòng lặp swipe vô ích.

## 8. Pitfall: Blank-line Codebase Formatting & Live Canary Discovery

**Triệu chứng:** Khi patch `feed_swipe_smoke.py`, việc find-and-replace literal string thường thất bại (hoặc không khớp) do file chứa nhiều dòng trống xen kẽ giữa các câu lệnh (`\n\n` hoặc blank lines do auto-formatter/decompilation).
**Cách xử lý đúng:**
- Khi tìm kiếm hoặc thay thế các điểm code lớn trong `feed_swipe_smoke.py`, ưu tiên dùng regex linh hoạt với `\s*` qua Python script thay vì chuỗi literal nhiều dòng liền nhau.
- Sau khi patch luôn chạy `python -m py_compile "python_runner/flows/feed_swipe_smoke.py"`.
- **Lấy device serial & ảnh live screencap khi kết thúc session:** Khi cần chụp ảnh live canary của một máy (ví dụ Máy 3), nếu runner timeout ở wrapper hoặc chưa xuất screencap trực tiếp ra thư mục cha:
  - Tra cứu device serial của máy qua `D:/Taadaa/runtime/kibe/live/.../machines/machine_<M>/.../summary.txt` (mục `device_serial: device:<serial_hash>` hoặc tương đương), hoặc lấy ảnh screenshot cuối cùng có sẵn trong artifacts: `.../feed-session-smoke/swipe_4_after_back_recheck/attempt_1/screen.png`.
  - Nếu cần screencap live trực tiếp từ thiết bị, query serial qua mapping config hoặc adb theo device mapping của machine đó rồi xuất qua `adb -s <serial> exec-out screencap -p`.

## 9. Kỷ Luật Test Canary Màn Rỗng & Isolated Logic (Tránh Xà Quằn)

- **Cấm chạy nguyên feed session 4 swipes để test đổi tab:** Vì `videos_until_tab_decision` (3-8 swipes) chưa về 0 thì runner chỉ lướt ở For You, không bao giờ chạm tới tab Friends/Following -> canary inconclusive và tốn thời gian vô ích.
- **Quy trình probe test trực diện:**
  1. Mở TikTok -> tap thẳng vào tab mục tiêu (`Bạn bè` hoặc `Đã follow`).
  2. Dump UI XML (qua ATX JSON-RPC port 7912 hoặc `uiautomator dump`).
  3. Kiểm tra marker rỗng (`_FRIENDS_FEED_CONTENT_TERMS`: `Nhật ký`, `Tác giả nổi bật`, `Hãy follow bạn bè`).
  4. Kích hoạt logic fallback (tap tab `Đề xuất`).
  5. Verify tab `Đề xuất` nhận `selected="true"` và xuất ảnh screencap MEDIA nghiệm thu.

## 10. Farm Alert Gate & Mass Failure Notification (>10 Máy Lỗi)

**Quy tắc bất biến:**
Khi bất kỳ khâu nào (Lướt Feed, Follow Hook, hoặc Upload Hook) có **> 10 máy bị lỗi**, watchdog BẮT BUỘC phải dispatch cảnh báo đỏ `[FARM ALERT]` trực tiếp về Telegram nhóm Farm Alert (`-5373649734`), tuyệt đối KHÔNG chỉ in ra console hoặc âm thầm gửi về origin session.

**Triệu chứng & Cạm bẫy:**
- Watchdog chỉ gom lỗi vào báo cáo tổng kết cuối phiên (`deliver: origin`), khiến các lỗi diện rộng (như 13 máy lỗi UI Follow, lỗi proxy hàng loạt) bị trôi xuống cuối bản tin text nhỏ, người vận hành không nhận được thông báo khẩn.
- Tỷ lệ Feed thành công cao (>80%) dễ che lấp các lỗi sụp đổ 100% của hook phía sau (Follow Mode 2 / Upload).

**Chuẩn triển khai (`feed_session_watchdog.py`):**
1. Khai báo `FARM_ALERT_CHAT_ID = "-5373649734"`.
2. Lấy `TELEGRAM_BOT_TOKEN` từ biến môi trường hoặc file `~/AppData/Local/hermes/.env`.
3. Kiểm tra biến đếm lỗi:
   - `feed_fail_cnt = len(fail)`
   - `follow_err_cnt = len(fl_error)`
   - `up_err_cnt = len(up_error)`
4. Nếu `feed_fail_cnt > 10 or follow_err_cnt > 10 or up_err_cnt > 10`:
   - Gửi ngay tin nhắn HTML khẩn cấp với định dạng:
     ```html
     🚨 <b>[FARM ALERT] PHÁT HIỆN LỖI DIỆN RỘNG (>10 MÁY)</b>
     • <b>Ca</b>: {name} (Row {row})
## 11. Case 171 (14/09/2026): Micro-Jitter Khởi Động Phiên (60s - 180s) Xóa Bỏ Chữ Ký Giờ Cứng Không Gãy Watchdog Farm

**Hiện tượng & Cảnh báo Anti-Fraud:**
- 160 máy Galaxy S7 cùng kích hoạt vào đúng giây `:00` của các mốc giờ chẵn (`06:00`, `08:00`, `12:00`...) tạo nên chữ ký nhịp tim cơ học (Periodic Deterministic Anomaly).
- Tuy nhiên, TUYỆT ĐỐI KHÔNG ĐƯỢC sửa giờ Cron hệ thống vì sẽ phá vỡ vùng cấm chạy Silent Window (`02:00 - 05:59`) của `tiktok_picker.py` và làm lệch khung quét `SESSION_WINDOWS` của `feed_session_watchdog.py`, dẫn đến bắn nhầm Red Alert.

**Giải pháp chuẩn (Case Fix):**
- Bổ sung tham số `[switch]$DisableSessionJitter`, `[ValidateRange(0, 600)][int]$SessionJitterMinSeconds = 60`, `[ValidateRange(0, 600)][int]$SessionJitterMaxSeconds = 180` vào `run-feed-session.ps1`.
- Trước khi thực hiện ADB chạm vào chiếc điện thoại đầu tiên (`$Run` mode), tiến trình tự động ngâm dừng ngẫu nhiên từ 1 đến 3 phút (`60s – 180s`).
- Trong lúc ngâm dừng, tiến trình PowerShell đã active (`runner_busy = True`), giúp Watchdog nhận diện phiên đang diễn ra an toàn và kiên nhẫn chờ.
- Tự động bypass Micro-Jitter khi chạy test hoặc phục hồi (`-RecoveryTestSwipes` hoặc `-DisableSessionJitter`).

**Vị trí áp dụng:** `scripts/run-feed-session.ps1`.
**Kiểm chứng:** Syntax preview pass exit 0, validation chặn min > max đúng chuẩn, GPT-5.6 Sol thẩm định `VERDICT: APPROVED`. Chi tiết xem thêm tại `references/case171-session-start-micro-jitter.md`.

## 12. Case 172 (14/09/2026): Phân Phối Mềm Liên Tục (Continuous Behavioral Rates) Cho Like & Comment Peek

**Vấn đề Anti-Fraud:**
- 160 máy trên farm trước đây sử dụng các mốc tỷ lệ cố định (For You like 8%, Comment peek 12%). Thuật toán học máy của ByteDance (Isolation Forest / Anomaly Detection) có thể phát hiện chữ ký "quần thể có entropy thấp" (Population Homogeneity) do thiếu độ lệch chuẩn tự nhiên giữa các thực thể.
- Việc chia các nhóm archetype cứng (30% nhóm A, 50% nhóm B...) vẫn bị Sol bắt lỗi vì tạo ra các cụm robot mới có ranh giới quá sạch sẽ.

**Giải pháp chuẩn:**
- Chuyển sang mô hình phân phối liên tục (Continuous Distribution):
  - **Like tab For You:** Biến thiên ngẫu nhiên `random.randint(5, 12)%` khởi tạo một lần theo cấp phiên trong `_feed_like_rates()`.
  - **Comment Peek:** Biến thiên ngẫu nhiên `random.randint(8, 16)%` khởi tạo một lần theo cấp phiên (`session_comment_peek_rate`) và tái sử dụng nhất quán trong toàn bộ phiên.
  - Giữ nguyên dải video an toàn `16 – 22 video` để bảo toàn phần cứng Samsung S7 và lịch trình chuyển ca của farm.

**Vị trí áp dụng:** `python_runner/flows/feed_swipe_smoke.py`.
**Kiểm chứng:** Pytest unit tests đạt 7/7 passed, GPT-5.6 Sol thẩm định độc lập `VERDICT: APPROVED`. Chi tiết xem thêm tại `references/case172-continuous-behavior-rates.md`.

## 13. Case 173 (15/09/2026): Chống Báo Ảo Follow Hook Lỗi UI/Script & Chốt Sớm Khi Runner Đang Bận (`feed_session_watchdog.py`)

**Hiện tượng & Báo ảo:**
- Watchdog phát cảnh báo đỏ diện rộng `⚠️ Follow Hook Lỗi UI/Script (N máy)` hoặc `Lỗi script/xác minh (70): ...` dù trên thực tế thiết bị không crash UI hay exception script.
- Nguyên nhân kép:
  1. Trong `can_report_session()`, điều kiện `completed_expected_count >= expected_count` (chỉ đếm khâu Feed) đặt TRƯỚC `if runner_busy: return False`. Khi toàn bộ máy vừa lướt xong Feed nhưng khâu Follow hook/ghi artifact vẫn đang chạy dở ở các máy sau, watchdog vội vàng chốt phiên ngay lập tức.
  2. Phân loại fallback: Máy lướt Feed thành công (`status == 'success'`) nhưng chưa đọc được `follow_result.json` bị đánh đồng là lỗi kịch bản (`fl_error.append(m)`).
  3. Cơ chế ghi `feed_session_reported.json` khóa cứng trạng thái, ngăn watchdog tự sửa báo cáo ở các tick sau khi file đã flush xong.

**Giải pháp chuẩn:**
- Trong `can_report_session()`: Khi đang trong giờ phiên (`now_hm < window_end_hm`), `if runner_busy: return False` BẮT BUỘC phải đặt lên đầu, trước mọi kiểm tra số máy hoàn tất.
- Trong logic phân loại: Kiểm tra cờ `runner_busy`. Nếu runner vẫn đang bận (`runner_busy == True`), phân loại máy vào `fl_skipped` (bỏ qua an toàn) thay vì gán lỗi `fl_error`.
- Chỉ tính `fl_error` khi runner đã kết thúc rảnh rỗi (`runner_busy == False`) mà máy lướt Feed thành công vẫn hoàn toàn thiếu dữ liệu follow hook.
- Đồng bộ nghiêm ngặt 3 vị trí (tránh sync drift): `C:/Users/Kibe/AppData/Local/hermes/scripts`, `D:/Taadaa/Hermes/deploy/hermes-home/scripts`, `D:/Taadaa/tiktok-luot nuoi acc/scripts`.

**Code Contract:**
```python
# 1. can_report_session: runner_busy chặn chốt sớm
if is_today and now_hm < window_end_hm:
    if runner_busy:
        return False
    if completed_expected_count >= expected_count and not has_unattempted_locked:
        return True

# 2. Phân loại an toàn khi runner đang bận
else:
    if all_machines[m].get("status") == "success":
        if runner_busy:
            fl_skipped.append(m)
        else:
            fl_error.append(m)
```

**Quy trình đồng bộ 4 vị trí (bắt buộc đồng bộ đủ cả 4 nơi để tránh drift):**
1. `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
2. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
3. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
4. `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`

**Kiểm chứng:**
- Chạy `pytest C:/Users/Kibe/AppData/Local/hermes/scripts/test_feed_session_watchdog.py` (4/4 passed).
- Chi tiết: `references/follow-hook-watchdog-race-false-alert-guard.md`.
## 14. Chuyển Đổi Mô Hình Dưỡng Sinh: Per-Account Organic Rest (1/3) Thay Thế Modulo 6 Cũ

**1. Thay thế Chu kỳ Modulo 6 bằng Per-Account Organic Rest (1/3):**
- **Cơ chế cũ (Deprecated):** Modulo 6 toàn farm `(now.date() - date).days % 6` khiến toàn bộ máy/row phải nghỉ dưỡng sinh đồng loạt vào Day 2 và Day 5 (set `TAADAA_REST_DAY_NO_FOLLOW=1`, không pass `-AllowUploadHook`). Nhược điểm: ngắt quãng farm đồng loạt, pattern cứng.
- **Cơ chế mới (Per-Account Organic Rest):**
  - **Lịch Chẵn/Lẻ tại Runner (`tiktok_runner.py`):** Phân định đơn giản theo ngày dương lịch `parity = 0 if (now.day % 2 == 0) else 1`, trả về `is_rest_day = False`, xóa bỏ biến môi trường toàn cục `TAADAA_REST_DAY_NO_FOLLOW`. Cho phép `-AllowUploadHook` để từng worker tự quyết định.
  - **Quyết định độc lập tại Worker (`multi_machine_feed_session.py`):** Từng tài khoản tự tính xác suất dưỡng sinh 1/3 qua MD5 băm `(date_str, machine, row)`, có hỗ trợ cờ cưỡng chế dưỡng sinh (`force_rest_ledger`) khi nick dính shadowban / 0-view jail:
    ```python
    def _is_account_organic_rest_day(machine: Any, row: Any, date_str: str | None = None, *, force_rest_ledger: dict[str, Any] | None = None) -> bool:
        try:
            m_num = int(machine or 0)
        except (ValueError, TypeError):
            m_num = 0
        try:
            r_num = int(row or 1)
        except (ValueError, TypeError):
            r_num = 1
        
        # Kiểm tra cờ Deep Organic Rest (nếu tài khoản đang trong thời gian dưỡng sinh phục hồi 0-view/phạt)
        if force_rest_ledger and isinstance(force_rest_ledger, dict):
            key = f"{m_num}:{r_num}"
            if force_rest_ledger.get(key) or force_rest_ledger.get(f"m{m_num}_r{r_num}"):
                return True

        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        h = hashlib.md5(f"{date_str}:{m_num}:{r_num}".encode("utf-8")).hexdigest()
        return (int(h[:8], 16) % 3) == 0
    ```
  - **Hành vi trong ngày dưỡng sinh:**
    - Lướt feed bình thường để tích lũy thời gian xem và tương tác organic.
    - `_run_follow_hook`: Tự động skip follow hook với `reason="organic-rest-day-pure-feed"`, `action="skip_follow_rest_day"`.
    - `_run_upload_hook`: Tự động skip upload hook với `reason="organic-rest-day-pure-feed"`.
  - Chi tiết thiết kế toán học xem tại `references/per-account-organic-rest-math-and-design.md`.

**2. Ngưỡng Budget Follow Chuẩn 10 - 20:**
- Cấu hình chuẩn per-session: `budget_per_session_min: 10`, `budget_per_session_max: 20`, `budget_per_session: 20`, `budget_per_day: 40`.
- Fallback code trong `follow_state.py` đồng bộ default về 10 - 20.

**3. Bản chất Toán học Follow chéo nội bộ:**
- 1 nick gửi đi an toàn ~250-350 follow/tháng $\rightarrow$ Để nhận về 1.000 follow nội bộ từ dàn, bắt buộc mất ~3 đến 4 tháng. Máy nhiều (160 máy) chỉ tăng sản lượng mẻ (batch output), không thể rút ngắn thời gian trưởng thành của 1 nick đơn lẻ.

**4. Cơ chế tự động mở lại cờ follow khi mãn hạn phạt:**
- Trong `feed_swipe_smoke.py`, hàm `is_account_in_follow_cooldown()` so sánh thời gian thực với `cooldown_until_at`.
- Khi hết hạn (`now_utc >= until_dt`): Cờ cooldown tự chuyển về `False`. Script tự động mở lại follow ở tab For You (`_deep_follow_rate` 5%) và popup `follow_back_suggestion` tự chuyển từ né phạt (bấm "Không quan tâm") sang nhận kết nối (bấm "Follow lại").
- Chi tiết xem tại `references/macro-cycle-and-cross-follow-scheduling.md`.

## 15. Format Báo Cáo Telegram Watchdog: Khối Dưỡng Sinh & Bóc Tách Nhóm Bỏ Qua

**Quy chuẩn hiển thị:**
1. **Khối Chế độ Dưỡng Sinh (Organic Rest ~33%):**
   - Vị trí: Đặt ngay sau thống kê Lướt Feed và trước thống kê Follow chéo.
   - Nội dung: `🌿 Nghỉ dưỡng sinh (X máy): M... (Chỉ lướt feed, 0 follow, 0 up)`. Nếu không có máy nào: `🌿 Nghỉ dưỡng sinh: Không có`.
2. **Bóc tách danh sách Bỏ qua (Follow & Upload Hook):**
   - Follow hook: Phân loại theo `fl_rest` (`organic-rest-day`), `fl_under10` (`under-10-videos`), và `fl_other`.
   - Upload hook: Phân loại theo `up_rest` (`organic-rest-day`), `up_novideo` (`video_not_rendered`, `missing_video_folder`), và `up_other`.
   - Không được gom máy dưỡng sinh vào `fl_error` hay `up_error` để tránh kích hoạt nhầm cảnh báo đỏ Farm Alert (>10 máy).
3. **Đồng bộ 4 vị trí:**
   - `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
   - `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/feed_session_watchdog.py`
   - `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`
   - `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`
   - Chi tiết xem tại `references/watchdog-organic-rest-reporting-format.md`.

## 16. Lazy XML Loading Cho Comment Peek Trên Deep Inspect Videos

**Triệu chứng:** Thống kê watchdog luôn báo `Đọc comment: 0 lượt / 1300 video (0.0%)` dù tính năng Comment Peek (20-35%) đã được cấu hình và bật cho video deep inspect.

**Root Cause:**
- Hàm `_maybe_peek_comments` đọc `xml_text = after_attempt.get("raw_xml")`.
- Luồng `_capture_step()` trả về `after` chỉ lưu đường dẫn file trên đĩa `after["xml_path"]` (để tối ưu RAM cho 40 workers song song), không giữ `raw_xml` trong RAM.
- Do đó `xml_text` luôn là `None`, tính năng xem lướt comment bị fail-silent 100% trên toàn farm.

**Chuẩn xử lý:**
- Nạp lười (lazy load) `raw_xml` từ `after["xml_path"]` ngay trước khi gọi `_maybe_peek_comments`:
  ```python
  if is_feed_session and is_deep_inspect_video:
      after["is_deep_inspect"] = True
      if not after.get("raw_xml") and after.get("xml_path"):
          try:
              from pathlib import Path
              xp = Path(str(after.get("xml_path")))
              if xp.is_file():
                  after["raw_xml"] = xp.read_text(encoding="utf-8", errors="ignore")
          except Exception:
              pass
      if _maybe_peek_comments(ctx, after, peek_rate_percent=session_comment_peek_rate):
          after["comment_peeked"] = True
  ```
- Kiểm chứng: `pytest python_runner/tests/test_feed_swipe_smoke.py -k "test_maybe_peek_comments"` và `test_comment_peek_logic.py` pass 100%. Chi tiết xem tại `references/comment-peek-xml-fallback-and-watchdog-upload-breakdown.md`.

## 17. Bóc Tách Chi Tiết Các Nhóm Bỏ Qua Upload Trên Watchdog (Tránh Nhãn "Khác")

**Triệu chứng:** Người vận hành thắc mắc khi thấy watchdog báo `Bỏ qua (79): Đang dưỡng sinh (17); Chưa render/thiếu video (3); Khác (59)`. Nhãn `Khác (59)` làm mất độ trong suốt vận hành.

**Chuẩn phân loại Upload Bỏ qua:**
- `Đã đăng trong ca (X)`: Các máy đã khởi chạy hoặc hoàn tất ở phiên trước (`already_uploaded_in_shift` / `already_uploaded`).
- `Đang ngâm cooldown/tuổi nick (X)`: Các máy chưa đủ tuổi đăng hoặc trong thời gian ngâm cooldown (`account_cooling_period`, `cooling_period`, `under_10_days`, `age_gate`).
- `Chưa xác thực ngày tạo nick (X)`: Các nick chưa đối soát được ngày tạo (`account_creation_date_unverifiable`).
- `Khác (X)`: Chỉ dành cho các trường hợp ngoại lệ hiếm gặp còn lại.
- Đồng bộ format trên cả 3 file watchdog (`hermes/scripts`, `Hermes/deploy`, `tiktok-luot nuoi acc/scripts`).

## 18. Kỷ Luật Watchdog Báo Cáo Xong E2E & Chống Bắn Lặp / Nuốt Header Phiên Sau

**Hiện tượng:** 
1. Watchdog bắn báo cáo dở dang lúc mới chạy 78/80 máy (ví dụ lúc 19:23), sau đó đến 21:41 lại bắn tiếp một bản báo cáo cùng phiên đó (khi đủ 80 máy).
2. Người vận hành tưởng "chưa thấy bắn báo cáo phiên 2", nhưng thực chất Phiên 2 đã bị nối chuỗi gộp chung bên dưới Phiên 1 trong một tin nhắn dài (>3.000 ký tự).

**Root Cause:**
- `can_report_session()` có logic ép chốt báo cáo khi quá `window_end_hm + 20m` bất kể batch runner vẫn đang chạy. Lần chốt sớm chưa kịp khóa state key vào `feed_session_reported.json`, dẫn đến tick sau quét lại thấy thư mục run có dữ liệu mới đủ máy lại xuất tiếp.
- Watchdog gom toàn bộ phiên hoàn tất vào mảng `messages` rồi `print("\n\n".join(messages))`, khiến người dùng đọc trên Telegram chỉ thấy banner đầu của Phiên 1.

**Quy chuẩn điều phối & xử lý:**
- **Điều tra trước khi kết luận:** BẮT BUỘC đọc và diff trực tiếp các file output `.md` tại `~/.hermes/cron/output/<job_id>/*.md` theo từng mốc giờ (chống đoán mò).
- **Nguyên tắc Xong E2E Mới Báo:** Watchdog chỉ được xuất báo cáo khi runner đã hoàn toàn kết thúc (`runner_busy == False`) hoặc toàn bộ máy dự kiến đã hoàn tất thật (`completed_expected_count >= expected_count and not has_unattempted_locked`). 
  - **Pitfall thứ tự điều kiện trong `can_report_session()`:** BẮT BUỘC đưa kiểm tra `completed_expected_count >= expected_count and not has_unattempted_locked: return True` lên ĐẦU HÀM, trước cả nhánh `now_hm < window_end_hm` và `now_hm >= window_end_hm`. Nếu để nhánh `now_hm >= window_end_hm` chặn `runner_busy` trước, khi cả 80 máy đã xong hoàn toàn nhưng runner wrapper chưa kịp dọn tiến trình sau giờ phiên, phiên sẽ bị kẹt không thể chốt báo cáo.
  ```python
  # 1. ĐẦU HÀM: Nếu tất cả máy dự kiến đã hoàn tất thật: chốt ngay kể cả runner_busy
  if completed_expected_count >= expected_count and not has_unattempted_locked:
      return True

  # 2. Khi đã qua window_end_hm: nếu là hôm nay, TUYỆT ĐỐI KHÔNG chốt khi runner vẫn đang bận (phải đợi xong hẳn)
  if is_today and now_hm >= window_end_hm:
      if runner_busy:
          return False
  ```
- **Pitfall điều hướng & tìm kiếm file trên Windows/MSYS:**
  - Tuyệt đối CẤM chạy `find /d` hoặc `search_files` quét toàn bộ ổ đĩa `/d` vì sẽ làm cạn kiệt budget timeout (180s) và blow session limit.
  - Công cụ `search_files` (ripgrep) có thể lỗi os error 3 khi nhận đường dẫn MSYS `/c/Users/...` dạng file đơn lẻ. Luôn ưu tiên dùng `read_file` với định dạng Windows backslash `C:\Users\...` hoặc Python snippet ngắn gọn để kiểm tra sự tồn tại và đọc code.
- **Tách riêng tin nhắn:** Mỗi phiên hoàn tất phải xuất thành tin nhắn độc lập hoặc claim dứt điểm từng phiên, không nối chuỗi gộp chung làm che khuất các phiên kế tiếp.
- Chi tiết xem tại `references/watchdog-duplicate-and-merged-session-pitfalls.md`.

## 19. Triage Lỗi Feed Diện Rộng: Hiệu Ứng Dây Chuyền Hàng Trống, Trần 8 Nick & Stale Locks

**Hiện tượng:** Người vận hành báo "Lướt feed fail gần 1 nửa" (ví dụ: chỉ 25/80 máy thành công). Thống kê sơ bộ có hàng chục máy không pass.

**Quy trình điều tra O(1):**
1. Đọc trực tiếp `run_manifest.json` trong `D:/Taadaa/runtime/kibe/live/<date>/row-<R>-<time>/<run_id>/`.
2. Kiểm tra `blocker_taxonomy_summary` và `multi_machine_summary` để tách các nhóm:
   - **`config-error` do hàng trống trong Excel:** `stop_reason: account row X is empty (no username) for machine Y, skipping`. Đây là **hiệu ứng dây chuyền** từ ca Reg bù / Reconcile trước đó bị fail (chưa có nick cho hàng đó).
   - **`skipped-device-locked` do khóa mồ côi (stale lock):** Tiến trình cũ kết thúc nhưng lock chưa kịp dọn. Kiểm tra PID và kích hoạt watchdog `reap-dead-owner-locks`.
   - **`MACHINE_FULL_8_ACCOUNTS` (tại ca Reg):** Switcher trên máy thật đã đủ 8 nick nhưng Excel bị trống. Cần JIT Reconcile quét Switcher đồng bộ lại Excel trước khi dispatch reg bù để tránh vi phạm trần 8 nick.
   - **Lỗi runtime thiết bị:** Mất focus sang launcher (`manual-needed`), capture invalid / mất session ATX, feed swipe timeout.
3. Chi tiết xem tại `references/cross-workflow-empty-row-and-stale-lock-triage.md`.

## 20. Xung Đột Chí Mạng: Cron Dọn Cache (`end-of-day-clear-tiktok-cache`) Bắn Phá Ca Nuôi Ban Đêm & Kỷ Luật An Toàn Maintenance Cron

**Hiện tượng:** Phiên lướt feed ban đêm (Ca 4, 01:50 - 02:53) bị rớt đồng loạt trên diện rộng: `TikTok focus lost to launcher`, `focused package unavailable`, `screen capture invalid`, `feed swipe command failed`.

**Root Cause:**
1. Job cron dọn dẹp cache cuối ngày đặt sai cú pháp: `*/10 1,2,3,4 * * *` (chạy mỗi 10 phút liên tục từ 1h đến 5h sáng) thay vì `0 4 * * *` (chỉ chạy 1 lần lúc 4h sáng).
2. Script dọn cache `cron_clear_tiktok_cache.py` chạy 40 worker song song mà KHÔNG kiểm tra trạng thái feed runner (`is_feed_runner_active()`). Khối `finally` gửi lệnh `am force-stop com.ss.android.ugc.trill; input keyevent KEYCODE_HOME;` trực tiếp đè lên các máy đang lướt feed.

**Quy tắc bất biến (Invariants):**
- **Cú pháp cron cuối ngày:** Bắt buộc dùng giờ cố định cụ thể `0 4 * * *`, cấm dùng khoảng lặp `*/10 1,2,3,4 * * *`.
- **Preflight Feed Runner Guard:** Toàn bộ maintenance cron chạm thiết bị (dọn cache, toggle wifi, reboot, restart app) BẮT BUỘC kiểm tra `is_feed_runner_active()`, nếu farm đang có ca nuôi thì silent skip ngay lập tức.
- Chi tiết xem tại `references/cache-cleanup-cron-feed-conflict-triage.md`.

## 21. Tiêu Chuẩn Báo Cáo Tiến Độ Upload Trên Watchdog Farm (Chống Gom Cục "Khác")

**Vấn đề & Feedback Người Vận Hành:**
Báo cáo watchdog cũ hiển thị:
```text
• Đăng Video (2/2 - 25 video đã đăng):
  + Success (25): 2, 4, 6, 11...
  + Timeout/Quá giờ (0): Không có
  + Lỗi script/xác minh (1): 77
  + Bỏ qua (42): Đang dưỡng sinh (16); Khác (26)
```
Gây ức chế vì: không rõ 25 máy trên tổng số bao nhiêu máy đủ điều kiện, không rõ từng máy đang ở video số mấy trong chu kỳ (tiến độ đến đâu), và gom 26 máy vào nhãn mù mờ `Khác (26)`.

**Quy chuẩn bắt buộc cho Watchdog & Báo Cáo:**
1. **Mẫu số hoàn thành:** Bắt buộc có dạng `{up_success}/{up_eligible} máy đủ điều kiện [{percent}%]`.
2. **Lũy kế Video Number:** Từng máy thành công phải gắn số video: `M<M>(v<N>)` (ví dụ: `M2(v1), M4(v2)...`).
3. **Chi tiết lỗi:** Máy lỗi phải kèm tóm tắt nguyên nhân: `M77 (Lỗi UI xác minh)`.
4. **Bóc tách 100% nhóm Bỏ qua an toàn:** Tuyệt đối không dùng nhãn "Khác" mà phải phân rã thành:
   - `Nghỉ dưỡng sinh ({N} máy): M...`
   - `Nick ngâm < 10 ngày ({N} máy): M...`
   - `Chưa có video render ({N} máy): M...`
   - `Hủy do feed fail ({N} máy): M...`
5. Chi tiết xem thêm tại `references/watchdog-upload-progress-and-skip-breakdown-standard.md`.

## 22. Case 179: Bóc Tách feed_counts Và Tính Tỷ Lệ % Thả Tim Từng Tab Trên Watchdog

**Hiện tượng:** Báo cáo Watchdog ghi nhận: `+ Thả tim: 146 tim / 1217 video (12.0%) [Đề xuất: 128 (0.0%) | Bạn bè: 14 (0.0%) | Following: 4 (0.0%)]`. Người vận hành thấy số tim có tăng (14 tim Bạn bè) nhưng % luôn bằng `0.0%`.

**Root Cause:**
- Script `feed_session_watchdog.py` đếm được `likes_map` nhưng **quên bóc tách dict `feed_counts`** từ `summary.txt`.
- Hàm `merge_machine_result` không merge trường `feed_counts`.
- Mẫu số `tot_fr_swipes`, `tot_fy_swipes`, `tot_fl_swipes` bằng 0 dẫn tới fallback `0.0%`.

**Giải pháp:**
1. Trích xuất `feed_counts_map` trong đoạn đọc per-machine `summary.txt`.
2. Bổ sung logic merge `feed_counts` vào `merge_machine_result`.
3. Đồng bộ cả 2 bản `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` và `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`.
4. Chi tiết xem tại `references/case179-watchdog-feed-counts-tab-like-percentage-fix.md`.

## 23. Case 180: Loại Bỏ Màn Gợi Ý Rỗng Ra Khỏi Mẫu Số feed_counts & Mở Rộng Từ Khóa Fallback For You

**Hiện tượng & Thắc mắc Người Vận Hành:**
- Watchdog báo tỉ lệ like tab Bạn bè cực thấp: `Bạn bè: 2 (8.7%)`.
- Người vận hành chất vấn: *"Ủa màn rỗng thì mắc gì tính vào mẫu số để r chia ra % bé?"*

**Root Cause:**
1. TikTok cập nhật cụm từ UI màn gợi ý kết nối bạn bè / danh bạ khiến `_FRIENDS_FEED_CONTENT_TERMS` cũ bị lọt lưới.
2. `_feed_action_counts` cộng dồn mù quáng mọi lượt swipe vào `feed_counts[feed_type]`, khiến 24 lượt swipe trên danh sách liên hệ rỗng bị tính làm mẫu số video bạn bè.

**Giải pháp chuẩn (Commit acb7989):**
1. Mở rộng `_FRIENDS_FEED_CONTENT_TERMS`: thêm `"Kết nối với bạn bè để xem bài đăng"`, `"Tìm các liên hệ của bạn"`, `"Kết nối với liên hệ trong danh bạ"`, `"Kết nối với bạn bè trên Facebook"`.
2. Gắn nhãn `after["is_empty_feed_fallback"] = True` khi kích hoạt fallback.
3. Trong `_feed_action_counts`: chỉ đếm `feed_counts[feed_type] += 1` khi `not row.get("is_empty_feed_fallback") and not _has_friends_feed_content(row)`.
4. Chi tiết xem tại `references/case180-empty-friends-suggestion-feed-counts-denominator-fix.md`.

## 24. Case 181: Khắc Phục Lỗi Watchdog Bỏ Sót Máy Trống Slot Do Bỏ Qua run_manifest.json

**Hiện tượng:** Watchdog gửi báo cáo `Tổng máy xử lý: 58 máy`, `Trống slot/chưa có nick (0): Không có` trong khi alert Preflight Reg bù ngay bên dưới lại báo `Tổng máy thiếu: 22 (cần reg bù)`.

**Root Cause:**
1. Khi gặp máy trống nick ở row đang chạy, runner safe-skip trước khi chạm thiết bị nên **không tạo thư mục con `machines/machine_X/`** và không sinh per-machine `summary.txt`. Trạng thái của 80 máy chỉ nằm trong `multi_machine_summary` của root `run_manifest.json`.
2. `parse_run_all` chỉ tìm kiếm thư mục `machines/machine_X/`, bỏ qua hoàn toàn `run_manifest.json`.
3. Mẫu số kỳ vọng đọc từ config runtime vốn chỉ có 58 máy đã có nick, khiến watchdog coi 58 máy là 100% phiên và tính `empty = 0`.

**Giải pháp chuẩn:**
1. Trong `parse_run_all`: Bổ sung parse `multi_machine_summary` từ file `run_manifest.json` ở root `run_dir` để nhặt đủ các máy bị `skipped-empty`.
2. Bổ sung `get_all_fleet_machines()` để đối soát trên toàn bộ 80 máy của Farm. Bất kỳ máy nào không có nick ở row đang chạy đều được xếp vào `Trống slot/chưa có nick`.
3. Đồng bộ đủ 4 vị trí: `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`, `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/feed_session_watchdog.py`, `D:/Taadaa/Hermes/deploy/hermes-home/scripts/feed_session_watchdog.py`, và `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`.
4. Chi tiết xem tại `references/case181-watchdog-empty-slot-manifest-parse-fix.md`.

## 25. Kỷ Luật Logging Trong Watchdog & File Đồng Bộ (Tránh `except Exception: pass` Mù)

**Vấn đề:**
- Các khối đọc file cấu hình (`SOURCE_CONFIG` trong `get_all_fleet_machines`) và parse artifacts (`run_manifest.json` trong `parse_run_all`) dùng `except Exception: pass` nuốt toàn bộ lỗi.
- Khi file JSON hỏng hoặc I/O bị khóa, watchdog âm thầm fallback sai trạng thái mà không có log warning cảnh báo để truy vết.

**Quy chuẩn Logging & Exception Handling:**
- Thay thế `except Exception: pass` bằng xử lý phân lớp rõ ràng:
  - Bắt cụ thể `(json.JSONDecodeError, OSError)` để ghi log `logger.warning(...)` có ngữ cảnh cụ thể.
  - Khối `except Exception as exc:` bắt các lỗi bất thường còn lại và log rõ `exc`.
- **Lưu ý Pyright / Scoping trong script:**
  - Kiểm tra import `json` ở đầu file. Tránh import lặp lại `import json` cục bộ trong các khối bên dưới nếu có thể gây biến cục bộ unbound variable (`Pyright: reportPossiblyUnboundVariable`).
- **Đồng bộ song song:** Khi cập nhật logging/xử lý trong watchdog, luôn đồng bộ cả file chính `scripts/feed_session_watchdog.py` và wrapper cron `scripts/hermes_cron/feed_session_watchdog.py`.

## 26. Dual-Cluster Watchdog Farm Reporting (Kibe Máy 1-80 & Admin Máy 201-280) & 3-Way Parity

**1. Cấu hình Dual-Cluster:**
- Khai báo danh sách `CLUSTERS` bao gồm `kibe` (`runtime_root`: `D:\Taadaa\runtime\kibe`, fleet `1..80`) và `admin` (`runtime_root`: `D:\Taadaa\runtime\admin`, fleet `201..280`).
- Mỗi cluster quản lý thư mục `live` riêng và workbook tài khoản riêng `D:\OneDrive\TaadaaData\<cluster>\taikhoan_run_safe.xlsx`.

**2. Đọc Dynamic Expected Machines Từ Workbook `taikhoan_run_safe.xlsx`:**
- Sử dụng `openpyxl` với `read_only=True` duyệt sheet `Accounts` (Cột A: `May`, Cột C: `ID`).
- Máy có 8 slot tương ứng các row. Máy thuộc `expected_machines` khi và chỉ khi slot `row_num - 1` có ID hợp lệ.
- Fallback an toàn: Trả về toàn bộ danh sách fleet của cluster nếu workbook không thể đọc hoặc không tồn tại.

**3. Format Báo Cáo Telegram Song Song:**
- Header chung cho toàn phiên: `📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})`.
- Từng cluster có dữ liệu chạy trong khung giờ phiên xuất hiện theo khối riêng:
  ```text
  🏢 【FARM KIBE - MÁY 1-80】
  • Tổng máy xử lý: ...
  ...
  🏢 【FARM ADMIN - MÁY 201-280】
  • Tổng máy xử lý: ...
  ```

## 28. reconcile_cluster_following: Pitfall fetchone() vs fetchall() Khi Mock Cursor

**Triệu chứng:** Test `test_reconcile_matches` fail với:
```
AssertionError: False is not true
WARNING reconcile_cluster_following: lỗi kết nối/đọc db: '>' not supported between instances of 'MagicMock' and 'int'
```

**Root Cause:** Hàm `reconcile_cluster_following` dùng 3 query riêng biệt với mix `fetchone()` / `fetchall()`. Khi unittest.mock mock `cursor`, `fetchone()` trả về `MagicMock` (không None), nhưng code sau đó cố so sánh `MagicMock[0] > 0` (ví dụ `latest_fl = latest_row[0] or 0`) → crash type error. Cụ thể: `fetchall()` trả về list Python thật (đã cài `mock_cursor.fetchall.return_value = [...]`), nhưng `fetchone()` trả về một `MagicMock` mới, không phải tuple, khiến `latest_row[0]` không phải int.

**Giải pháp chuẩn:** Hợp nhất thành 2 query, BẮT BUỘC dùng `fetchall()` cho mọi query bên trong `reconcile_cluster_following`:
```python
# Query 1: Lấy 2 bản ghi gần nhất (dùng fetchall, không fetchone)
cur.execute("""
    SELECT following, timestamp FROM snapshots
    WHERE LOWER(username) = LOWER(?)
    ORDER BY timestamp DESC, id DESC LIMIT 2
""", (u,))
pair = cur.fetchall()
latest_row = pair[0] if len(pair) >= 1 else None

# Query 2: Tìm baseline theo session_start_iso (dùng fetchall, không fetchone)
if latest_row and session_start_iso:
    cur.execute("""
        SELECT following, timestamp FROM snapshots
        WHERE LOWER(username) = LOWER(?) AND timestamp <= ?
        ORDER BY timestamp DESC, id DESC LIMIT 1
    """, (u, session_start_iso))
    b_rows = cur.fetchall()
    if b_rows:
        baseline_row = b_rows[0]

# Fallback baseline từ cặp đôi đã fetch sẵn
if latest_row and not baseline_row and len(pair) >= 2:
    baseline_row = pair[1]
```

**Lý do:** `fetchall()` trả về Python list thật ngay cả khi mock chỉ set `return_value` một lần, còn `fetchone()` trả về `MagicMock` mới mỗi lần gọi và phá vỡ comparison.

**Workflow đồng bộ và verify:**
1. Patch `C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py`
2. Sync sang `D:/Taadaa/tiktok-luot nuoi acc/scripts/feed_session_watchdog.py` bằng `cp`
3. Chạy pytest: `pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_feed_session_watchdog.py" -q`
4. Chạy CANARY_FINAL_VERIFY: import `reconcile_cluster_following, CLUSTERS`, gọi với cluster thật + db thật, xác nhận output dạng `+ Đối soát TikTok Web (+N Following thật - Khớp 100%...)`

**Kết quả:** 10/10 tests passed, CANARY output: `M32 (@ng.kim.ngn469): script báo 1 | web tăng +1 (Khớp 100%)`.

## 27. Case 184: Mẫu Số feed_counts Bỏ Sót Fast Swipe Khiến Tỷ Lệ % Thả Tim Từng Tab Cao Ảo

**Hiện tượng & Nghi vấn:**
- Watchdog báo: `+ Thả tim: 140 tim / 1159 video (12.1%) [Đề xuất: 132 (32.3%) | Bạn bè: 8 (57.1%) | Following: 0 (0.0%)]`.
- Tỷ lệ tổng ngoài ngoặc là `12.1%` (140 tim / 1159 video) — hoàn toàn an toàn và nằm trong dải phân phối tự nhiên.
- Nhưng tỷ lệ trong ngoặc vuông của tab Đề xuất vọt lên `32.3%` và Bạn bè `57.1%`, khiến người vận hành nghi ngờ bot thả tim bất thường hoặc chỉ tính trên các lượt dump XML.

**Root Cause:**
- Trong `feed_swipe_smoke.py`, các lượt Fast Swipe (lướt nhanh không dump XML) được gán `action: "fast_swipe"`.
- Hàm `_feed_action_counts()` trước đây chỉ lọc `if row.get("action") == "swipe" and feed_type in feed_counts: feed_counts[feed_type] += 1`.
- Vì bỏ sót nhãn `"fast_swipe"`, toàn bộ ~737 lượt lướt nhanh bị loại khỏi mẫu số của từng tab (`tot_fy_swipes`, `tot_fr_swipes`). Mẫu số bị co cụm về chỉ còn ~408 video Deep Inspect (có dump XML), dẫn đến phép chia `132 / 408 = 32.3%`.

**Giải pháp (Patch Contract):**
- Trong `python_runner/flows/feed_swipe_smoke.py`:
  Mở rộng điều kiện đếm: `if row.get("action") in ("swipe", "fast_swipe") and feed_type in feed_counts:`.
- Trong `python_runner/tests/test_feed_swipe_smoke.py`:
  Bổ sung assertion xác nhận `{"action": "fast_swipe", "feed_type": "for-you"}` được cộng dồn đúng vào `feed_counts["for-you"]`.
- Chi tiết xem tại `references/case184-fast-swipe-action-counts-denominator-leak.md`.
## 4. Quản Lý Trạng Thái Session & 3-Way Parity

- **Graceful Cluster Absence:** Trong thực tế, một trong hai cluster (ví dụ Admin) có thể chưa khởi tạo thư mục `live` (`os.path.exists(cluster["live_root"]) == False`). Vòng lặp `main()` và bước gom `dates_to_check` BẮT BUỘC kiểm tra sự tồn tại của thư mục trước khi `os.listdir`, tránh crash `FileNotFoundError`.
- **State File:** `D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json` (dùng chung cho việc claim session key `{date}_ca{ca}_phien{phien}`).
- **3-Way Parity Invariant:** Mọi chỉnh sửa watchdog BẮT BUỘC phản ánh đồng nhất trên cả 3 file:
  1. `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py`
  2. `D:\Taadaa\Hermes\deploy\hermes-home\scripts\feed_session_watchdog.py`
  3. `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\feed_session_watchdog.py`
- Kiểm tra cú pháp sau khi ghi: `python -m py_compile <path>` cho cả 3 đường dẫn.
- Chi tiết xem tại `references/dual-cluster-watchdog-reporting-and-parity.md`.


- `references/case181-watchdog-empty-slot-manifest-parse-fix.md` — Case 181: Khắc phục lỗi Watchdog bỏ sót máy trống slot (0 máy ảo) do bỏ qua run_manifest.json khi runner safe-skip, đối soát toàn diện 80 máy fleet.
- `references/dual-cluster-watchdog-reporting-and-parity.md` — Dual-Cluster Farm Watchdog (Kibe Máy 1-80 & Admin Máy 201-280), dynamic expected machines từ taikhoan_run_safe.xlsx và kỷ luật 3-Way Parity.
- `references/dual-cluster-alert-scope-and-upload-failure-triage.md` — Triage phạm vi cảnh báo Farm Alert Dual-Cluster (Kibe Máy 1-80 vs Admin Máy 201-280 vs Toàn Farm 160 máy), quy trình điều tra O(1) lỗi Upload hàng loạt và phân loại 4 nhóm nguyên nhân (chốt an toàn POST_SUBMISSION_UNKNOWN vs switcher vs phần cứng).
- `references/case182-prepare-tiktok-focus-zero-delay-storm-triage.md` — Case 182: Triage lỗi diện rộng "prepare-tiktok failed to focus TikTok after launch" (53 máy rớt) do Screen ON + TouchWiz animation bận khiến monkey bị nuốt, kết hợp zero-delay polling storm.
- `references/case183-creator-lifecycle-upload-gate-and-organic-rest.md` — Case 183: Creator Lifecycle Upload Gate: Cho phép đăng video trong ngày Dưỡng Sinh (chỉ tắt Follow), rút ngắn thời gian tích lũy 10 video từ 30 ngày xuống 20 ngày.
- `references/case184-fast-swipe-action-feed-counts-denominator-drift.md` — Case 184: Lệch mẫu số feed_counts từng tab do Fast Swipe mang action "fast_swipe" khiến % like trong ngoặc bị cao ảo (~32%), trong khi tỉ lệ tổng ngoài ngoặc vẫn chuẩn (~12%).
- `references/case185-upload-skip-triage-and-creation-date-gate.md` — Case 185: Triage hiện tượng bỏ qua đăng video diện rộng ở Row >= 5 (Kibe dính chốt Fail-Closed account_creation_date_unverifiable do thiếu ngày tạo trong Excel, Admin thiếu nick Row 5 và chưa render video). Người dùng chỉ đạo chính sách: nick để trống ngày tạo coi như nick cũ reg lâu rồi, cho phép đăng luôn (True, "ok").
- `references/case186-natural-follow-watch-time-gate-and-watchdog-telemetry.md` — Case 186: Watch Time Gate (ngâm video 8-12s trước khi tap follow) chống nhả follow (Silent Action Block) & bổ sung telemetry Follow tự nhiên trên báo cáo Watchdog theo ca.
- `references/case187-feed-failure-triage-empty-following-and-stranger-profile.md` — Case 187: Triage 5 cụm lỗi Feed Session Farm (Following tab rỗng false-positive network, kẹt Profile người lạ do popup đề xuất, vision-XML drift ở Profile preflight).
- `references/empty-following-feed-and-foreign-profile-recovery.md` — Empty Following Feed False Positive (0 following) & Foreign Profile Escape Recovery.
- `references/case188-profile-verification-captcha-false-alarm-and-switcher-missing-triage.md` — Case 188: Phân biệt lỗi mất focus khi verify profile với Captcha/Challenge thật (tránh false alert `CẢNH BÁO XÁC MINH`), và triage lỗi `ACCOUNT_MISSING` do bảng Switcher chưa kịp bung trên S7.
- `references/case189-openblas-memory-allocation-failure-high-core-host.md` — Case 189: OpenBLAS Memory allocation failure trên host Dual CPU 56 cores do openpyxl nạp numpy/scipy DLL trong feed_session_watchdog.py & mô hình phòng vệ 3 lớp.
- `references/case190-zombie-runner-process-watchdog-deadlock.md` — Case 190: Tiến trình Runner Zombie kẹt luồng chặn Watchdog báo cáo ca nuôi (`runner_busy` Deadlock) và quy trình dọn dẹp O(1).
- `references/case191-screen-timeout-25d-and-remote-teardown-drift.md` — Case 191: Sáng màn hình hàng loạt do uiautomator ép timeout 25 ngày (2147483647) & treo app TikTok do fallback teardown thiếu Remote Host.

## 32. Case 189: OpenBLAS Memory Allocation Failure Trên Host Dual CPU 56 Cores & Phòng Vệ 3 Lớp (24/09/2026)

**Hiện tượng:** Watchdog `tiktok-feed-session-watchdog` crash đột ngột với exit code 1:
`OpenBLAS error: Memory allocation still failed after 10 retries, giving up.` Không có Python traceback.

**Root Cause:**
- Host có 56 logical processors (`cpu_count = 56`).
- `feed_session_watchdog.py` import `openpyxl` kéo theo numpy DLL `libscipy_openblas64`.
- OpenBLAS mặc định xin cấp phát bộ nhớ ảo cho cả 56 threads. Khi tải farm cao và bộ nhớ bị phân mảnh, `VirtualAlloc` thất bại sau 10 lần thử và gọi thẳng `exit(1)` ở tầng C.

**Mô hình phòng vệ 3 lớp (3-Tier Defense):**
1. **Script Level:** Đặt `os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")` (cùng MKL, OMP, NUMEXPR) ngay dòng đầu tiên của `feed_session_watchdog.py` TRƯỚC mọi lệnh import thư viện khác.
2. **Scheduler Level:** Trong `Hermes/cron/scheduler.py` (`_run_job_script`), tự động tiêm `OPENBLAS_NUM_THREADS="1"` vào `cron_env` của subprocess cho toàn bộ 33 cronjobs.
3. **Host OS Level:** Cấu hình biến môi trường User Windows `OPENBLAS_NUM_THREADS=1` qua PowerShell.
- Chi tiết xem tại `references/case189-openblas-memory-allocation-failure-high-core-host.md`.

## 29. Case 186: Watch Time Gate Cho Follow Tự Nhiên & Telemetry Follow Tự Nhiên Trên Watchdog Farm (23/09/2026)

**Hiện tượng & Vấn đề:**
- Tính năng Follow Tự Nhiên khi lướt feed từng bị tắt do người vận hành phát hiện nhiều nick bấm nút Follow trên UI xong thì bị TikTok âm thầm hủy (nhả follow).
- Đồng thời, báo cáo Watchdog theo ca (`feed_session_watchdog.py`) chỉ thống kê "Follow chéo" (chạy sau ca lướt qua Mode 1/Mode 2), hoàn toàn thiếu số liệu về số lượt và tỷ lệ % Follow tự nhiên thực tế diễn ra trong lúc lướt feed.

**Root Cause:**
- Khi lướt feed For You, nếu roll trúng tỷ lệ follow, script tìm nút Follow và tap ngay lập tức (sau 1–2s). Hệ thống chống bot của ByteDance gắn cờ đây là hành vi spam/bot và âm thầm drop action trên server.
- Watchdog không bóc tách `follow_counts` per-machine từ `summary.txt`.

**Giải pháp chuẩn (Case Fix):**
1. **Watch Time Gate (`feed_swipe_smoke.py`):** Trong `_maybe_follow_video()`, chèn thời gian dừng ngâm video ngẫu nhiên `8.0s – 12.0s` (`time.sleep(random.uniform(8.0, 12.0))`) trước khi tap nút Follow. Giúp TikTok ghi nhận watch-time đầy đủ và giữ lượt follow vĩnh viễn trên server.
2. **Telemetry Watchdog (`feed_session_watchdog.py`):** Bóc tách `follow_counts` từng tab (`for-you`, `following`, `friends`), merge tích lũy, tính tỷ lệ `tot_nat_follow_rate`, và xuất dòng báo cáo:
   `+ Follow tự nhiên: {tot_nat_follows} lượt / {tot_swipes} video ({tot_nat_follow_rate:.1f}%) [Đề xuất: {tot_fy_nat_follows} | Bạn bè: {tot_fr_nat_follows}]` ngay dưới dòng Thả tim.
3. **Telemetry & Ý nghĩa chỉ số "Follow tự nhiên [Đề xuất: X | Bạn bè: Y]":**
   - **Bản chất:** Khác với Follow chéo (tìm nick cụ thể trong danh sách theo Mode 1/2), *Follow tự nhiên (Organic Follow)* là bot ngẫu nhiên bấm Follow tác giả video ngay khi đang lướt feed (`_maybe_follow_video`). Mục đích là giả lập hành vi người dùng thật, tạo đồ thị tương tác tự nhiên và làm loãng chuỗi follow chéo tránh thuật toán TikTok quét ra bot farm.
   - **Tab Đề xuất (For You):** Video xu hướng do thuật toán phân phối. Tỷ lệ follow ~5% (hoặc ~20% với Deep Inspect), có Watch Time Gate ngâm 8-12s trước khi tap.
   - **Tab Bạn bè (Friends):** Ngoài video bạn bè thân thiết, tab này gợi ý "Bạn bè của bạn bè", "Người bạn có thể biết" kèm nút Follow/Kết bạn. Bot lướt qua nếu roll trúng tỷ lệ sẽ bấm follow tự nhiên.
   - **Tab Following:** Luôn = 0 vì toàn bộ kênh ở tab này đã follow từ trước.
4. **Triage Hiểu Lầm: Vì sao có Follow tự nhiên dù Follow chéo ra 0 lượt / Bỏ qua:**
   - Cả Follow tự nhiên và Follow chéo đều dùng chung Gate an toàn: `video_count >= 6` và không phải ngày dưỡng sinh (`_is_organic_rest`).
   - Nếu trong phiên có máy đủ điều kiện (ví dụ Row 8 có các máy M19, M51, M56, M63 đạt 6 video), các máy này **vẫn tham gia roll Follow tự nhiên** khi lướt feed For You.
   - Sau khi lướt feed xong, bước Follow chéo chạy: Nếu máy bị nhả follow (`FOLLOW_FAILED` như M19), dính timeout (như M56), hoặc gặp anchor 0 following (`zero-following-skip-v2` như M51, M63, M59, M77), kết quả follow chéo sẽ về 0.
   - **Lưu ý:** Việc Follow chéo ra 0 lượt **hoàn toàn không có nghĩa là không máy nào đủ điều kiện video**; mà là máy đủ điều kiện video đã roll follow tự nhiên trên feed, còn follow chéo bị skip/revert bởi cơ chế an toàn anchor/runtime.
5. Chi tiết xem tại `references/case186-natural-follow-watch-time-gate-and-watchdog-telemetry.md`.

## 30. Case 187: Triage 5 Cụm Lỗi Feed Session Farm & Cơ Chế Soft-Fallback Tab Following (23/09/2026)

**Hiện tượng & Vấn đề:**
- Phiên lướt feed Row 3 (14:03) có tỷ lệ fail lên tới 28.75% (23/80 máy), tiệm cận ngưỡng RED ALERT 30% của Watchdog.
- Không phải do một lỗi duy nhất mà do 4 cụm lỗi logic runner cộng hưởng với sự cố mất kết nối phần cứng.

**5 Cụm nguyên nhân cốt lõi:**
1. **Tab Following rỗng / False-positive Network Error (M33, M41, M70, M72, M75):** Nick mới follow ít kênh (hoặc 0 following), khi chuyển sang tab Following gặp màn hình trống / retry marker ("Đã xảy ra lỗi | Vui lòng thử lại. | Thử lại"). Runner nhận diện nhầm marker UI này thành `manual-needed:network` và ngắt cả phiên thay vì quay lại lướt FYP.
2. **Kẹt Profile người lạ do Pop-up Đề xuất / Follow Back (M17, M23, M25, M76):** Pop-up gợi ý bạn bè điều hướng sang trang cá nhân của người khác (có nút "Follow lại", "Nhắn tin"), khiến runner không tìm thấy nút "Hồ sơ" chính chủ ở đáy, dính lỗi `navigation target profile not found in XML` và 0 swipes.
3. **Vision & XML Drift ở Profile Preflight (M14, M42):** XML xác nhận đã ở Profile chính chủ nhưng Image classifier nhận diện sai đường gạch header thành underline tab Following, dẫn đến `screenshot_xml_mismatch` và kẹt lỗi `known TikTok screen`.
4. **Switcher thiếu nick & Reconcile Timeout (M32):** Nick workbook chưa có trên máy thật, subprocess login tự động timeout 300s.
5. **Rớt ADB & Wi-Fi Router Proxy (M5, M46, M56, M71, M74, M79):** Đứt kết nối vật lý USB hub hoặc rớt sóng Wi-Fi AP.

**Quy chuẩn xử lý & Invariant bắt buộc (User chốt 2026-09-23):**
- **CẤM BỎ TAB FOLLOWING TỪ ĐẦU:** Dù nick có 0 following, bot VẪN BẮT BUỘC tap vào tab Following bình thường theo tỷ lệ phân bổ tự nhiên (mô phỏng hành vi người dùng thật). CẤM tự ý gán tỷ lệ Following = 0% để né tab.
- **CƠ CHẾ VÀO XONG TỰ QUAY VỀ FEED (Graceful Fallback on Device):**
  - Khi đã bấm vào tab Following, nếu gặp màn hình rỗng (`"manual-needed:network"`, `"manual-needed:empty"`, `"manual-needed:retry"` do nick chưa follow ai / kênh chưa đăng clip):
  - Bot BẮT BUỘC thực hiện hành động tap ngược lại tab **"Đề xuất" (For You)** qua `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FOR_YOU))`.
  - Đánh dấu trạng thái `confirm["status"] = ExitStatus.DEGRADED.value`, `confirm["safety_status"] = "ok"`, log warning và reset `videos_until_tab_decision = random.randint(5, 10)` để tiếp tục lướt hoàn thành 100% quota video trên For You, tuyệt đối không ngắt phiên.
- **THOÁT PROFILE NGƯỜI LẠ:** Bổ sung `is_foreign_profile` trong `calibrate_screens.py` để mở khóa chuỗi `KEYCODE_BACK`, giúp bot lùi về Home feed an toàn khi bị pop-up điều hướng sang trang cá nhân người khác.
- **XML PRECEDENCE:** Trong Profile Preflight, khi XML đã xác nhận profile chính chủ (`_profile_identity_from_profile_attempt` hoặc `xml_detected_screen == "profile"`), cấm classifier ảnh ghi đè thành drift.

**Kiểm chứng:** Chạy `D:/Taadaa/python-envs/automation/Scripts/pytest "D:/Taadaa/tiktok-luot nuoi acc/python_runner/tests/test_classifier.py" -q`.
- Chi tiết và code anchors xem tại `references/case187-feed-failure-triage-empty-following-and-stranger-profile.md`.

## 31. Case 188: False Alarm Captcha do Substring 'verification' & Triage 'ACCOUNT_MISSING' Switcher trên S7 (23/09/2026)

**1. False Alarm Captcha do từ khóa 'profile verification' (M13):**
- **Hiện tượng:** Watchdog phát cảnh báo đỏ `⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Máy M13: profile verification navigation-failed: TikTok focus lost`.
- **Root Cause:** Máy đã lướt trọn vẹn 16/16 video trên FYP. Cuối phiên khi vào bước `verify_profile` kiểm tra nick thì TikTok mất focus về launcher (`failed: TikTok focus lost`). Watchdog trong `batch_aggregator.py` quét bare substring `verification` nên gắn nhãn nhầm vào `CHALLENGE_KEYWORDS`.
- **Kỷ luật xử lý:** Kiểm tra `summary.txt` thấy `swipe_count == 16`, giải tỏa ngay cảnh báo Captcha cho User; watchdog cần exclude các cụm nội bộ `profile verification`, `preflight verification`, `proxy verification`.

**2. Báo động nhầm Mất phiên do Switcher chưa kịp bung trên S7 (M53):**
- **Hiện tượng:** Báo lỗi P0 `manual-needed:account-switcher-missing-expected: expected account not found in account switcher` cho nick Row 5 (`mgpovhrgnnq`).
- **Root Cause:** Trên Samsung S7 / TikTok 47.x, tiến trình dump UI XML bị OOM-kill (`ATX_SESSION_EMPTY_XML` / `SHELL_EXIT_137`). Màn hình thực tế vẫn đứng ở Profile root của nick cũ (Row 3), Bottom Sheet `Chuyển đổi tài khoản` chưa bung ra. Hàm `select_exact_account` cuộn màn hình mù nhưng chỉ cuộn grid video Profile, dẫn tới raise `ACCOUNT_MISSING`.
- **Kỷ luật phục hồi:** Soi screencap xác nhận màn hình; tự động chạy Fast Targeted Login:
  `python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss` (kèm `--allow-parent-lock` nếu gọi từ feed session); chụp ảnh nghiệm thu `m<STT>_login_verified.png` TRƯỚC khi teardown.
- Chi tiết xem tại `references/case188-profile-verification-captcha-false-alarm-and-switcher-missing-triage.md`.

## 33. Case 190: Tiến Trình Runner Zombie Kẹt Luồng Chặn Watchdog Báo Cáo Ca Nuôi (runner_busy Deadlock) (24/09/2026)

**Hiện tượng:** 
- Quá giờ ca nuôi (ví dụ: đã xong cả Ca 1 và Ca 2 lúc 16:00+) nhưng Telegram không nhận được bất kỳ báo cáo tổng kết phiên nào từ `feed_session_watchdog.py`. Người vận hành thắc mắc *"sao không thấy báo cáo ca nuôi acc nữa hay là do chưa hết ca?"*.
- Kiểm tra file state `feed_session_reported.json` thấy các session key trong ngày chưa được ghi nhận.

**Root Cause:**
1. Tiến trình `run-feed-session.ps1` hoặc `run_tiktok.py` (multi-machine-feed-session) đã hoàn thành lượt chạy và ghi đầy đủ `run_manifest.json` trong runtime live directory.
2. Tuy nhiên, tiến trình cha/con Python hoặc PowerShell bị kẹt luồng (zombie process: 0% CPU, 0 network connection, threads không tự hủy hết).
3. `feed_session_watchdog.py` có guard:
   `runner_busy = is_feed_runner_active()`
   Và trong `can_report_session()`:
   `if is_today and runner_busy: return False`
   Điều này khiến watchdog tưởng rằng farm vẫn đang bận chạy ca và tự động hoãn (silent hold) toàn bộ báo cáo trong ngày để tránh chốt phiên non.

**Quy trình chẩn đoán O(1) & Khắc phục chuẩn:**
1. **Kiểm tra tiến trình kẹt:**
   `powershell "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*run_tiktok*' -or $_.CommandLine -like '*run-feed-session*' } | Select-Object ProcessId, CreationDate, CommandLine"`
2. **Đối chiếu artifact:** Đọc `run_manifest.json` tại `D:\Taadaa\runtime\<cluster>\live\<date>\row-X-<time>\<run_id>\run_manifest.json` xác nhận `end_time` đã có từ lâu và phiên đã kết thúc.
3. **Kiểm tra tài nguyên:** Xác nhận PID đó 0% CPU, không giữ socket mạng và không giữ lock trong `~/.codex/device-locks/`.
4. **Dọn dẹp tiến trình zombie:** `powershell "Stop-Process -Id <PIDs> -Force"`
5. **Xả báo cáo:** Chờ tick cron 5 phút tiếp theo hoặc chạy `python C:/Users/Kibe/AppData/Local/hermes/scripts/feed_session_watchdog.py` để watchdog xả báo cáo các phiên hoàn tất về Telegram.
- Chi tiết xem tại `references/case190-zombie-runner-process-watchdog-deadlock.md`.

## 34. Case 191: Sáng Màn Hình Hàng Loạt Do uiautomator Ép Timeout 25 Ngày & Treo App TikTok Do Teardown Thiếu Remote Host (24/09/2026)

**Hiện tượng:** 
- Toàn bộ dàn máy Farm (cả cụm Admin máy 201-280 lẫn Kibe máy 1-80) đồng loạt bị mở sáng màn hình rực sáng, ngâm hàng giờ không tự tắt sau 10 phút nhàn rỗi dù farm đã cấu hình chuẩn 10 phút tự tắt màn.
- Hàng loạt máy (như Máy 220 Admin) bị treo nguyên ứng dụng TikTok trên màn hình, không tự động đóng app và không về HOME launcher sau khi kết thúc phiên.

**Root Cause:**
1. **Ép sáng 25 ngày:** Trong lúc nuôi feed/recovery, khi APK test của `uiautomator` được kích hoạt (`/uiautomator`), mã Java bên trong tự động set `screen_off_timeout = Integer.MAX_VALUE` (`2147483647` ms = 24.85 ngày). Khối `finally: teardown` trong `multi_machine_feed_session.py` hoàn toàn thiếu bước set trả lại `600000` (10 phút) và `stay_on_while_plugged_in = 0`.
2. **Teardown Fallback thiếu Remote Host:** Khi socket Remote ADB (`192.168.110.119:5037`) bị nghẽn làm `child_ctx.adb` timeout, fallback `_force_stop_tiktok_and_home` dùng `subprocess.run` thiếu `-H 192.168.110.119 -P 5037` cho máy Admin (`machine >= 200`), khiến ADB cục bộ báo lỗi không tìm thấy serial và bỏ mặc TikTok mở trên màn hình.
3. **Hiệu ứng hàng trống Excel:** Các ca sau (Row 4, Row 6) không có tài khoản cho Máy 220 nên runner skip trước khi chạm thiết bị, khiến app TikTok bị ngâm từ sáng đến chiều.

**Giải pháp chuẩn (Patch Contract):**
1. Mở rộng `_force_stop_tiktok_and_home` thực thi trọn vẹn 5 lệnh Teardown: `am force-stop`, `input keyevent 3`, `svc power stayon false`, `settings put global stay_on_while_plugged_in 0`, `settings put system screen_off_timeout 600000`.
2. Bổ sung định tuyến Remote ADB (`-H 192.168.110.119 -P 5037`) cho fallback khi `machine >= 200` hoặc có `ADB_SERVER_SOCKET`.
3. Truyền `machine=account.machine` từ call site dòng ~2570 và ~5018.
4. Triển khai watchdog `farm_idle_screen_and_app_healer.py` quét 25 workers song song dọn dẹp các máy rảnh không bị lock.
- Chi tiết xem tại `references/case191-screen-timeout-25d-and-remote-teardown-drift.md`.

## Feed-detected empty slots: Reg-bù hook verification and recovery

When a Feed session reports `skipped-empty`, `account row ... is empty (no username)`, or `does not have valid row`, distinguish two mechanisms before reporting success:

1. **Per-device recovery/reconcile**: `automation_core.tiktok.account_recovery.trigger_account_reconcile(...)` or `_maybe_recover_missing_account_via_login(...)` restores/reconciles an account that should already exist on the device. This is not new TikTok registration.
2. **Reg-bù for empty slots**: the Feed/watchdog result must explicitly launch the existing TikTok registration launcher with only the detected machine STTs (for example through `TIKTOK_REG_TARGET_STTS`). A night-chain Reg phase that runs before Feed is not evidence that Feed-triggered Reg-bù ran.

Required verification before claiming the hook worked:
- Identify the exact watchdog anchor where `empty` is computed and confirm the hook is called after the Feed result is finalized.
- Confirm targeted STTs, launcher path, environment/arguments, and fail-closed preflight inputs from code.
- Require idempotency evidence (session/cluster marker or equivalent) so repeated watchdog ticks cannot register the same slot twice.
- Run a mocked focused verification of both branches: empty list/no-op and non-empty list/launch with exact STTs plus marker creation; never launch live Reg or touch devices for this verification.
- If pytest collection is blocked by unrelated dirty-test syntax, report that blocker separately and use the direct mocked probe; do not edit or revert unrelated workspace changes.
- A `py_compile` pass alone is insufficient for this behavior. Report `PATCHED/UNVERIFIED` until the mocked launch/readback evidence exists.

Pitfall: the Admin cluster can have many empty slots while Kibe has only a few row-specific gaps. Always compare the active session row and cluster workbook before inferring that the hook is broken. Empty-slot classification/reporting is not itself proof that registration ran.

## Feed-detected empty slot → targeted Reg bù hook

When a completed Feed session reports `skipped-empty`, `account row ... empty (no username)`, or `does not have valid row`, treat this as an actionable registration target, not only a reporting category.

1. Extract the exact machine/STT list from the parsed `run_manifest.json` result for the active cluster and row.
2. Invoke the existing registration launcher only with `TIKTOK_REG_TARGET_STTS=<comma-separated STTs>`; never launch a full-fleet Reg batch from a Feed report.
3. Fail closed when the list is empty or launcher, `_detect_clean.py`, account workbook, or other preflight input is unavailable.
4. Write an idempotency marker under `<cluster runtime_root>/cron-state/tiktok-reg-<cluster>-<session_key>.json` before/with launch so watchdog ticks cannot duplicate the same session. Mock `Popen`; never run live Reg or ADB during verification.
5. Verify: `py_compile`, focused mocked test for targeted env + one launch + second-call no-op + empty-list no-op. Preserve unrelated dirty files.

Reference: `references/targeted-reg-bu-hook.md`.

## Follow reconciliation: committed vs attempted actions

When reconciling cross-follow against Web Following, never use an attempted/action ledger count as the script-success count. The authoritative commit evidence is the terminal `follow_result.json`: only `status == "OK"` with `followed_count > 0` / explicit `followed` entries contributes to committed follow delta. `FOLLOW_FAILED`, `follow_failed == true`, a reason containing "bị nhả"/"released", or `followed_count == 0` is audit evidence of a failed or released attempt and MUST contribute zero to the Web discrepancy numerator, report success list, and `daily_account_actions` commit ledger. Report released attempts separately and compare Web only against committed count; if both are zero, report "Khớp 0", not a negative discrepancy. Never reclassify cross-follow discrepancies as natural follows.

Before accepting a watchdog report, inspect the per-machine follow_result.json for every reported follow and reconcile attempted, released/failed, committed, and Web delta. Preserve the raw artifact path in the evidence report. Reference: references/follow-reconciliation-committed-vs-attempted.md.

### Watchdog Reconciliation Masking & Cross-Repo Cooldown Invariants (2026-10-02, Update 2026-10-03)

1. **Reconciliation Masking Defect & False Positive Skew (`m_to_reported`)**:
   - In `feed_session_watchdog.py`, `failed = bool(follow_data.get("follow_failed"))` was historically applied as `m_to_reported[str(m)] = 0 if failed else cnt + natural_cnt`.
   - **Double Pitfall (Case 2026-10-03 - Lệch +22 ảo)**:
     1. Khi follow chéo dính lỗi ở lượt thứ N+1 (`failed = True`), code ép `m_to_reported = 0`, xóa sổ cả `natural_cnt` (follow tự nhiên khi lướt feed đã xong) lẫn `cnt` (các nick follow chéo 1..N đã bấm thành công trước đó).
     2. TikTok Web không hề rollback các lượt đã bấm thành công. Khi Web tăng thật +12 (M52) hay +6 (M70), việc ép `expected = 0` tạo ra con số **Lệch dương ảo khổng lồ (+20 lượt lệch ảo)**, đồng thời in dòng nghịch lý: `script báo 0 (chéo 9, tự nhiên 3) | web tăng +12 (Lệch +12)`.
   - **Quy chuẩn Người Dùng chốt (2026-10-03)**:
     - **Nếu lượt đầu tiên follow chéo = 0 (`cnt == 0`)**: Nick bị nhả/drop ngay từ đầu phiên -> Bỏ hết cả follow tự nhiên (`reported = 0`, và hàm `calculate_session_natural_follows` tự trừ follow tự nhiên của máy này khỏi tổng phiên để tránh lệch âm).
     - **Nếu lượt đầu tiên follow chéo thành công (`cnt > 0`)**: Nick đã ăn follow tự nhiên và ăn các lượt chéo trước khi bị nhả -> Giữ nguyên 100% follow tự nhiên thành công (`natural_cnt`) + các lượt chéo đã gửi lên server (`cnt`), ghi nhận `m_to_reported = cnt + natural_cnt`, tuyệt đối KHÔNG trừ follow tự nhiên của máy này trong `calculate_session_natural_follows`.
   - Chi tiết xem tại `references/watchdog-follow-failed-reconciliation-skew.md`.

2. **Cross-Repo Follow Cooldown Execution Order & Next-Day Automatic Skip**:
   - In any given session, Feed Session (with natural follow) runs FIRST; Follow Hook (follow chéo) runs AFTERWARDS.
   - In the initial failure session, accounts without prior penalties roll natural follow during feed, and only enter cooldown at session end when follow chéo detects server rejection (`set_follow_failed()`).
   - On subsequent sessions and days across the entire Progressive Cooldown window (Streak 1: 3 days, Streak 2: 5 days, Streak >= 3: 7 days):
     - `is_account_in_follow_cooldown(ctx)` in `feed_swipe_smoke.py` reads `follow_state_{machine}_row_{row}.json` (`cooldown_until_at` / `cooldown_until_date`).
     - `_maybe_follow_video` **automatically cancels 100% of natural follow attempts** (`result="skipped", error="account is in follow cooldown (imprisoned)"`).
     - Follow chéo is also cleanly bypassed (`status="skipped", reason="follow-released-daily-cooldown"`). Accounts safely run pure feed nurturing without risking further penalties.

## Triage: Phân biệt Follow nội bộ vs Follow tự nhiên trên Dashboard & Watchdog

Khi Dashboard hiển thị `🔗 Nội bộ: +N` nhưng danh sách Following thực tế trên app không có nick nội bộ:
1. **Kiểm tra `daily_account_actions` vs `session_action_stats`:** Trong `feed_session_watchdog.py`, kiểm tra biến `m_to_reported` xem có bị cộng gộp `cnt (chéo)` + `natural_cnt (tự nhiên)` rồi lưu đè vào cột `internal_follows` hay không.
2. **Đối soát DB Farm:** Quét danh sách following trên TikTok thật so với bảng `farm_account_info` trong `tiktok_tracker.db` để xác thực nick nào là farm, nick nào là kênh ngoài feed.
3. Chi tiết xem tại `references/internal-vs-natural-follow-telemetry-isolation.md`.

## 35. Case 192 (28/09/2026): Khắc Phục Lỗi Watchdog Gộp 2 Phiên Vào 1 Tin Nhắn Telegram (Session-Aware Runner Busy & Single Delivery Gate)

**Hiện tượng & User Feedback:**
- Watchdog gom 2 phiên liên tiếp (Ca 3 - Phiên 1/2 và Ca 3 - Phiên 2/2) vào chung 1 tin nhắn Telegram dài >6.000 ký tự.
- Phiên 1 kết thúc lúc 20:02 nhưng không báo ngay, bị giữ lại suốt 1.5h cho tới khi Phiên 2 xong lúc 21:37 mới xuất cả 2 phiên cùng lúc lúc 21:52.
- Người vận hành phản ánh: *"tao bảo rõ ràng là phiên nào xong gửi cron phiên đó sao lại gộp 2 phiên làm 1 thế này"*.

**Root Cause:**
1. **Runner Busy toàn cục:** `feed_session_watchdog.py` dùng `runner_busy = is_feed_runner_active()` của cả máy chủ. Khi Phiên 1 (18:00 - 20:00) vừa xong lúc 20:02:59 thì Phiên 2 (20:00 - 24:00) đã bắt đầu lúc 20:02:25. Cờ `runner_busy=True` giam giữ Phiên 1 suốt 1.5h.
2. **Nối chuỗi message:** Vòng lặp `main()` gom tất cả các phiên hoàn tất vào `messages = [msg1, msg2]` rồi `print("\n\n".join(messages))`. Cron `no_agent: true` bắt toàn bộ stdout gửi thành 1 tin nhắn Telegram duy nhất.

**Giải pháp chuẩn:**
1. **Session-Aware Runner Busy (`is_cluster_session_busy`):** Khi `now_hm >= win["end"]`, nếu run mới nhất của session đã có `run_manifest.json` đóng `end_time` và thư mục ngày đã xuất hiện run của phiên kế tiếp (`r_hm >= win["end"]`), trả về `runner_busy = False` cho session đó.
2. **Khóa cứng One-Message-Per-Session:** Sau khi format xong 1 phiên và claim atomic state, thực hiện `break` ngay lập tức khỏi cả 2 vòng lặp và in duy nhất `print(messages[0])`. Nếu có nhiều phiên sẵn sàng, mỗi tick 5 phút gửi 1 phiên độc lập.
3. **Đồng bộ 4 vị trí:** `scripts/feed_session_watchdog.py`, `C:/Users/Kibe/AppData/Local/hermes/scripts/`, `Hermes/deploy/hermes-home/scripts/`, `OneDrive Taadaa_Sync_Shared/hermes-cron/scripts/`.
4. Chi tiết xem tại `references/session-aware-runner-busy-and-single-delivery-gate.md`.

## 36. Dual-Cluster Farm Alert Scope & O(1) Upload Failure Triage

**Hiện tượng & Câu hỏi Người Vận Hành:**
- Watchdog phát cảnh báo `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (10 máy lỗi script Upload) - Ca 3 - Phiên 1/2 (Tối) (Row 6)`.
- Người vận hành chất vấn: *"10 máy lỗi trên tổng farm hay sao?"*.

**Root Cause & Triage Scope:**
1. Tiêu đề `[FARM ALERT]` ghi tổng số máy lỗi mà không ghi tên cụm trong header khi chỉ có 1 cụm bị lỗi hoặc tham gia chạy.
2. Khi Cụm Admin (Máy 201–280) chưa chạy Row tương ứng, chỉ có khối `🏢 【FARM KIBE - MÁY 1-80】` xuất hiện trong tin nhắn.
3. 10 máy lỗi chỉ thuộc Cụm Kibe (Máy 1–80), không phải trên tổng 160 máy cả Farm.
4. Mẫu số thực tế: 80 máy Kibe - 21 máy dưỡng sinh = 59 máy cần đăng. Tỷ lệ lỗi là 10/59 (~17%), 47 máy đăng thành công (~80%).

**Quy trình điều tra O(1) & Phân loại 4 nhóm lỗi Upload:**
- Tuyệt đối tuân thủ invariant: CẤM `os.walk`, `find`, `glob(recursive=True)`. Truy vấn trực tiếp file kết quả:
  `D:/Taadaa/runtime/<cluster>/live/<date>/<row_dir>/<run_id>/machines/machine_<M>/<run_id>/upload_result.json`.
- Phân loại rõ ràng cho người vận hành:
  1. `[POST_SUBMISSION_UNKNOWN]` (COMPAT-POST-VERIFY-004): Chốt an toàn fail-closed từ chối ghi nhận thành công khi TikTok không hiện rõ màn hình xác nhận bài đăng, KHÔNG phải lỗi script crash.
  2. `[ACCOUNT_SWITCHER_FAILED]`: Kẹt menu chuyển tài khoản (onboarding, popup, văng phiên).
  3. `[VIDEO_PICK_*]`: Kẹt luồng picker/navigation.
  4. `[PREFLIGHT_VPN_BLOCKED]` / Offline: Rớt phần cứng ADB/USB cáp lỏng.
- Chi tiết xem tại `references/dual-cluster-alert-scope-and-upload-failure-triage.md`.

## 37. Tự Động Khấu Trừ Follow Tự Nhiên Khi Follow Chéo Phát Hiện Nick Bị Nhả/Drop (`calculate_session_natural_follows`)

**Hiện tượng & Vấn đề:**
- Phiên nuôi feed báo có `Follow tự nhiên: N lượt`, nhưng đến pha Follow chéo thì có máy bị TikTok nhả follow sau khi vuốt reload (`FOLLOW_FAILED` / `released`).
- Web đối soát cào sau phiên cho thấy `Following tăng +0`, dẫn đến số liệu follow tự nhiên trong báo cáo feed và database bị vống ảo (Ghost Follows) nếu nick đó bị nhả/drop ngay từ đầu.
- Tuy nhiên, nếu máy đó đã follow chéo thành công $N$ lượt trước khi bị ngắt ở lượt $N+1$ (như M52 chéo 9, M70 chéo 4), TikTok Web thực tế vẫn ghi nhận đầy đủ cả $N$ lượt chéo lẫn các lượt tự nhiên.

**Quy tắc bắt buộc cho Watchdog (Người Dùng chốt 2026-10-03):**
1. **Khấu trừ có điều kiện theo lượt đầu:**
   - BẮT BUỘC gọi `calculate_session_natural_follows(all_machines, all_follows, fl_released)`.
   - **Chỉ trừ** follow tự nhiên của các máy bị nhả/drop mà **lượt đầu follow chéo = 0 (`cnt == 0`)** (nick dính Action Block từ đầu phiên).
   - **Giữ nguyên 100%** follow tự nhiên của các máy mà **lượt đầu follow chéo thành công (`cnt > 0`)** (nick không bị drop, đã ăn cả tự nhiên lẫn các lượt chéo trước lúc bị ngắt).
2. **Minh bạch hóa Telemetry Telegram:**
   - Nếu có máy bị drop (`dropped_tot_nat > 0`):
     `+ Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}] (Đã tự trừ {dropped_tot_nat} lượt do nick bị nhả/drop)`
   - Nếu không có máy bị drop: Giữ nguyên định dạng chuẩn.
3. **Làm sạch Database (`tiktok_tracker.db`):** Chỉ lưu `natural_fl = valid_tot_nat` vào `save_session_action_stats`, tuyệt đối không lưu số thô chưa khấu trừ.
4. **Focused Unit Test Suite:** Bắt buộc có test case `test_calculate_session_natural_follows_deducts_released_machines` trong `python_runner/tests/test_feed_session_watchdog.py`.
- Chi tiết xem tại `references/watchdog-natural-follow-released-deduction.md`.

## 38. Hiệu Chỉnh Ngưỡng Kích Hoạt Farm Alert Watchdog & Chống Báo Động Giả Lỗi Hàng Loạt (2026-10-03)

**Hiện tượng & Vấn đề:**
- Watchdog phát cảnh báo đỏ: `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (3 máy lỗi script Upload) - Ca 1 - Phiên 2/2 (Sáng) (Row 1)`.
- Người vận hành phản ánh bức xúc: *"là sao lỗi có 3 máy báo chi v"*.
- Trên quy mô 80 máy Cụm Kibe (hoặc 160 máy cả Farm), 3 máy lỗi (M19 kẹt ATX-agent, M37 & M42 đen màn hình khi mở TikTok) chỉ chiếm 3.75%. Đây là sự cố ngoại cảnh / lag thiết bị cá biệt, không phải lỗi script sập hàng loạt.

**Root Cause:**
- Trong `feed_session_watchdog.py`, điều kiện đổi tiêu đề header sang `🚨 [FARM ALERT]` trước đây bị hardcode ngưỡng quá nhạy: `if tot_fl_err >= 3:` và `if tot_up_err >= 3:`.

**Quy chuẩn Chuẩn Hóa:**
1. **Nâng ngưỡng kích hoạt `has_script_alert` lên $\ge 8$ máy (tương đương $\ge 10\%$ farm):**
   ```python
   # Bắn Farm Alert khi phát hiện lỗi script hàng loạt (>= 8 máy ~ 10% farm dính lỗi follow hoặc upload)
   if tot_fl_err >= 8:
       has_script_alert = True
       alert_reasons.append(f"{tot_fl_err} máy lỗi script Follow")
   if tot_up_err >= 8:
       has_script_alert = True
       alert_reasons.append(f"{tot_up_err} máy lỗi script Upload")
   ```
2. **Dưới ngưỡng ($< 8$ máy):** Giữ nguyên header êm dịu `📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất (Row {active_row})`. Danh sách máy lỗi cá biệt vẫn được in đầy đủ ở dòng `+ Lỗi script/xác minh (N): ...` bên dưới để theo dõi, triệt tiêu việc giật chuông đỏ báo động giả.
3. Chi tiết xem tại `references/watchdog-farm-alert-threshold-calibration.md`.

## 39. Chống Cộng Dồn Lặp Trong Reconcile Following: Idempotent Two-Tier Ledger & Kỷ Luật Đối Soát Script (2026-10-03)

**Vấn đề & Root Cause:**
- Trong `feed_session_watchdog.py`, hàm `reconcile_cluster_following` từng ghi trực tiếp vào `daily_account_actions` với phép cộng dồn:
  `internal_follows = daily_account_actions.internal_follows + excluded.internal_follows`.
- Khi watchdog chạy quét lại (rescan), retry hoặc đối soát lại nhiều lần cùng một phiên chưa chốt báo cáo, phép tính này khiến số lượng follow bị cộng dồn liên tiếp (nhân đôi, nhân ba lên x2, x3...). Ví dụ: M9 Phiên 1 làm 10 nick bị x3 thành 30 + Phiên 2 làm 19 = 49 (trong khi thực tế script chỉ làm 29).

**Kỷ Luật Đối Soát & Trừ Nhả (Người Dùng Chốt):**
1. **Bộ đếm trừ nhả BẮT BUỘC do chính script tự tính tại hiện trường:**
   - Cơ chế phát hiện nhả follow (`verify_follow`, cờ `follow_failed`, `fl_released`, khấu trừ natural follow) là do script trên thiết bị tự bắt và quản lý.
   - **CẤM TUYỆT ĐỐI lấy delta cào từ TikTok Web/Database để ghi đè hoặc tự trừ vào số nội bộ**: Mục đích đối chiếu 2 con số "Nội bộ" (từ script) vs "Đã follow" (từ TikTok Web) là để kiểm chứng độc lập xem script trên máy bắt nhả có chuẩn hay không. Nếu lấy số DB đè lại thì mất hoàn toàn ý nghĩa đối soát của script.
2. **Quy tắc 1 nick chạy 1 ca (Slot Isolation):**
   - Mỗi nick trên farm chỉ chạy đúng 1 ca trong slot tương ứng của nó trong ngày.
   - Khi thấy "Nội bộ" vọt lên bất thường vượt quá chỉ tiêu ca của nick đó (ví dụ 49 > 32 trong khi max per session là 20), đó là dấu hiệu của bug cộng lặp non-idempotent trong Watchdog. CẤM đoán mò ngụy biện "do nick chạy nhiều ca cộng dồn" hay "TikTok server âm thầm nhả". Bắt buộc đọc trực tiếp artifact `follow_result.json` của thiết bị để thấy số thực tế script đã báo.

**Quy chuẩn Kiến trúc Giải pháp (Two-Tier Idempotent Ledger):**
1. **Bảng trung gian cấp phiên (`session_account_actions`):**
   - Khóa chính tổng hợp: `PRIMARY KEY (session_key, cluster, username)`.
   - Lưu trữ số lượt follow của phiên hiện tại, UPSERT với `SET internal_follows = excluded.internal_follows`.
2. **Tổng hợp cấp ngày (`daily_account_actions`):**
   - Cập nhật số follow trong ngày bằng phép `SUM(internal_follows)` gộp từ `session_account_actions` của đúng `target_date` và `username`.
   - UPSERT với `SET internal_follows = excluded.internal_follows`.
3. **Contract chữ ký hàm:**
   - `reconcile_cluster_following` bổ sung tham số `session_key: Optional[str] = None`.
   - Vòng lặp `SESSION_WINDOWS` bắt buộc truyền `session_key=session_key`.
4. Chi tiết xem tại `references/idempotent-session-account-actions-reconciliation.md`.

## 40. Đồng Bộ Assertion Tỷ Lệ Phân Bổ Tab Feed 50/25/25 Trong Test Suite

**Hiện tượng & Bối cảnh:**
- Cấu hình phân bổ tab mặc định của farm (`DEFAULT_FEED_DISTRIBUTION` trong `feed_swipe_smoke.py`) chuyển sang tỷ lệ **50% For You / 25% Following / 25% Friends** (thay cho tỷ lệ cũ 70/15/15).
- Các unit test cũ trong test suite kiểm tra tỷ lệ phân bổ tab và like rates nếu chưa cập nhật assertion sẽ gây fail khi chạy CI/CD hoặc regression suite.

**Quy chuẩn assertion đồng bộ:**
1. `DEFAULT_FEED_DISTRIBUTION[FEED_TYPE_FOR_YOU] == 0.50`
2. `DEFAULT_FEED_DISTRIBUTION[FEED_TYPE_FOLLOWING] == 0.25`
3. `DEFAULT_FEED_DISTRIBUTION[FEED_TYPE_FRIENDS] == 0.25`
4. Áp dụng đồng bộ trên cả 2 file test:
   - `python_runner/tests/test_feed_like_rates.py` (`test_feed_distribution_complies_with_farm_ratios`)
   - `python_runner/tests/test_feed_swipe_smoke.py` (`test_friends_and_following_feed_distribution_and_like_rates`)
5. Tuyệt đối không can thiệp/sửa đổi file logic `feed_swipe_smoke.py` khi chỉ được yêu cầu cập nhật assertion trong test files.

## 41. Case 193: Loại Trừ Video already_liked Ra Khỏi Mẫu Số Tính Tỷ Lệ Like Tab Bạn Bè / Following Trên Watchdog

**Vấn đề:** Báo cáo Watchdog hiển thị tỉ lệ like tab Bạn bè rất thấp (~20.8%) dù cấu hình rate 85-95%. Nguyên nhân: video cũ lặp lại đã được tim đỏ từ trước (`already_liked` chiếm 19/24 clip) khiến bot không tap lại để tránh unlike, nhưng watchdog chia mù quáng cho tổng 24 swipes.
**Giải pháp:** Mẫu số hợp lệ `valid_*_swipes = max(tot_likes, tot_swipes - tot_already_liked)`. Runner ghi nhận `after_attempt["already_liked"] = True` và telemetry `already_liked_counts` để Watchdog tính đúng 100% trên clip mới. Chi tiết xem tại `references/case193-already-liked-denominator-exclusion.md`.

## 42. Quy Chuẩn Gating Follow Tự Nhiên & Đối Soát Web Post-Session (2026-10-04)

**1. Khóa Cứng Follow Tự Nhiên Ngày Dưỡng Sinh:**
- Trong `multi_machine_feed_session.py` (dòng 4871–4873): khi `is_organic == True`, `child_config["_follow_rate"]` bắt buộc gán `{"for_you": 0, "following": 0, "friends": 0}`.
- Máy dưỡng sinh chỉ lướt xem video thuần (Pure Feed), tuyệt đối không bấm nút Follow tự nhiên. 100% follow tự nhiên trên báo cáo chỉ đến từ các máy cày (`is_organic == False`, `age >= 21`, `video >= 6`).

**2. Gom Cào Web Đối Soát Follow Tự Nhiên:**
- Trong `feed_session_watchdog.py`: `target_machines` cào Web sau phiên luôn bao gồm `set(natural_targets)`. Bất kỳ máy nào có `natural_cnt > 0` đều được tự động gom vào danh sách cào Web TikTok đối soát sau phiên, đảm bảo kiểm chứng thực tế 100% thay vì bỏ sót.

**3. Hiện Tượng Co Cụm Mẫu Số (Denominator Shrinkage):**
- Tỷ lệ thiết kế $\frac{\text{Natural Follow}}{\text{Cross Follow}} \approx 3\% - 5\%$.
- Khi TikTok siết nhả follow chéo làm hàng chục máy ngắt phiên sớm về 0 lượt, sản lượng follow chéo bị co cụm (ví dụ chỉ còn 7 máy hoàn tất ăn 76 lượt), trong khi follow tự nhiên đã hoàn tất ở bước lướt feed trước đó trên 35 máy cày (27 lượt).
- Tỷ lệ hiển thị trên báo cáo tạm thời bị đẩy lên ~35%. CẤM ngộ nhận script tăng tỷ lệ follow tự nhiên; đây là hệ quả toán học do mẫu số chéo bị co lại.

**4. Kỷ Luật Số Liệu Lịch Sử:**
- CẤM lấy số Following lũy kế toàn đời (250–380) gán nhãn "tăng trong 1 tháng qua". Trước ngày 02/10/2026, log script cũ có dương tính giả do Optimistic UI và nhãn `id/t_q`. Đánh giá hiệu suất và tỷ lệ nhả follow chỉ dùng dữ liệu đối soát 2 pha từ 2026-10-02 trở đi.
- Chi tiết xem tại `references/natural-follow-gating-reconciliation-and-ratio-analysis.md`.













