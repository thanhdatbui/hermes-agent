# Hermes cron orchestration cho farm (migration từ Windows Task Scheduler)

Quyết định kiến trúc 2026-08-09/10 (user chốt): đẩy lớp QUYẾT ĐỊNH lên Hermes cron, giữ lớp THỰC THI là consumer scripts hiện có. Không thay consumer scripts / automation-core shared code.

## Vì sao KHÔNG đẩy 100% lên Hermes cron
- Hermes cron KHÔNG wake được máy đang sleep → wake timers (TikTokSchedulerWake 6:00, GmailSchedulerWake 8:00, TikTokAllSchedulerWake 9:30) là Windows-only. User xác nhận máy chạy 24/7 nên không lo wake nữa.
- Hermes chết = cron chết = lịch chết. Hermes KHÔNG tự báo được → bắt buộc watchdog NGOÀI Hermes: heartbeat file (cron job mỗi ~10' ghi timestamp) + tray mở rộng check heartbeat quá hạn (>~25') → Telegram bot API (curl thẳng, không cần Hermes) + restart gateway.
- Tray apps là daemon (proxy watcher respawn 15s) — cron theo tick không thay được daemon.

## Split: decision layer vs execution layer
| Lớp | Nơi chạy | Token |
|---|---|---|
| Picker (sinh lịch ngẫu nhiên per-account) | Hermes cron script thuần 00:30 | 0 |
| Runner (entry tới giờ → gọi launcher cũ) | Hermes cron script thuần mỗi 15' | 0 |
| Watcher (đọc reports → recovery → Telegram) | Hermes cron hybrid | LLM optional |
| Wake + daemon + watchdog | Windows Task Scheduler (GIỮ 1 task logon tray) | 0 |

## Constraint lịch user chốt (per-account random + constraint cụm)
- 6 acc/máy (farm 60-74 máy SM-G930F), mỗi acc **2 ngày lướt 1 lần**; jitter CHỈ TRỄ không sớm (≥3 ngày = hard overdue, ưu tiên cao nhất)
- Max **3 acc/máy/ngày**, 2 acc cùng máy start cách nhau **≥2h** (start-to-start)
- Khung 08:00-22:00, CẤM 12:00-14:00 & 17:00-19:00 (RESERVED_BLOCKS từ `automation_core.scheduler.time_windows`)
- **LƯỚT XONG ĐĂNG LUÔN** trong cùng entry (`feed_then_post`) nếu acc đến hạn đăng — KHÔNG tách lịch post riêng (user: "chia ra sợ hơi phức tạp")
- Slot granularity 15', session_duration ~60' (cần user xác nhận), grace 90' sau slot → quá hạn = missed + watcher review
- Timezone **Asia/Ho_Chi_Minh** (UTC+7) — user luôn dùng giờ VN
- Manifest JSON (không JSONL): schema `tiktok-farm-assignment-v1`, mỗi entry có `entry_id` + `idempotency_key`, seed deterministic (KHÔNG `random.random()` global; cùng seed = cùng output), atomic write `os.replace`, process lock `picker.lock`/`runner.lock`/`watcher.lock` (KHÔNG dùng làm device lock), idempotent reuse manifest cùng ngày, `--force-regenerate` chặn khi đã có entry running/success
- `action_type` enum: `feed_only | feed_then_post | recovery_replay | blocked` — `post_only` CẤM trong picker; `blocked` chỉ audit, runner không chạy

## Workbook source of truth (mâu thuẫn đã xác nhận — đừng đoán)
- Feed: `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` (sync từ tracking workbook qua `sync-safe-workbook.py`)
- Upload: `Tik1.xlsx`/`Tik2.xlsx` (workflow riêng: Folder Video, Video Đã Đăng = monotonic cursor không regression, Hashtag Pool) — KHÔNG đọc taikhoan_run_safe
- `Taikhoan_dat_v2` = account/credential — không dùng làm lịch
- Alias: `ID` ≈ `ID TikTok`; account row hợp lệ cần: device ID + ID TikTok + Folder Video + Hashtag Pool
- P1 dùng `source-config.json` khai báo source, không hard-code 1 workbook

## Mapping acc → máy/serial (thứ tự ưu tiên)
1. `D:\CodexRuntime\tiktok-video\config-machine-<N>.yaml` (CHỈ field định danh machine/serial, không đọc secret)
2. DeviceMapWorkbook (`list_feed_session_machines`)
3. Resolver của launcher hiện tại
Conflict config vs workbook → `MAPPING_CONFLICT` (block, không tự chọn 1 bên). Serial trống → `MISSING_SERIAL`. ID TikTok trống → `MISSING_TIKTOK_ID` (máy 73/75/77-80). 1 acc map nhiều máy → `AMBIGUOUS_ACCOUNT_MAPPING`.

## Device lock (P1 an toàn: consumer-owned)
- Runner CHỈ preflight lock; bận → `SKIPPED_DEVICE_LOCKED` (typed result, KHÔNG tính là success/fail mù)
- KHÔNG claim outer lock riêng (tránh deadlock machine/serial alias)
- KHÔNG takeover tự động, KHÔNG xóa stale lock bằng heuristic cleanup
- lock state: queued/running/recovery/handoff/blocked/temporarily_skipped; exception/timeout → handoff

## Gotchas verified (đọc code 2026-08-10)
- `run_tiktok_upload_batch.ps1` default `config-machine-62.yaml` → KHÔNG coi là sẵn sàng mọi máy chỉ vì nhận `-MachineId`; adapter phải truyền đúng config/runtime per máy
- `run_tik1_random_render.ps1` CHỈ render local, KHÔNG upload
- Feed launcher: `-Row` 1..6 (workbook row) hoặc `-Machines`; `-Preset full` bắt buộc cho discovery từ workbook; cần `-Run` để live; hỗ trợ `-RandomizeMachineOrder`, `-MachineStartStaggerMs`
- Upload wrapper có thể prompt `RUN` nếu thiếu `-Confirmation` → runner phải truyền flag non-interactive
- **CHƯA có launcher per-account "feed xong post"** → P1 chỉ làm adapter CONTRACT, adapter thật ở P4
- `scheduler.jsonl` event: completed/failed/skipped-missed-window/multi-machine-feed-session...; **exit code 0 KHÔNG đủ proof** (cần report/verifier; đã gặp exit=1 không report, exit=0 thiếu verifier)

## Recovery attempts (dùng runtime đang có, user: "cứ dùng y r fix sau")
- attempt 1: gọi recovery runtime, KHÔNG Telegram
- attempt 2 fail: Telegram + blocker
- blocker thật: Telegram ngay
- Recovery runtime: `run-schedule-recovery-watch.ps1` (`-Dispatch` + `-EnableLiveRecovery`), `recovery-health-watch.ps1` (checkpoint ~300s, guarded takeover ~600s)
- Telegram: gửi về chat Home; payload KHÔNG chứa credential; grouping theo entry

## Phases migration (P1-P6)
- **P1** Core harness: picker/runner/watcher + manifest schema, KHÔNG sửa consumer hay automation-core
- **P2** Chuẩn hóa account/workbook/ledger source + mapping đầy đủ
- **P3** Chốt cadence, video quota, chọn video, post receipt
- **P4** Adapter/launcher integration: feed, upload, 5 consumer scheduler (Tiktok_Reg, tiktok-log-in, tiktok-add-bao-mat-f2a, add mail khoi phuc, register gmail)
- **P5** Watchdog ngoài Hermes: heartbeat + tray + Telegram production
- **P6** Rollout farm-wide, canary/dual-run, tắt Windows Task Scheduler (chỉ giữ 1 task logon tray)

## Quy trình thực thi (AGENTS.md)
Task này = COMPLEX (đụng scheduler policy, multi-repo) → plan trước (subagent read-only, nó trả verdict `PLAN_READY`/`PLAN_NEEDS_MORE_INFO`), audit plan, rồi worker build từng phase. User chốt hướng mới dispatch worker — không tự build.