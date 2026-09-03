---
name: tiktok-farm-hermes-cron-migration
description: Migrate TikTok farm scheduling từ Windows Task Scheduler sang Hermes cron orchestration — picker/runner/watcher, manifest schema v1, user-chốt constraints, audit findings, phases P1-P6.
---

# TikTok Farm → Hermes Cron Migration

## Mục tiêu
Bỏ Windows Task Scheduler (TikTokScheduler/TikTokAllSchedulerTray/wake tasks), chuyển sang Hermes cron: mỗi account lướt feed (nuôi acc) ngẫu nhiên giờ riêng, lướt xong đăng luôn nếu đến hạn — hết đồng loạt. Picker/runner = script thuần no_agent (0 token LLM); watcher hybrid; chỉ Telegram khi fail hết 2 attempts / blocker thật.

## User chốt (2026-08-10 — cao hơn mọi đề xuất cũ trong plan)
- Mỗi consumer giữ workbook RIÊNG, không hợp nhất: feed/lướt = `taikhoan_run_safe.xlsx` (D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\), upload = `Tik1.xlsx` (có Folder Video/Video Đã Đăng). Picker đọc 2 nguồn qua source-config.json + account_id mapping ổn định.
- Farm 60-74 máy SM-G930F; mỗi máy tối đa 6 acc (target đủ 6).
- Mỗi acc: 2 ngày lướt 1 lần; jitter chỉ TRỄ không sớm (≥3 ngày = hard overdue, ưu tiên cao).
- Mỗi máy/ngày: max 3 acc; 2 acc cùng máy cách ≥ 180 phút.
- Window: 06:00 → 01:00 đêm hôm sau; reserved blocks 12-14 & 17-19 GIỮ NGUYÊN.
- Slot 15 phút; phiên (session_duration) 60 phút.
- Lướt xong đăng luôn trong 1 phiên: action `feed_then_post` (không tách lịch; `post_only` cấm trong picker).
- Lock: consumer là owner duy nhất; runner chỉ preflight → `SKIPPED_DEVICE_LOCKED`, không claim outer lock.
- Recovery: giữ runtime hiện có (chưa từng tự recovery thành công — user cứu tay; fix sau). Attempt 1 → recovery không Telegram; attempt 2 fail → Telegram; blocker thật → Telegram ngay.
- Telegram về Home channel; timezone Asia/Ho_Chi_Minh; runner 15', grace 90' sau slot_time, quá hạn → missed + watcher review.
- Máy chạy 24/7 (không lo wake).

## Account-block model (chốt 2026-08-10 — ⚠️ ĐÃ BỊ THAY THẾ 17/08 bởi ROW-SLOT picker; xem mục `## ⚠️ ROW-SLOT picker (user chốt 17/08...)` phía dưới — KHÔNG implement lại block/lane/bắt-buộc-3-acc)

Plan triển khai `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md` (đã reconcile 6 findings từ audit
độc lập: 3 MAJOR + 3 MINOR) thay mô hình "3 entry độc lập/máy/ngày" bằng **account-block**. Các con số dưới
đây là NGUỒN DUY NHẤT khi implement Phase 1–7 — mọi nơi khác ghi window cũ 06:00→01:00 / reserved 12–14,17–19
GIỮ NGUYÊN / "117 passed 3 failed" là HẾT HIỆU LỰC:

- **Logical window 06:00 → 02:00 (+1)** (20h); offline 02:00–06:00. Mốc ngoài-window duy nhất cho test = **02:30**
  (02:00 là ranh giới exclusive — dùng trong `is_in_logical_window`/`grid_slots`; KHÔNG dùng 01:00/01:30 làm mốc).
- Mỗi máy/ngày: **3 account-block** (anchor 07:00 / 14:00 / 21:00). Mỗi block = 1 account = 2 phiên feed 60 phút
  + **pair gap 60–90 phút (grid 15 → {60,75,90})**. Công thức chốt: pair gap là khoảng GIỮA S1_end và S2_start
  → `S2_start = S1_end + pair_gap`, `S2_end = S2_start + 60`. End max: B1 ≤ 10:30, B2 ≤ 17:30, B3 ≤ 00:30(+1) < 02:00.
- Inter-block gap 210–240 phút ∈ [180,300]; duration cụm = 60+60+pair_gap (180' gap 60 / 210' gap 90).
- **2 lane cố định (Cập nhật 01/09: Chuyển Ca 3 tối sang nuôi Row 5 & 6, Row 1 & 2 chỉ nuôi sáng)**:
  - **Ngày Lẻ (Lane B)**: Ca 1 (06:00) = **Row 1** + Ca 2 (12:30) = **Row 3** + Ca 3 (19:00) = **Row 5** `(1, 3, 5)`.
  - **Ngày Chẵn (Lane A)**: Ca 1 (06:00) = **Row 2** + Ca 2 (12:30) = **Row 4** + Ca 3 (19:00) = **Row 6** `(2, 4, 6)`.
  - Thứ tự 3 acc trong lane random theo **seed per-machine-per-day = `int(sha256(f"{day}|{machine}|{assignment_seed}")[:8], 16)`**;
  - **Chiến lược Warmup Row 5 & Row 6**: 10 ngày đầu **CHỈ LƯỚT FEED THUẦN**, không đăng video, không follow chéo (Gate < 5 video tự động khóa follow chống action block).
  - 2 phiên cùng acc PHẢI liền nhau trong block (session_index 1/2, chung block_id) — không tách phiên, không reshuffle.
- `reserved_blocks` ĐÃ BỎ (12–14, 17–19 không còn bị chặn); `reserved_intervals()` giữ trả `[]` vĩnh viễn (tương thích).
- Clear-tiktok-cache cuối block 3, 1 lần/máy/ngày (offline harness: journal + in lệnh, KHÔNG spawn subprocess).
- Baseline P1 thực tế: **121 passed, 0 failed (GREEN)** — KHÔNG còn "3 test đỏ"; Phase 0 verification-only,
  không sửa code để "xanh". Golden vector (`test_hermes_cron_contract.py`) cập nhật ĐÚNG 1 LẦN ở Phase 3.
- Chi tiết từng finding + locator đã sửa: `references/2026-08-10-fleet-plan-audit-reconciliation.md`.
- Quy trình đồng bộ trực tiếp taikhoan_run_safe, xử lý MAPPING_CONFLICT và tự động tái tạo manifest/cohort: `references/2026-09-01-taikhoan-safe-direct-cron-sync-and-manifest-regeneration.md`.

## ⚠️ INVARIANT: jitter/anchor PHẢI nằm trên grid 5 phút (RESERVED_BLOCK_CONFLICT 20/08)

Cron sáng 20/08: `phase9-staging-picker` 06:00 fail `ValueError: RESERVED_BLOCK_CONFLICT` → manifest ngày không tạo được → toàn bộ lịch nuôi acc hôm đó không chạy (watcher 06:07 fail cùng thời điểm — verify traceback child riêng nếu nghi ngờ).

- **Root cause**: commit `7053491` (19/08 23:09, "jitter continuous -25..+25") đổi `JITTER_MINUTES` từ discrete `(-20, -15, 15, 20)` → `tuple(range(-25, 26))`. Nhưng `is_schedulable_interval` (models.py:255) bắt buộc `minute % SLOT_GRID_MINUTES == 0` (grid 5'), duration đúng 60', window 06:00→02:00(+1), đúng logical day. Jitter liên tục → session 1 lệch grid (06:07, 06:08, 06:12...) → 312/534 entries invalid → `RESERVED_BLOCK_CONFLICT`.
- **Fix đã áp dụng**: `JITTER_MINUTES = tuple(range(-25, 26, 5))` — 11 mốc bội số 5 (từ -25 đến +25 bước nhảy 5 phút: -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25).
- **Random 2 lớp (Lịch trình Macro + Thực thi Micro Stagger)**:
  1. *Macro Jitter (Cấp lịch trình)*: Mỗi ca có anchor + jitter riêng (Ca 1: 06:00 clamp 0..25p; Ca 2: 12:30 ±25p; Ca 3: 19:00 ±25p) + Pair-gap random độc lập 35..60p (bước 5p). Tạo ra các mốc giờ chạy rải rác từng đợt 5 phút.
  2. *Micro Stagger (Cấp thực thi)*: Trong cùng một mốc 5 phút khi có nhiều máy cùng chạy, `multi_machine_feed_session` dùng `build_machine_launch_plan` delay ngẫu nhiên 2000ms - 8000ms (2 - 8 giây) giữa từng máy để không bắn lệnh ADB và kết nối proxy cùng 1 giây.
- **Tạm tắt Follow rửa IP**: Trong `multi_machine_feed_session.py`, `_run_follow_hook` mặc định `ALLOW_CROSS_REPO_FOLLOW = False` (chỉ bật khi có env `ALLOW_FARM_FOLLOW=1` hoặc config `safety.allow_farm_follow=True`) để nuôi lướt feed mà không đi follow khi đang đổi dàn proxy.
- **Invariant chung**: MỌI đổi `JITTER_MINUTES`/`BLOCK_ANCHORS`/pair-gap trong `blocks.py` phải chạy lại probe grid trước khi live: `scripts/check_jitter_grid.py <source-config> <feed_state.json> <post_state.json> <day> <seed>` (gọi `Picker._entries` + check `is_schedulable_interval` + minute%5 từng entry). Kiểm luôn window: s3 ca 19:00 + jitter +25' + gap 60' kết thúc 00:25(+1) < 02:00 (hiện OK — nếu jitter/gap tăng nữa sẽ vượt).
- **Triệu chứng publication dở dang**: `manifests/<day>/ACTIVE.lock` (3 bytes "000") + `snapshot_bundles/<day>/gen_*` = picker fail giữa chừng. Re-pick sau khi sửa: xóa CẢ `manifests/<day>/` LẪN `snapshot_bundles/<day>/` bằng path đầy đủ `D:/Taadaa/runtime/kibe/cron-state/...` (relative path sai chỗ — đã dính trước đây).
- **Chuỗi chẩn đoán cron fail**: `cronjob list` tìm job `last_status: error` → đọc `~/AppData/Local/hermes/cron/output/<job_id>/<ts>.md` (traceback đầy đủ + argv child) → chạy lại lệnh child bằng tay với `PYTHONPATH=<repo>` (không có PYTHONPATH → `ModuleNotFoundError: python_runner` đánh lạc hướng) → grep ReasonCode → đối chiếu invariant.
- **Triệu chứng cron im lặng hoàn toàn / không alert (Job Hang & `already running — skipping`)**: Nếu runner/watcher bị timeout (3600s) hoặc kẹt process ngầm (`hermes_cron_watcher.py`), scheduler của Hermes sẽ thấy job cũ chưa thoát và liên tục bỏ qua các tick tiếp theo (`already running — skipping`), dẫn đến picker 6h sáng không chạy, không có manifest ngày mới, không kích hoạt máy -> farm im lặng 100% không sinh alert. Cách chẩn đoán & xử lý chi tiết: xem `references/2026-08-22-cron-hang-silent-skipping-diagnosis.md`.
- **`last_status: error` trong cron list ≠ lỗi ĐANG diễn ra** (hit 20/08 sau khi fix): picker/watcher hiển thị error là lần chạy TRƯỚC khi sửa (06:00/07:07), cron chỉ lưu trạng thái lần chạy gần nhất — fix xong nhưng job chưa tick lại nên status vẫn error. Verify sức khỏe THẬT bằng (a) chạy tay child script với PYTHONPATH → exit 0 + artifact tạo ra; (b) runner live lease `state_root/runner-live-lease/<day>.json` có pid + expires tương lai = feed đang chạy thật (cron tick tiếp sẽ silent-skip khi lease active — KHÔNG phải job hỏng); (c) watcher im lặng (không output file mới) = watchdog pattern đúng thiết kế khi không có sự kiện, KHÔNG phải scheduler treo — phân biệt với "treo" bằng việc chạy tay watcher trả output + process scheduler còn sống (`tasklist` thấy gateway pythonw + runner powershell). Cron chạy tay 07:12 tạo manifest → lần tick kế (08:07) sẽ tự sạch.

## Phase 4 hardening — schema-remediation audit lesson (2026-08-11)

Commit `fc61be9` đã sửa phần lớn lỗi block validation (metadata splice với
`SourceConfig`/entries và thứ tự `entry_ids` canonical), nhưng **không được coi là
APPROVED chỉ vì suite 137 passed**. Audit độc lập còn bắt được hai lớp closure bắt buộc:

- **Source-less canonical integrity:** kiểm tra derived identity như `seed` phải chạy
  unconditional trong `validate_manifest(payload, source=None)`. Source-less mode không thể
  xác thực quyền sở hữu mapping với `SourceConfig`, nhưng vẫn phải bác payload tự-consistent
  bị tamper ở các giá trị canonical nội bộ. Không dùng `if source is not None` để bỏ qua kiểm
  tra derived value.
- **Chống gate-masking trong adversarial tests:** không mutate đồng thời `day`, machine,
  serial, account, lane, seed rồi chỉ assert `pytest.raises(ValueError)`. Mutation phải độc
  lập, giữ topology/slot/ID hợp lệ để đi tới đúng gate đang audit, và assert exact
  `ReasonCode`. Với ordered fields, canonical `[session 1, session 2]` phải pass còn list đảo
  phải reject.

Reference tái sử dụng: `references/2026-08-11-schema-remediation-reaudit.md`.
Các chi tiết cũ về `fc61be9`/Phase 4 residual được giữ trong
`references/2026-08-11-phase4-block-validation-hardening.md` và
`references/2026-08-11-fleet-plan-audit-v2-residuals.md`; không dùng chúng để suy ra
approval nếu audit mới còn finding.

⚠️ **CÒN LẠI TỪ plan v2** (đã ghi trong reference):
1. ✅ `expected_ids` trong `_validate_block_structure` dùng `payload["seed"]`
   (entry KHÔNG có key seed) — không áp lại bản vá cũ.
2. ✅ `test_journal_clear_cache_event_canonical` assert `"timestamp" in req` — GIẢI QUYẾT Ở PHASE 6 (commit 33f6c4d):
   `_append_unlocked` tự `setdefault("timestamp", as_of or now(TZ))` cho CLEAR_CACHE_* events, `common` allowlist
   nhận `timestamp` + `parse_hcm_timestamp` — assert GIỮ NGUYÊN, KHÔNG bỏ (chi tiết:
   `references/2026-08-11-phase6-clear-cache-maintenance.md`).


## Phase 3 ĐÃ IMPLEMENT (2026-08-11) — block planner live, đừng lạc vào code cũ

Picker giờ sinh 3 block/máy/ngày; manifest có top-level `blocks` + entry `block_id`/`session_index`;
golden vector đã cập nhật ĐÚNG 1 LẦN. Sự thật kiến trúc sau implement (chi tiết + recipe đầy đủ:
`references/2026-08-11-phase3-block-planner-implementation.md`):

- **entry_id hash cả `block_id` + `session_index`**; `block_id_for` là công thức DUY NHẤT ở `blocks.py`
  (manifest import alias `blocks_block_id_for`).
- **BẪY `entry_ids` của block**: `_entries` tính entry_id với manifest_id TẠM (thiếu `resource_mapping`) →
  assignment_id khác payload thật → `blocks[*]["entry_ids"]` stale. `build_manifest_payload` PHẢI rebuild
  `entry_ids` từng block từ entries (theo session_index) sau khi recompute entry ids — đã fix, đừng xóa.
- **validate_manifest mode-aware**: `blocks` non-empty = block-mode (entry bắt buộc block_id/session_index,
  account lặp chỉ trong CÙNG block; BỎ heuristic cũ "≤3 start/máy + gap ≥180" vì block-mode có 6 session/máy);
  `blocks == []` = legacy (schema entry cũ + heuristic giữ) — legacy mode CẦN THIẾT cho payload thủ công của
  test cũ (vd `test_prior_day_*`).
- **Picker lập lịch 100% FEED_ONLY** (post DUE bị bỏ qua, không còn feed_then_post từ picker); lane không đủ
  3 due → skip CẢ lane `UNSCHEDULABLE_CAPACITY` (không lập lịch một phần); ngoài lane → `CAPACITY_EXCEEDED`.
- **Fixtures 1-account CHẾT dưới block planner** (cần đúng 3 due/lane) → `entries[0]` IndexError hàng loạt.
  Recipe migrate: 3 acc acct-a/b/c rows 1-3, GIỮ seed=7 (re-pick khớp), nhưng permutation
  `rng.sample` của `machine_day_seed(2026-08-10,1,7)` = [b,a,c] → entries[0] = acct-b (row 2) → `TARGET` row 2;
  custom state dicts phải đủ 3 acc; `run_entry(execute=True)` với as_of trước 07:00 → `FUTURE_NOOP` (dời 07:30).
  Luôn verify permutation bằng script nháp, đừng đoán.
- **Golden vector = formula pin**: reference_assignment/entry dùng input config-mẫu (KHÔNG resource_mapping/
  digest) và KHÔNG BAO GIỜ bằng hash của snapshot thật — test có 2 lớp độc lập (reference stdlib vs pipeline).
  Cập nhật = tính hash mới bằng script stdlib trước khi sửa assert.
- **Tình trạng Phase 3 tại cutoff** (CHƯA commit): fleet 5/5 + contract 27/27 xanh; p1_r2 68/80 (5 patch cuối
  chưa re-run); watcher/regressions CHƯA migrate fixture; còn ~7 test + full suite + commit theo message plan.

## Phase 6 ĐÃ IMPLEMENT (2026-08-11) — maintenance clear-cache offline, commit 33f6c4d

- Top-level `maintenance` bắt buộc trong manifest (strict `set(payload) == required` cập nhật cùng phase);
  `maintenance_for_source(source)` (máy 1 + serial) tự sinh qua DEFAULT param của `build_manifest_payload` →
  mọi legacy caller (p1_r2, regressions) xanh không phải sửa.
- Journal: 2 event `CLEAR_CACHE_REQUESTED` (non-terminal) / `CLEAR_CACHE_DONE` (terminal); auto `timestamp`.
- `Runner.clear_cache_due(as_of)` = trong window & ≥ max slot_end block 3 & chưa có DONE; mốc 00:00 False / 01:00 True / 03:00 False.
- CLI `--clear-cache`: offline-only KHÔNG spawn subprocess; idempotent (check REQUESTED/DONE rồi mới append);
  stdout = MỘT JSON object `{action: clear_tiktok_cache, command, offline: true}` (KHÔNG list entry).
- Cả 4 test plan dòng 829-927 implement nguyên văn; full 6 suite 166 passed; `git diff --check` clean.
- **Checklist 8 chỗ khi thêm 1 journal event mới** (models enum → TRANSITION_MATRIX → allowlist → exact_fields →
  value-semantic → required_by → terminal_by_event → auto-populate trong `_append_unlocked`) + locator chi tiết:
  `references/2026-08-11-phase6-clear-cache-maintenance.md`.

## Kiến trúc (3 script mới chạy dưới Hermes cron)
1. **PICKER** (00:30, script thuần): đọc workbook read-only → filter account hợp lệ → sinh slot random per-acc thỏa constraint cụm → manifest JSON atomic (tmp + os.replace). Idempotent: manifest hợp lệ tồn tại → reuse, không reroll; `--force-regenerate` chỉ khi chưa có entry running/success.
2. **RUNNER** (15'): đọc manifest → entry tới giờ → gọi launcher EXISTING (KHÔNG sửa consumer scripts) đúng 1 lần; idempotent trong cửa sổ; lock bận → SKIPPED_DEVICE_LOCKED; feed fail → không gọi post; feed_then_post → gọi upload contract sau feed success.
3. **WATCHER** (15'): parse JSONL ledger/reports (scheduler.jsonl, handoff-ledger.jsonl); stale running → phân loại; gọi recovery runtime hiện có; Telegram theo rule trên.

Manifest: `assignments/tiktok-farm-YYYY-MM-DD.json` (+ `.active.json`), entry_id + idempotency_key unique, seed ghi trong manifest, deterministic (cùng seed → cùng output), bounded backtracking N=100, không phá hard constraint, skipped[] có reason_code riêng (MISSING_TIKTOK_ID, ACCOUNT_LOGGED_OUT, NO_VIDEO_AVAILABLE, MAPPING_CONFLICT, CAPACITY_EXCEEDED...).

## Audit findings (Sol 08-10 — BẮT BUỘC áp khi build P1)
1. **Manifest phải khớp loader thật** `automation_core.assignments.AssignmentManifest.load()`: yêu cầu `schema_version`, `assignment_id`, `owner_id`, `reviewed_at` — KHÔNG dùng `schema`/`manifest_id`/`owner` object như plan cũ (RED repro: ASSIGNMENT_MANIFEST_INVALID).
2. **KHÔNG import nguyên `time_windows.is_available()`** (core cứng 08:00-22:00): P1 cần operating-window riêng 06:00→01:00 nhưng TÁI SỬ DỤNG `RESERVED_BLOCKS` (12-14, 17-19).
3. `run_tiktok_upload_batch.ps1` default `config-machine-62.yaml` — không coi là ready mọi máy; adapter P4 phải truyền config/runtime đúng.

## Audit R6 (2026-08-10) — REJECT, 3 P1 code + reconciliation

Worker R6 fix xong 7 finding R5 (70 tests pass) nhưng audit độc lập (gpt-5.6-sol, read-only) vẫn REJECT:

1. **watcher.py:132-140,257 — VERIFIED_SUCCESS với proof giả**: chỉ hash `recapture`; retry/proof chỉ check
   path tồn tại (AGENTS.md/CLAUDE.md/PROJECT_RULES.md được chấp nhận làm artifact); `invocation_id` không
   đối chiếu (bị thay bằng reservation_id). Invariant: mỗi recapture/retry/proof phải hash/identity-bound vào
   manifest hash/id, entry, target, signature, attempt, invocation, reference time.
2. **journal.py:151,204-211,264 — closed schema chỉ đóng key set, chưa đóng value**:
   `CLASSIFIED(outcome="BOGUS", lock_safe="not-a-bool")` và `FAILED(retryable="yes", next_attempt=99)` vẫn qua.
   Invariant: enum/bool value validation, attempt continuity, `next_attempt == attempt+1`, identity/ID check
   tại append lẫn replay.
3. **watcher.py:183 — thiếu gate "registered handler"**: bridge có callable recover + handler_id không rỗng
   được coi là hợp lệ; `handler_id="totally-unregistered-handler"` → AUTO_RECOVERY_PENDING. Invariant: registry
   phải chứng minh handler đăng ký + khớp bridge trước RECOVERY_RESERVED; thiếu → NO_HANDLER_IMPLEMENTED.

Reconciliation (KHÔNG phải scope escape của P1 worker): worktree nhiễm file ngoài allowlist —
`benign_popup.py`/`feed_swipe_smoke.py` thuộc task add-phone của worker khác (đang sửa live), còn
`runtime/taikhoan-sync-state.json` + HANDOFF section thuộc task auto-sync `taikhoan_run_safe` — cần baseline
chứng minh nguồn gốc, không coi là lỗi.

## Audit R7 → R8 (2026-08-10) — REJECT liên tiếp trên CÙNG invariant; bài học root-cause

- **R7 REJECT, 4 P1**: (1) journal nhận `entry_id` không thuộc manifest; (2) state machine chưa đóng —
  `FAILED(terminal=true)` trong recovery chain, `RECOVERY_REQUESTED` ngay sau DETECTED (chưa qua
  CLASSIFIED/RESERVED/RECOVERING); (3) artifact binding không buộc `invocation_id`/`reference_time` vào
  chain thật; (4) handler chưa đăng ký vẫn ghi `CLASSIFIED` trước khi chứng minh registry.
- **R8 REJECT, 6 P1 — cùng một root cause**: journal "closed schema" chỉ đóng TÊN event, chưa đóng VALUE:
  (1) unregistered handler vẫn CLASSIFIED ở path sensitive/locked; (2) recovery matrix cho phép reserve sau
  `MANUAL_REQUIRED` và `FAILED(attempt=8) → RECOVERY_REQUESTED(9)`; (3) execution journal nhận
  `LAUNCH_RESERVED(idempotency_key="forged-key", artifact_root="../../outside")` và `LAUNCH_STARTED(inv-B)`
  sau reservation inv-A; (4) notification replay cho phép payload chứa secret +
  `ALERT_SENT(delivery_result=False)`; (5) artifact `reference_time` không so với `reserved_at` đúng
  stream/attempt; (6) `finalize_handoff` check evidence NGOÀI journal lock (TOCTOU), không verify đủ từng
  chuỗi RECOVERING→RECAPTURED→RETRYING→FAILED.
- **BÀI HỌC (4 vòng REJECT liên tiếp cùng invariant)**: khi audit lặp lại journal/recovery closure, đừng vá
  từng probe — yêu cầu worker redesign theo ROOT CAUSE: tách validation 2 lớp — (a) topology theo tên
  predecessor, (b) value-semantic theo event type (enum/bool/identity/polarity/binding) — áp dụng CHUNG cho
  append VÀ replay; test phải phủ mọi event × predecessor × value-constraint, không chỉ "event có trong
  matrix" (audit R8: test chỉ check "represented" → vẫn REJECT vì thiếu chiều value).
- **Test pass ≠ closure proof**: suite 80/109 passed vẫn bị REJECT — auditor chạy probe adversarial độc lập
  (in-memory, không cần pytest) tìm lỗi mà test không phủ. Audit sandbox read-only cũng KHÔNG chạy được
  pytest (`No usable temporary directory`) → claim "N passed" luôn là NEEDS_PROOF trong audit, không phải
  test failure; verdict dựa trên probe.

## Phase 9 live-wiring guardrails (bổ sung 2026-08-13)

Plan/live integration không được suy ra từ harness offline hiện có. Trước khi build phải audit contract runtime thật: `no_agent` không truyền argv cho script; `--workdir` trong no-agent chỉ là cwd của subprocess; runner offline-only không được gọi như live runner; watcher chỉ wire sau khi runner có producer failure-JSONL contract. `*/30 6-25 * * *` là cron không hợp lệ vì hour chỉ 0–23; logical window xuyên nửa đêm phải dùng wrapper tính thời gian động hoặc các job hợp lệ, kèm lease/idempotency chống overlap. SourceConfig global `account_row` unique không đủ cho fleet 80 máy × row 1–6: uniqueness phải là `(machine, account_row)`, nhưng parser hiện vẫn cần rows `1..9` cho overflow/capacity fixtures; chỉ live selector/permit bị giới hạn `1..6`.

Hermes cron deployment phải pilot-first: source wrapper tracked trong repo, deploy/hash-verify vào `%LOCALAPPDATA%\\hermes\\scripts`, target Python explicit, env sanitized, success stdout rỗng. CLI không có atomic paused-create: staging phải snapshot + transaction identity, create one-shot xa trong tương lai, reconcile exact ID kể cả mất stdout, pause ngay, read-back `enabled=false/state=paused`, rồi dùng **`hermes cron edit <id> --schedule ...`** và verify lại; không dùng fabricated `cron update`. `hermes cron run` trên record paused bị runtime từ chối, nên offline smoke giữ record paused và gọi deployed wrapper trực tiếp bằng kill-switch, đồng thời chứng minh cron state không đổi.

Runner tick 15 phút không được chờ mù một feed child dài hoặc dựa vào scheduler timeout để chống overlap: child dài phải có reservation/lease bind PID + creation time + manifest/entry/invocation, tick sau silent no-op; stale lease chuyển `FAILED_LOCKED`/manual-required, không auto reclaim/retry/release. Atomic snapshot trên Windows phải probe primitive thật: file flush/fsync + same-volume `os.replace` và fault-injection; không chép POSIX directory-fsync recipe nếu target Python không mở/fsync directory được.

Chỉ pilot live sau human chọn row 1–6 + máy cụ thể và có artifact summary, ảnh/profile độc lập, ACCEPTED verifier; không coi `report.json` một mình là bằng chứng. Mọi phase phải RED→GREEN bằng test hành vi/declarative spec, không dùng grep làm test; worker report phải được coordinator stat/read/hash độc lập trước audit/build. **Audit approval bind vào SHA-256 exact của plan/diff; edit sau APPROVED bắt buộc re-hash + re-audit.** Worker timeout/outcome-unknown có thể còn writer nền: chứng minh process dừng + hash/mtime ổn định trước cleanup, rồi chỉ revert artifact attributable, không race `git restore` với writer live.

### Phase 9C.2 live pilot + post-pilot fixes (2026-08-15/16)

Single live entry qua `live_entrypoint.run_once` (permit 1 lần + manifest) trên máy thật — recipe đầy đủ: `references/2026-08-15-live-pilot-and-eol-lessons.md`.

- **Permit canonical ≠ pilot permit**: `run_once` dùng `_load_permit` (canonical: 13 keys + `schema_version`); `build_activation_permit` (pilot) thêm `logical_day/expiry/nonce/consumed` → bị reject `permit has unknown keys`. Live entry phải build permit canonical thuần qua `canonical_json`, KHÔNG qua pilot builder.
- **Manifest phải là assignment manifest đầy đủ** (hand-rolled bị `SOURCE_CONFIG_INVALID`): dùng `_entry` + `build_manifest_payload` giống `_live_fixture` trong test — không tự dựng JSON.
- **User REJECT synthetic verifier** ("Nguỵ trang cc gì phiền phức chế đâu ra v"): KHÔNG bắt script tạo `verifier_record.json` chế ra; dùng bằng chứng THẬT script đã viết (`summary.txt` có `final_status: success` + profile screenshot `.../profile_preflight_identity_guard/attempt_1/screen.png`). `_build_observation_from_evidence` build observation từ real artifacts, fail-closed khi thiếu summary/screenshot/success-marker. → **Nguyên tắc: bằng chứng verify phải là artifact workflow thật, không phải file tự chế.**
- Post-pilot code fixes (mỗi cái AG exact-byte APPROVED trước commit):
  - `PYTHON_EXE` phải là Windows path (`D:\...`) không phải MSYS `/d/...` — PowerShell spawn fail `CommandNotFoundException`.
  - `_spawn_subprocess` PHẢI strip `PYTHONPATH` khỏi child env — Hermes session PYTHONPATH (hermes-agent venv) leak làm child resolve PIL sai venv → `cannot import name '_imaging'`.
  - LIVE feed misclassification → guard `_is_live_feed_screen` ở consumer `core/classifier.py` (chi tiết: skill `tiktok-feed-session`).
- **Xác định cấp độ lỗi trước khi fix**: grep consumer nào dùng hàm/classifier — tiktok-follow dùng `core/popup.py` riêng (không qua `detect_allowed_generic_popup`) → fix consumer là đủ; chỉ sửa automation_core khi core chặn mọi consumer.

### EOL/autocrlf + audit re-binding (bẫy lặp đi lặp lại trong live-wiring)

- `core.autocrlf=true` + file baseline mixed EOL (vd classifier.py 681 CRLF + 73 LF) → patch tool đổi CRLF↔LF gây diff toàn file (681/681), `staged hash mismatch`, `git diff --check` báo trailing whitespace trên dòng `\r`.
- **Quy tắc**: normalize toàn bộ file về LF TRƯỚC audit lần đầu; MỌI byte đổi sau APPROVED (kể cả LF normalize) bắt buộc rebuild prompt + re-audit (audit binding = SHA-256 exact). Đừng audit rồi mới normalize — sẽ re-audit 3 lần như session này.
- File `MM` (staged + working modified) sau khi normalize → `git reset -q HEAD -- <f>` rồi `git add -- <f>` lại.
- Diff cho audit prompt dùng `git diff HEAD -- <f>` (bao gồm staged); `git diff -- <f>` (working-only) TRỐNG khi file đã stage → auditor không thấy diff.
- `git add -A -- <deleted-path>` fail `pathspec did not match any files` khi deletion đã staged → dùng `git add -A` không pathspec + verify `git diff --cached --name-only` exact sau đó.
- File mixed-EOL: chèn dòng mới bằng script line-based giữ EOL từng dòng (split `\n`, giữ `\r`, join `\n`), không dùng patch tool (nó LF-hoá cả vùng).
- Worktree có thay đổi external (agent khác sửa AGENTS.md): commit helper phải allowlist chứa cả file đó nếu user yêu cầu "commit luôn", hoặc tách EXTERNAL list không stage.

### Phase 9A.1 identity migration and verification evidence

For a SourceConfig identity migration, the uniqueness key is exactly `(machine, account_row)`, while `account_id` uniqueness, machine↔serial one-to-one mapping, and `require_row` range validation remain independent invariants. The focused test must cover both acceptance of repeated rows on different machines and rejection of duplicate composite identities; add explicit regression assertions for the preserved invariants.

Capture the exact repository-defined regression command and its real count **before any write**. Never use a historical count as an assertion or baseline. The final report must compare post-change count to the captured pre-change count and name any setup blocker separately from test results.

Treat every later verification request as a fresh evidence gate: do not rely on a prior transcript, tool result, or claimed file path. Re-check the absolute target paths immediately before running the focused command and immediately before reporting. If a focused test file is absent, stop and diagnose the live worktree; do not infer that an earlier write persisted, reconstruct it from history, or claim its result. A canonical suite pass that omits the requested focused test is not focused-test evidence.

#### Commit-only closeout guard

When the user requests a commit of an exact allowlist, validate every requested path against the live filesystem and `git status` **before** staging or running a guessed test command. A stale ignored bytecode file, an old plan mention, or a path that appears in another worktree is not evidence that the requested source/test file exists in the current worktree. Also verify that the requested source actually differs from `HEAD`; do not create a no-op commit merely because it is named in the request. If any allowlisted path is missing or the requested change is absent, stop without staging, content edits, or commit and report the blocker plainly. Never reconstruct missing source from `.pyc`, infer a focused test filename from a historical plan, or claim focused/R5 counts that were not produced by the real commands.

For a valid closeout, the evidence order is: baseline status and exact-path existence → canonical tests (if feasible) → `git add --` with only the exact paths → `git diff --cached --name-only` exact-match assertion → `git diff --cached --check` → commit with the exact requested message → `git show --format=fuller --name-status --stat` and post-commit status. Do not push or touch unrelated dirty/untracked files. See `references/phase9a1-identity-verification.md` for the detailed identity/test recipe.

If a verifier requires fresh evidence beyond canonical commands, use a deterministic offline ad-hoc probe in a `tempfile.NamedTemporaryFile` under the OS temp directory with prefix `hermes-verify-`; run it against the real production module with the repository root explicitly importable, assert acceptance plus rejection paths, print the result and cleanup status, and delete it in `finally`. Call this **ad-hoc verification**, not suite green, and still run the canonical focused suite, regression suite, compile, diff-check, and exact allowlist diff inspection. Recipe and evidence labels: `references/phase9a1-identity-verification.md`.

## Hermes cron job — recipe thực tế (auto-sync taikhoan_run_safe, 2026-08-10)

Cron `no_agent=true` + script = watchdog thuần (0 token LLM): stdout RỖNG = silent (không gửi gì),
stdout non-empty = deliver về origin. Dùng cho "sync khi source đổi, im lặng khi không đổi".

1. **Script phải nằm trong `~/hermes/scripts/` và khai báo BẰNG TÊN FILE** — cronjob tool từ chối absolute
   path (`Script path must be relative to ~/.hermes/scripts/`). Pattern chuẩn: thư mục đó chỉ đặt 1 launcher
   mỏng (subprocess gọi python venv chạy wrapper THẬT trong repo) → logic wrapper commit được vào repo,
   launcher thì không.
2. **Schedule quirk — `1m` / `every 1m` / `*/1 * * * *` đều tạo `repeat: once` (one-shot!)**. Phải update
   thêm `repeat=0` → mới thành `repeat: forever`. Luôn verify response có `"repeat": "forever"`.
3. Wrapper tự quyết: stat source (size+mtime_ns) so state file JSON → đổi thì chạy sync + in 1 dòng;
   không đổi → exit 0 không in gì. Lỗi → in `TAIKHOAN_SYNC_ERROR` + giữ `last_error` trong state để retry
   lần sau (không cập nhật signature khi fail).
4. State file đặt dưới `runtime/` trong repo + thêm `runtime/` vào .gitignore (tránh lẫn vào commit khác).
5. Verify: `cronjob action=run` → `last_status: ok`; chạy lần 2 phải im lặng (stdout rỗng = watchdog đúng).
6. Windows task cũ xoá bằng `schtasks /Delete /TN <name> /F` sau khi cron chạy OK.
7. **Watcher fail-closed nếu `report.jsonl` chưa tồn tại (pitfall 18/08 sáng)**: `hermes_cron_watcher.py` gọi `paths.regular_file(report_jsonl)` → raise `INVALID_PATH` nếu file không tồn tại (state-root validator yêu cầu target exists). Cron báo `failed: Script exited with code 1`. Fix: tạo file `report.jsonl` RỖNG (`touch`, KHÔNG `[]` — parser JSONL `[]` là noncanonical → `ValueError: noncanonical report stream`). Tương tự: `feed_state.json`/`post_state.json` thiếu key schema → picker skip im lặng (entries=0). Khi watcher báo `failed` code 1, đọc `cron/output/<id>/*.md` xem traceback trước khi kết luận cron hỏng.

## Concurrent coordinator — CHECK TRƯỚC KHI DISPATCH (2026-08-10)

Cùng lúc HAI session điều phối P1: session Telegram khác cũng đang chạy audit + dispatch worker R8
(codex `--model gpt-5.6-terra --output-last-message ...advisor-result.txt` + worker Luna
`--sandbox danger-full-access` prompt "remediation R8"). Worker R7 dispatch từ session này gặp writer song
song ghi đúng scope lúc 13:01-13:05 — phải pivot sang verify-only (xem `concurrent-workspace-safety`).

Check trước khi dispatch:
- `powershell Get-CimInstance Win32_Process` lọc Name~codex|bash + CommandLine match tên deliverable
  (`hermes_cron|remediation|p1-`) — thấy process của session khác → đừng dispatch trùng scope.
- `grep <session-id> ~/AppData/Local/hermes/logs/agent.log` để biết session nào đang chủ động điều phối.
- Nếu session khác đang drive cùng deliverable → STAND BACK, chỉ poll transcript/result, báo user ai đang
  giữ. Dispatch song song = lãng phí (worker trùng scope phải tự nhường).

## Tiếp nối audit nhiều vòng (R3→R6, pattern đã dùng ổn định)

- Audit chạy background: `codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol`, stdout redirect
  vào transcript `~/AppData/Local/hermes/cache/terminal/p1-independent-audit-r<round>-transcript.txt`.
- **`stream disconnected ... localhost:60818` = Codex API Service (provider `codex_local_access`) down, KHÔNG phải 9router**: 60818 là service nền codex CLI, không watchdog; 9router = port 20128 (watchdog `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1` tự restart). 2 lần retry cùng lỗi = service chết thật, đừng retry nữa → check `Get-NetTCPConnection -LocalPort 60818` (rỗng = chết) → audit model thay bằng `codex exec --ephemeral --sandbox read-only -c 'model_provider="9router"' --model ag/claude-opus-4-6-thinking` (KHÔNG có flag `--model-provider` — phải dùng `-c 'model_provider="9router"'`; prompt qua stdin redirect `< prompt.md` hoặc positional arg, `-p "text"` bị hiểu là `--profile`). Chú ý: combo `gpt-5.6-sol/luna/terra` kể cả qua 9router vẫn cần codex credentials → hết creds = 404 `No active credentials for provider: codex`; dùng `ag/claude-opus-4-6-thinking` hoặc Claude CLI (user rule 16/08). Chi tiết: `references/2026-08-16-feed-farm-python-resolution-audit-fallback.md`.
- **Phát hiện audit ĐANG chạy**: so `stat -c %Y` transcript 2 lần cách ~60-90s — mtime tăng = còn chạy;
  kèm check process bash/codex có CommandLine khớp `p1-independent-audit`. Đang chạy → ĐỢI, không dispatch
  audit mới (tránh double-audit trùng scope).
- **Đọc verdict**: file có thể 500KB+ (tool output đọc từng file) — verdict + findings ở CUỐI file
  (`tail -c 3000`). Format findings là `1. P1 — …` (KHÔNG phải `CONFIRMED_P1`) — grep "CONFIRMED_P" trên
  toàn file sẽ miss. Dòng cuối cùng `REJECT`/`APPROVED` là verdict.
- Sau REJECT: dispatch worker round kế với prompt chứa exact findings (path:line + invariant bắt buộc) +
  yêu cầu RED probe trước khi fix.
- **Guard đa worker cùng repo**: trước khi dispatch, check mtime các file dễ đụng
  (`stat -c '%n %y' <file>`) — file mtime mới = worker khác đang sửa live → CẤM đưa vào scope worker mới
  (session này: benign_popup.py/feed_swipe_smoke.py mtime 12:36-12:44, worker add-phone đang chạy).

## Trạng thái LIVE thực tế (2026-08-16) — HALF-MIGRATED, CHƯA cutover

BẪY PHÂN TÍCH: skill này mô tả PLAN migration rất chi tiết nhưng **KHÔNG ghi trạng thái live** → session phải tốn ~6 tool call mới phát hiện "Hermes cron chưa deploy, Windows Task Scheduler vẫn chạy và đang break". **Luôn verify trạng thái thật bằng lệnh trước khi báo cáo** (recipe: `references/2026-08-16-live-wiring-status-audit.md`):

- **Hermes cron feed/follow CHƯA BAO GIỜ deploy**: `cronjob action=list` chỉ có sync/skills/render/reap, KHÔNG có job picker/runner/watcher. Wrapper `scripts/hermes_cron/tiktok_{picker,runner,watcher}.py` có trong repo NHƯNG (1) CHƯA copy vào `%LOCALAPPDATA%\hermes\scripts\` (`deploy_hermes_cron_wrappers.ps1` chưa chạy) và (2) **default-off**: `if env.get(ACTIVATION_ENV) == "1"` — thiếu `HERMES_CRON_*_ENABLED=1` thì wrapper exit ngay kể cả đã deploy. `hermes_cron_schedule.json` (picker `0 6 * * *`, runner `*/15 * * * *`, watcher `7,22,37,52 * * * *`) chỉ là spec, chưa create job.
- **Windows Task Scheduler vẫn là nguồn chạy thật**: `schtasks /query` thấy `TikTokScheduler` (At logon, `python -m scheduler --live --poll-seconds 30` + env PYTHONPATH/workbook/manifest qua PowerShell) + tray/recovery tasks Enabled/Running; `TikTokAllSchedulerWake`/`TikTokScheduleRecovery` đã Disabled.
- **Task Scheduler ĐANG BREAK 100% từ 14/08**: `python_runner/runs/scheduler.jsonl` toàn `failed` — `ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'`. **ROOT CAUSE THẬT (đã chứng minh 16/08) = version skew automation-core giữa 3 env, KHÔNG phải PYTHONPATH leak** (dù traceback hiển thị path hermes venv — đường dẫn trong traceback chỉ ra env mà process đó resolve, không tự nó là nguyên nhân):
  - `hermes-agent venv` = 0.4.43; **Python312 global** (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312`) = 0.4.44; `D:\Taadaa\python-envs\automation` = 0.4.45. Class `DeviceLockNeedsUserDecision` CHỈ có từ 0.4.45 (thêm ở commit lock-gate `d0bab14`).
  - `run-feed-session.ps1` default `$Python = "python"` → bare python mà Task Scheduler spawn resolve về **hermes venv 0.4.43** (HKCU user env `Path` đặt `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts` ở ĐẦU) → đúng path trong traceback log launcher (`...hermes-agent\venv\Lib\site-packages\automation_core\device_lock.py`). **BẪY `which python`**: shell MSYS resolve bare python về Python312/0.4.44 (PATH MSYS riêng) — suy luận từ `which python` sẽ fix sai env. Ground truth = interpreter path trong traceback của log thật. Chi tiết version matrix + recipe diff wheel additive: `references/2026-08-16-device-lock-import-root-cause.md`. Đồng thời **2 process scheduler sống song song**: automation env python (PID 16692) + Python312 (PID 2856) `-m scheduler --live` — task At-logon spawn trùng qua 2 env.
  - **Fix (đã làm 16/08)**: cài 0.4.45 vào **Python312** (nơi cmd.exe/MSYS bare `python` resolve — qua WindowsApps PythonManager alias → 0.4.44 → ImportError): `python -m pip install --force-reinstall "file:///D:/Taadaa/automation-core-user-lock-gate-wt/dist/automation_core-0.4.45-py3-none-any.whl"` (KHÔNG dùng `/d/...` MSYS path — bị mangle). Verify = probe chạy ĐÚNG loại shell của chuỗi lỗi (`.cmd` probe qua `cmd.exe /d /c`) → `HAS_CLASS=True`, không chỉ pip show.
  - **Audit SOL 16/08 REJECT phương án chỉ cài hermes venv** (lúc đầu tưởng traceback hermes venv ⇒ cài hermes venv là đủ): bare `python` resolve **KHÁC NHAU theo invocation context** — PowerShell `& $Python` trong run-feed-session.ps1 (PATH HKCU, hermes venv Scripts đứng #2) → hermes venv 0.4.43 (khớp traceback log launcher thật); cmd.exe / MSYS bash (PATH có WindowsApps alias đứng trước) → Python312. `which python` trong bash KHÔNG đại diện cho môi trường Task Scheduler. Ground truth luôn = interpreter path trong traceback của log THẬT + reproduce bằng ĐÚNG loại shell, không suy diễn chéo.
  - **⚠️ CÒN DỞ (check session kế tiếp)**: mới cài 0.4.45 vào Python312; **hermes venv vẫn 0.4.43**. Nếu slot feed kế tiếp vẫn fail traceback hermes venv → cài 0.4.45 vào hermes venv, HOẶC (bền hơn — audit đề xuất P1) sửa `run-feed-session.ps1` default `$Python = 'D:\Taadaa\python-envs\automation\Scripts\python.exe'` để không bao giờ phụ thuộc bare-python resolution. Sau cài 0.4.45: restart 2 scheduler (kill PID → `schtasks /run /tn TikTokScheduler`; trước đó đã có 2 process `-m scheduler --live` song song 16692 automation + 2856 Python312, sau restart = 29772 automation + 33456 Python312, chạy sạch không ImportError).
- Feed chết → follow chết theo (follow chỉ chạy qua hook trong feed flow, không luồng độc lập).
- **Code plan 16/08 đã vào `blocks.py`** (anchors 06:00/12:30/19:00, 3 session/ca, jitter ±20, gap 35-60) — offline sẵn sàng, thiếu mỗi live-wiring.
- **Following KHÔNG có scheduler riêng**: không schtasks follow, không Hermes cron follow; chỉ `_run_follow_hook` trong `multi_machine_feed_session.py:500` sau feed success/degraded.
- Hai hướng chiến lược: (A) sửa ImportError để Task Scheduler cũ sống lại (tạm), (B) hoàn tất cutover Hermes cron (deploy wrapper → create job paused → canary 1 máy → verify artifact thật → mới tắt Windows task). Rule 16/08: hỏi user chọn hướng trước khi đụng code.
- **User CHỐT hướng đi 16/08**: làm qua Hermes cron ("cấu hình trực tiếp qua hermes cron đi") — KHÔNG cần plan mới (2 plan APPROVED sẵn: `2026-08-12_185400-phase9-live-integration-cron-wiring.md` cho live wiring + `2026-08-16_follow-hook-3-session-jitter.md` cho 3 phiên/jitter/reactive, code đã vào master). Trả lời quota: **cron no_agent script-only = 0 token LLM** (chỉ phụ thuộc Hermes sống; watchdog ngoài Hermes P5 chưa làm). Khi user hỏi "Window Task cũng làm account-block/jitter/reactive được k" — lưu ý: account-block/jitter thì code được (giờ cố định), nhưng **reactive phiên 2/3 thì Task Scheduler KHÔNG làm được** (giờ tính sau khi phiên trước success → cần daemon loop = chính là scheduler cũ đang lỗi); Hermes cron runner tick 15' đã có lease/idempotency/stale-lease → FAILED_LOCKED sẵn. Trình tự đề xuất đã chốt: fix import core → hoàn thiện live launcher (bật execute, gọi `run-feed-session.ps1` chuẩn) → deploy 3 wrapper + create 3 cron job → canary 1 máy → P6 cutover xóa Windows task.

## Live-wiring STAGING THỰC TẾ (2026-08-16) — 4 bẫy khi bật 3 cron job

Khi chạy `phase9-staging` (`staging.StagedJobSpec` + `run_transaction`) với Hermes CLI THẬT (v0.18.2), fail 4 lần liên tiếp trước khi 3 job `phase9-staging-{picker,runner,watcher}-<txn_id>` đứng paused:

1. **`--script` bắt buộc FILENAME tương đối, KHÔNG absolute**: `hermes cron create ... --script tiktok_picker.py` (script phải nằm `%LOCALAPPDATA%\hermes\scripts\`), lỗi `Failed to create job: Script path must be relative to ~/.hermes/scripts/`. `StagedJobSpec.script` = tên file; hash đối chiếu = hash file installed, không phải spec.script.
2. **create stdout KHÔNG có `Created job: <id>`** → `parse_created_job_id` trả None → `reconcile found 0 candidates` → FinalBlocked → rollback (an toàn, sạch). Phải điều tra canonical adapter, đừng đoán trùng ID.
3. **`cron.jobs.list_jobs` trả schedule là DICT** `{"kind":"once","run_at":...,"display":"once at ..."}` (KHÔNG phải string như doc cũ): `_job_matches_create` so `record.schedule != spec.create_schedule` → `created schedule mismatch`. Phải normalize bằng `_schedule_display()` ưu tiên `run_at`/`expr`/`display` (human display `'once at ...'` KHÔNG khớp ISO spec). Đây là chi tiết version drift CLI thật vs doc — patch `staging.py` thêm helper (đã sửa, chưa commit; cần test + commit sau canary).
4. **Shell quirk khi gọi .ps1 có dấu cách trong đường dẫn**: `powershell -File scripts/deploy_hermes_cron_wrappers.ps1` từ bash bị mangle → `A positional parameter cannot be found that accepts argument 'hermes_cron'`. Dùng `powershell -NoProfile -Command "& 'D:\...\script.ps1' -Param ..."` (literal path trong quote). **Cách này vẫn fail** vì `deploy_hermes_cron_wrappers.ps1` line 23 `Join-Path $RepoRoot 'scripts' 'hermes_cron'` append thừa `scripts` → `$SourceDir` không tồn tại → PowerShell 5.1 `Resolve-Path` trên path không tồn tại ném. **Workaround đã dùng**: copy byte thủ công + `sha256sum` verify từng file source vs installed (không sửa script approved). **CÒN DỞ**: nên thu hẹp `templates` cho deploy script này (fix path bug) hoặc ghi chú dùng workaround thủ công.
5. **Kết quả mong đợi khi thành công**: journal `state: paused`, `cron list` thấy job `enabled:false state:paused` schedule đã edit đúng (`0 6 * * *` / `*/15 * * * *` / `7,22,37,52 * * * *`). **`repeat:"once"` trong list là BÌNH THƯỜNG cho job staged paused** — không phải lỗi (mặc định create repeat=1, sẽ resume/sửa repeat sau khi canary OK). Resume/bật = user duyệt + `cronjob update` hoặc CLI, không tự resume.

Khi staging fail: kiểm tra trước `cronjob list` có job orphan `phase9-staging-*` không — transaction có rollback nhưng thỉnh thoảng để lại record → xóa bằng `cronjob action=remove` đúng ID. Chi tiết từng lần fail + spec đúng + trạng thái session: `references/2026-08-16-live-wiring-staging-pitfalls.md`.

## Canary N máy = MỘT session multi-machine (2026-08-17, user chốt)

Khi user duyệt "cho 5 máy đầu chạy đi" — **CẤM loop `run_once` từng máy** (mỗi permit/máy = 1 feed session riêng → 5 máy tuần tự ~2-2.5h — user: "5 máy sao k chạy cùng nhau"). Đúng: gọi **1 lần** `run-feed-session.ps1` với `-Machines 1,2,3,4,5` → workers song song, ~25-30' tổng.

- **TRƯỚC canary (bắt buộc)**: dừng + DISABLE Task Scheduler cũ để 2 luồng không đè máy:
  `schtasks /end /tn TikTokScheduler` + kill process `-m scheduler --live` (kill → disable `schtasks /change /tn TikTokScheduler /disable`) → verify không còn process match `scheduler --live|run-feed-session|run_tiktok`.
- **3 nhánh `run-feed-session.ps1` — đọc kỹ TRƯỚC khi gọi (bẫy 3 chiều)**:
  - `-Preset full` (có hoặc không kèm `-Machines`) → vào nhánh Preset: discover TOÀN BỘ máy row từ workbook (`list_feed_session_machines`), **`-Machines` bị BỎ QUA**; assignment gate lọc theo manifest (khi không LocalRun). Env session kế thừa Task Scheduler cũ (`TIKTOK_FEED_ASSIGNMENT_MANIFEST=tiktok-feed.json` resources máy 1–74, `TIKTOK_FEED_WORKER_ID=taadaa-writer-…`) → `-Preset full -Machines 1,2,3,4,5` **CHẠY 73 MÁY THẬT** (accident 17/08 tốn 1h). CHECK env: `echo $TIKTOK_FEED_ASSIGNMENT_MANIFEST` trước khi gọi.
  - `-LocalRun` → **BẮT BUỘC `-Preset full` VÀ CẤM kèm `-Machines`** (throw `LocalRun cannot be combined with -Machines`, ps1:106; thiếu Preset throw `LocalRun requires -Preset full`, ps1:103) → chạy toàn bộ máy row, bỏ gate assignment — KHÔNG dùng để canary N máy.
  - **Đúng cho đúng N máy**: `powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 -Row <R> -Machines 1,2,3,4,5 -Run -SkipAccountWorkbookSync -MachineStartStaggerMs 2000,8000 -RandomizeMachineOrder -ArtifactRoot <dir> -Python D:\Taadaa\python-envs\automation\Scripts\python.exe` — KHÔNG Preset, KHÔNG LocalRun → nhánh else (ps1:188+) chỉ chạy đúng máy list, assignment gate cần `-AssignmentManifest`/`-WorkerId` (env kế thừa OK với resources 1–74 = siêu tập; hoặc tạo manifest canary resources ⊆ máy cần). Xác nhận trước khi chạy: `grep -nE 'if \\(-not \\$Preset|LocalRun cannot' scripts/run-feed-session.ps1` (dòng 98-108).
- **Serial máy 1-5** lấy từ `D:\OneDrive\Tiktok\Tik1.xlsx` sheet `TaiKhoan` (cột `device ID`) — KHÔNG có config `D:\CodexRuntime\tiktok-video\config-machine-N.yaml` (đã check, không tồn tại).
- Verify kết quả từng máy: `artifact_root/<ts>/machines/machine_N/<ts>/summary.txt` (`final_status: success`) + `follow_result.json` (`exit_code:0, status:OK, followed_count` có thể 0 — organic follow random). `selected_total_videos = random 15-30`, success = `completed_swipes >= selected_total`.
- ⚠️ **`followed_count: 0` trong follow_result KHÔNG được coi là "không follow"** — đọc `runs/state/follow_state_<máy>.json` (followed dict kèm timestamp) LÀ NGUỒN SỰ THẬT. Đã gặp: máy 1 follow_result `{"status":"OK","followed_count":0,"followed":["yabsley1990",...5 nick]}` — count sai nhưng follow THẬT đã chạy (state_1 có nick 00:23-00:31). Xem phần "follow hook followed_count bug" dưới đây.

### follow hook — `followed_count` bug khi `FOLLOW_RESULT.followed` là list (fix 17/08)

- **Bug**: `_run_follow_hook` (multi_machine_feed_session.py ~587) cũ dùng `int(parsed.get("followed", 0))` → khi `FOLLOW_RESULT {"followed": ["nick1","nick2",...]}` (list) → `int(list)` TypeError → bị swallow bởi `except (ValueError, TypeError)` → `followed_count` giữ 0 dù hook ĐÃ follow thật (follow_state tăng nick). Nhầm thành "organic follow 0" nếu chỉ đọc follow_result.
- **Fix (ĐÃ COMMIT 17/08, `9bfec1e`)**: `followed_list = parsed.get("followed"); result["followed_count"] = len(followed_list) if isinstance(followed_list, list) else int(followed_list or 0)`. Verify logic bằng MOCK parse (`parsed={'followed':['a','b','c']}` → count 3), chạy cách ly PYTHONPATH="" để import đúng automation_core 0.4.46.
- **Không có test nào cover `_run_follow_hook`/FOLLOW_RESULT parse** (grep tests không thấy) — thêm test là việc nên làm sau.
- Chi tiết 2 bug + bảng evidence + lệnh reproduce: `references/2026-08-17-follow-count-bug-and-canary-debug.md`.
- **Phân biệt 2 nơi trả identity-mismatch trong follow repo** (debug máy 2/3/5): `follow_one_uid` sau search trước tap = `skipped "ID không khớp"` (không dừng session); `verify_after_tap` sau tap follow = `MANUAL_REVIEW: exact profile identity không khớp sau tap` (verify_follow.py:296, dừng session fail-closed). Máy 2 = `OPEN_TIKTOK_FAILED`, máy 5 = `VERIFY_IDENTITY nick không khớp @khnh.vyyyy6` — đều là lỗi tiktok-follow (mở app/search/identity), không phải feed; mỗi máy cần bằng chứng screenshot/XML riêng trước khi fix.

### Debug canary máy manual-needed: classifier account-switcher (user correction 17/08)

- **User rule**: "3 nick kệ cha nó, mở lên tìm đúng nick đúng row thì chọn" — flow PHẢI tự chọn nick row đúng khi account switcher mở, KHÔNG manual. `feed_swipe_smoke` ĐÃ có cơ chế: `_find_account_switch_option(xml, expected)` → `_tap_ui_element(... action="tap_expected_account")` → `verify_selected_account` — nhưng bị chặn TRƯỚC bởi classifier.
- **Fix (ĐÃ COMMIT 17/08, `9bfec1e`)**: bỏ điều kiện class, chấp nhận mọi element `selected=\"true\"` + có text/desc. KHÔNG đụng automation_core (cấp độ: grep consumer dùng hàm nào trước; classifier là consumer-local).**Verify fix bằng XML THẬT máy fail**: `classify_tiktok_screen` → phải ra `manual-needed:account-switcher` (0.9) + `_is_legitimate_profile_account_switcher_xml(xml, expected)` = True → flow tự chọn nick row đúng (máy 3 đã PASS 29/29 sau fix, tự chọn `trangtran168432` row 1). Test `test_classifier.py` + `test_account_switcher.py` = 71 passed.
- **Triệu chứng "TikTok focus lost" sau switcher**: đọc `extra` trong log.jsonl (`detected_screen: com.android.systemui`, `safety_status: failed`) + screenshot lúc đó — đừng đoán. Switcher mở đúng (title "Chuyển đổi tài khoản" + danh sách nick) nhưng classifier chặn → flow loay hoay → mất focus. Fix classifier là đủ.
- **⚠️ MÁY 5 wave-2 (canary row 5, 17/08 tối): tap nick THÀNH CÔNG nhưng vẫn manual-needed** — KHÁC classifier-blocked: flow `tap_expected_account` (đúng nick thachkieu05, XML xác nhận) → 7-18s sau `verify_tiktok_focus`/`verify_*_navigation_blocker` thấy `focused_package: com.android.systemui` → "TikTok focus lost" → fail-closed. Root cause: **đổi account → Vi Changer VPN reconnect bắn notification "VPN Connected" → notification shade mở đè TikTok**. Máy 21/34 cùng chuỗi tap nhưng THÀNH CÔNG = VPN không reconnect vào đúng khoảnh khắc đó (race). Bài học: khi tap nick OK mà verify fail focus, check XML/XSHOT verify xem có shade systemui (battery/clock/VPN notification trong tree) không; hướng fix = dismiss shade sau tap nick + retry verify focus 1-2 lần, KHÔNG fail ngay. Cũng đừng kết luận "không chọn được profile" khi log đã có tap_expected_account success.
- **⚠️ Popup "Thêm số điện thoại" dạng BOTTOM SHEET không detect (máy 5, 17/08 tối)**: TikTok render popup add-phone dạng bottom sheet ("Trang tính dưới cùng"), close X nằm ở góc phải CỦA SHEET (bounds `(936,804,1056,936)` — top=804 > 350). Core `_close_candidate` (automation_core/tiktok/benign_popup.py:374) loại mọi close có `top > 350` (giả định close X góc trên màn) → `detect_add_phone_popup` trả None → classifier ra `for-you` 0.89 dù XML đầy đủ marker ("Thêm số điện thoại", "+84", "Số điện thoại", "Tiếp tục", desc 'Đóng') → flow không dismiss popup → keyboard xiaowei bên dưới → keyboard cleanup fail → manual-needed. **Triệu chứng chẩn đoán nhanh**: classifier ra `for-you` nhưng ẢNH có popup add-phone + XML có đủ marker → nghi ngờ close-candidate geometry, test `detect_add_phone_popup(root)` trực tiếp bằng XML artifact thật. Fix consumer-local (KHÔNG sửa core): `python_runner/core/benign_popup.py::detect_add_phone_popup` thêm fallback `_bottom_sheet_close_candidate` (nhận close label Đóng/Close/×/X bất kể vị trí khi 4 content markers đủ) → detect ra `add_phone` + classifier `manual-needed:add-phone` 0.98 → `dismiss_add_phone_popup` được gọi đúng. Verify: test trực tiếp bằng XML artifact máy fail trước khi chạy máy thật; test_classifier + test_account_switcher = 71 passed. LƯU Ý: popup này có thể chỉ mở 1 lần (run kế tiếp không thấy) — luôn test với XML artifact đã lưu, đừng chỉ dựa run lại máy.
- **Feed success ≠ follow success — follow hook chạy RIÊNG sau feed**: feed máy 3 PASS 29/29 nhưng `follow_result.json` = `MANUAL_REVIEW: exact profile identity không khớp sau tap` (follow_failed=true, dừng) — lỗi nằm ở tiktok-follow `verify_after_tap` (dòng 296), KHÔNG phải feed/switcher. Phân biệt 2 chỗ trả `identity_mismatch`: `follow_one_uid` (SAU search, TRƯỚC tap) = "skipped ID không khớp" (không dừng session); `verify_after_tap` (SAU tap follow) = MANUAL_REVIEW (dừng). Chi tiết luồng + cách debug: `references/2026-08-17-canary-and-live-wiring-lessons.md`.
- **Serial/account mapping khi debug**: workbook `taikhoan_run_safe.xlsx` (D:\OneDrive\TaadaaData\kibe) — dòng theo `(máy, row)`: máy 3 row 1 = `trangtran168432`, row 2 = `ninhy05100`... So sánh nick đang active trong switcher vs nick row expected để biết máy đang login sai nick.
- **User workflow khi nhiều máy fail (17/08 tối: "fix từng máy, đến máy nào gửi ảnh máy đó")**: KHÔNG debug đại trà nhiều máy cùng lúc — xử lý TỪNG máy tuần tự, với MỖI máy phải gửi ảnh (screenshot artifact thật qua MEDIA:) + phân tích log riêng cho máy đó trước khi sửa. Khi nói "máy 5 trước, tại sao k chọn đc profile" — trả lời đúng câu hỏi của máy đó (log tap_expected_account + XML verify), không lan sang máy khác.
- **⚠️ CẤM tự chạy follow-verify trên máy LIVE khi chưa hỏi (correction 17/08, máy 5)**: chạy `run_follow.py --machine 5 --account-ready-only` để debug lỗi VERIFY_IDENTITY làm `prepare_device` **force-stop TikTok** → user thấy recent app bị đóng ("t thấy m vừa close recent app máy 5") → sai rule live-ops. Quy tắc: máy live đang vận hành farm → trước khi chạy BẤT KỲ runner nào đụng device (kể cả chế độ verify/read-only-ish như account-ready) phải (1) hỏi user, hoặc (2) chỉ đọc bằng adb dumpsys (focus/wakefulness/tun0) KHÔNG gọi runner. Và đừng kết luận "máy lỗi" từ 1 lần fail đêm khuya khi sáng nó vào acc bình thường — check trạng thái hiện tại (focus = TikTok SplashActivity + tun0 UP = bình thường) trước khi chẩn đoán; màn hình launcher/ViChanger LoginActivity lúc đó chỉ là trạng thái tạm/thoát app, không phải lỗi.
- Evidence đầy đủ + ảnh/lệnh reproduce: `references/2026-08-17-canary-and-live-wiring-lessons.md`.

### VPN preflight — cơ chế mapping-exemption (automation_core/preflight.py, trả lời user 17/08)

User hỏi "sao 1 số máy k có vpn vẫn đc phép chạy" — cơ chế bắt buộc check VPN NẰM trong automation-core, KHÔNG phải consumer:

- `core/vpn_preflight.py: require_vichanger_connected(adb, serial)` → `automation_core.preflight.serial_is_mapped_in_workbook(PROXYgandienthoai.xlsx, serial)` → `required=True/False` → `require_android_vpn(adb, required=required)`.
- **`check_android_vpn` (preflight.py:127): `if not required: return AndroidVpnPreflight(...allowed)` — BỎ QUA check VPN HOÀN TOÀN** khi serial KHÔNG có trong workbook mapping (mapping exemption, thiết kế cố ý). Khi `required=True` mới check `tun0` UP + `dumpsys connectivity` VPN; fail = `ConsumerPreflightError("required Android VPN is not connected")` → `blocked-vichanger-vpn`.
- Mapping path resolve: `AUTOMATION_PROXY_MAPPING` → `TIKTOK_PROXY_MAPPING` → default `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (kibe). Khi session kế thừa env Task Scheduler cũ, cả 2 env đều trỏ kibe.
- **Kiểm tra thật 17/08**: kibe farm 80/80 serial ĐỀU có trong `PROXYgandienthoai.xlsx` → MỌI máy 1-80 bắt buộc VPN (đợt 73 máy: 0 máy bị VPN block). **Farm admin 200+: `D:\OneDrive\TaadaaData\admin\` KHÔNG có file PROXY*.xlsx nào** → serial admin không tìm thấy trong mapping kibe → `required=False` → **mọi máy admin exempt khỏi check VPN** = chính là "máy không VPN vẫn chạy" user quan sát. Đây là lỗ hổng tiềm tàng (admin farm chạy không gate VPN) — HỎI user trước khi sửa, không tự tạo file mapping.
- Cách verify nhanh 1 máy: `PYTHONPATH="" python -c "from automation_core.preflight import serial_is_mapped_in_workbook; ..."` với đúng workbook mapping của máy đó (đừng chạy thiếu env → resolve nhầm kibe).

#### User CHỐT rule VPN (17/08 tối) — "k bật vpn thì k đc chạy"

> "Tóm lại k bật vpn thì k đc chạy, phải reboot để cho gan proxy thử bật vpn cho máy đó (reboot 1-2 lần tránh loop lỗi do gan proxy) r ms cho chạy"

- **KHÔNG VPN = KHÔNG CHẠY** (bất kể máy nào). Mapping-exemption im lặng = bug, không phải tính năng.
- **Recovery VPN fail**: GanProxy reassign thử bật VPN → **reboot máy 1-2 lần** (tránh loop lỗi do gan proxy) → verify VPN lại → mới cho chạy. Vẫn fail → block máy.
- **Core ĐÃ có sẵn cơ chế gần đúng**: `automation_core/device_recovery.py` `recover_missing_android_vpn(adb, serial, live_vpn_verifier)` = mark `proxy_pending` → chờ GanProxy watcher bật (`wait_for_proxy_ready`) → fail thì `soft_reboot_and_wait` (reboot + unlock + chờ proxy ready) → fail nữa `MissingVpnRecoveryError FINAL_BLOCKED`. **Core hiện reboot 1 lần sau reassign fail** — user muốn 1-2 lần; nếu cần 2 lần phải sửa core (hỏi user).
- **ĐÃ FIX TOÀN BỘ (17/08 tối, hướng A + user chốt semantics)**: user chốt "máy CÓ map vpn mới bắt buộc vpn; máy k map thì kệ nó chạy direct" (= GIỮ mapping-exemption cho máy unmapped) + "không bật vpn thì không chạy" cho máy mapped + recovery qua GanProxy reassign → reboot 1-2 lần → verify lại → mới chạy. Implementation hoàn tất, commits:
  - **Core `automation_core 0.4.46` (commit `2db001e`)**: thêm `resolve_proxy_mapping_path(env, filename)` — mapping bắt buộc từ `TAADAA_HOST_CONFIG` workbook_root (hoặc env explicit), **fail-closed**: host không có PROXY file → `ConsumerPreflightError` (KHÔNG fallback kibe, không exempt nhầm máy admin); không host + không env → raise luôn. `serial_is_mapped_in_workbook` semantics GIỮ NGUYÊN (unmapped → required=False → exempt) — KHÔNG đổi fail-closed cho unmapped (user chốt).
  - **Repo này (`vpn_preflight.py`, commit `9bfec1e`)**: `DEFAULT_PROXY_MAPPING` = `resolve_proxy_mapping_path()` (host-aware); `require_vichanger_connected(adb_path, serial, *, recover=True)` giờ: mapped → `require_android_vpn(required=True)` fail → **`recover_missing_android_vpn`** (reassign GanProxy → soft-reboot 1 lần → verify `_vpn_up` = `check_android_vpn(required=True)`) → vẫn fail → `ConsumerPreflightError` (không bao giờ chạy không VPN). unmapped → `require_android_vpn(required=False)` direct (như cũ).
  - **Các repo khác (pattern giống nhau, patch bằng script, mỗi repo 1 commit)**: `tiktok-log-in/login_runner/{cli.py, account_reconcile.py}` + `tiktok-add-bao-mat-f2a/python_runner/run_batch_live_2fa.py` — thay hardcode `DEFAULT_PROXY_MAPPING` bằng `_resolve_proxy_mapping()` gọi resolver core.
  - **ĐỢT 2 — final all-repo scan (17/08 tối, sau khi user hỏi "áp dụng all repo chưa")**: scan `grep -rln "OneDrive.TaadaaData.kibe.PROXYgandienthoai" --include=*.py /d/Taadaa` (loại `venv|site-packages|__pycache__|.git|build/|dist/|automation-core|node_modules|.bak|context-worktrees|jitter-backup|gmail-jitter-backup|.ai-runs|tests/`) bắt nốt các repo còn hardcode:
    - `add mail khoi phuc/run_add_recovery.py` — CÓ hardcode kibe (sửa cả nhận định cũ "không đụng") → patched + commit.
    - `register gmail/{gmail_reg_v10.py, guarded_device_reboot.py}` — patched trực tiếp file (KHÔNG phải git repo, không commit được).
    - `Hotmail/flows/hotmail_login.py` — patched trực tiếp; ⚠️ cảnh báo sibling subagent có thể đang sửa file này — đọc lại trước khi write.
    - `gan-proxy/scripts/gan_proxy_fleet.py` — chain `GAN_PROXY_MAPPING → AUTOMATION_PROXY_MAPPING → TIKTOK_PROXY_MAPPING → resolver core`.
    - worktree `tiktok-log-in-recovery-adapter-p2-wt/login_runner/cli.py` — git worktree nhánh khác, patch + commit RIÊNG (đừng nhầm với repo main).
  - **Pattern patch repo non-git / worktree**: `str(__import__("automation_core.preflight", fromlist=["resolve_proxy_mapping_path"]).resolve_proxy_mapping_path())` — gọn, không cần sửa import block.
  - **LOẠI TRỪ đúng (KHÔNG patch)**: `Tiktok_Reg` (chỉ comment "synced from PROXYgandienthoai.xlsx" + `PROXY_MAP_PATH = D:\PROXYgandienthoai.xlsx` — device-map file riêng, không phải VPN gate runtime), backups/`jitter-backup`/`gmail-jitter-backup`/`context-worktrees` (không active), `gan-proxy/tests` (test fixture).
  - **Verify cuối**: chạy lại cùng scan → **0 file runtime còn hardcode**; mỗi file patched `py_compile` OK; repo git có commit message chuẩn `fix(vpn): host-aware proxy-mapping resolution (fail-closed, no kibe fallback)`.
  - **Cài 0.4.46 vào CẢ automation env + Python312** (`--force-reinstall --no-deps --no-cache-dir`; lần đầu chạy không `--no-cache-dir` vẫn hiện 0.4.45 — pip cache). Verify bằng import thật `PYTHONPATH=""` (tránh hermes venv vẫn 0.4.43 che).
  - **Test**: core `test_preflight.py` 7 passed + `test_device_recovery.py` 47 passed; consumer `test_multi_machine_feed_session.py -k "vpn or mapping"` 2 passed; tiktok-log-in 29 passed; add-bao-mat 18 passed.
  - **CÒN DỞ (check session kế)**: patch `vpn_preflight.py` + `staging.py` chưa test đầy đủ full suite? (đã commit); `PIP install` hermes venv vẫn 0.4.43 — nếu feed qua PowerShell bare-python vẫn resolve hermes venv → cài 0.4.46 vào hermes venv hoặc sửa `run-feed-session.ps1` default `$Python` (audit P1). Cron job `reap-dead-owner-locks` vẫn 401 (LLM-driven, chưa chuyển no_agent).
- Chi tiết implementation + pipeline patch all-repo + verify evidence: `references/2026-08-17-vpn-gate-all-repo-fix.md`.

### Hermes cron LLM-driven job — 2 lỗi runtime (model drift + 401), no_agent là pattern an toàn

Job cron `no_agent: false` (LLM-driven, có `enabled_toolsets`) trên máy này gặp 2 lỗi runtime liên tiếp (job `reap-dead-owner-locks`, 17/08):

1. **Model-drift guard (#44585)**: `RuntimeError: Skipped to prevent unintended spend: global inference config drifted since this job was created (model 'deepseek-v4-flash' -> 'worker'), and this job is unpinned.` — job tạo khi global model cũ, unpinned → khi global model đổi, cron TỪ CHỐI chạy. Fix = `cronjob action=update job_id=... model={model,provider}` (pin model hiện tại hoặc model cũ).
2. **`HTTP 401: {"error":"API key required for remote API access"}`** sau khi pin: cron runtime gọi model qua provider `custom:9router` KHÔNG có API key trong context chạy cron (key chỉ có trong session Hermes tương tác) → pin model xong vẫn fail. **Toàn bộ job cron no_agent=true script-only (sync-hermes, taikhoan-run-safe, tik3 watchdog) chạy `last_status: ok` vì KHÔNG inference** → pattern chuẩn cho farm này: job cron PHẢI no_agent script-only (0 token, 0 key); job cần LLM nên là `deliver:local` + script tự quyết, hoặc chuyển logic sang script thuần. Đừng hứa "pin model là xong" cho LLM cron job trên 9router — verify `cronjob action=run` sau pin, nếu 401 → chuyển no_agent.
3. Chỉ riêng job này model pin đang set `deepseek-v4-flash`/`custom:9router` (trạng thái 17/08, job vẫn `last_status: error` do 401) — chưa chuyển no_agent vì chưa có user duyệt; check session kế tiếp.
4. **✅ ĐÃ FIX 17/08 tối (sau khi user hỏi "cron sao phải cần key AI, tưởng tự vận hành ngầm như window schedule")**: chuyển `reap-dead-owner-locks` sang **no_agent script-only** — `cronjob action=update job_id=b63730cc5c85 no_agent=true script=reap-dead-owner-locks-wrapper.py workdir=<repo>` + tạo launcher mỏng trong `~/AppData/Local/hermes/scripts/` (subprocess gọi automation python chạy script thật trong repo) → `cronjob action=run` → **`last_status: ok, execution_success: true`**, output `Mode: no_agent (script)`. **Bài học user chốt**: cron farm = phải tự vận hành script thuần như Windows Task Scheduler (0 key, 0 token); KHÔNG thêm key vào `Hermes_Gateway.vbs` cho LLM-job (gateway VBS chỉ set HERMES_HOME/PYTHONPATH/... nên process gateway THIẾU `NINEROUTER_API_KEY` → mọi LLM cron job qua custom:9router 401; dù thêm key vào VBS cũng cần restart gateway — không đáng khi no_agent sạch hơn).
5. Các job cron farm MỚI tạo: **mặc định `no_agent=true` + script wrapper mỏng** (0 token/key), đừng tạo LLM-driven có `enabled_toolsets`. Verify sau create bằng `cronjob action=run` → `last_status: ok`.

## ⚠️⚠️ THIẾT KẾ ĐÚNG = 3 CA × 3 PHIÊN/NGÀY (user đính chính 18/08 — ROW-SLOT 6-row/ngày LÀ SAI)

> **User 18/08 sáng: "Làm đéo có chuyện 1 ngày chạy 6 row thiết kế bị ngu à? Đọc lại thiết kế" — phủ định row-slot 17/08 (1 entry/acc theo 6 row cố định = 1 máy chạy tới 6 lần/ngày).** Thiết kế CHÍNH THỐNG = plan 16/08 APPROVED:
> - **1 máy 1 ngày: 3 CA (06:00 / 12:30 / 19:00), mỗi ca 1 acc, mỗi acc 3 PHIÊN 60' → tổng 9 phiên/ngày/máy.**
> - Phiên 1: anchor + jitter ±20'. Phiên 2/3: **REACTIVE** — chỉ chạy sau phiên trước SUCCESS + nghỉ random 35-60' (giờ tính runtime, không ghi cứng). Cap 3 phiên/acc/ngày.
> - **Chọn acc theo PARITY row (user chốt CUỐI 18/08 — thay cho lane liền 1-3/4-6)**: ngày LẺ → rows **1,3,5**; ngày CHẴN → rows **2,4,6**. Mỗi ca 1 acc; ca 06:00 = row đầu nhóm, 12:30 = row giữa, 19:00 = row cuối (vd ngày lẻ: ca1→row1, ca2→row3, ca3→row5). **Nick GIỮ GIỜ CỐ ĐỊNH theo row — KHÔNG random thứ tự acc trong nhóm** (row 1 luôn ca 06:00, 2 ngày 1 lần qua parity). Máy thiếu acc row ca đó → bỏ ca (không bắt buộc đủ 3).
> - **Rationale ông anh tổng**: tránh ngày toàn nick yếu đi follow (dễ bị TikTok flag). Parity đảm bảo mỗi ngày luôn có ≥1 nick 'mạnh' (row 1 hoặc 2) đi cùng yếu — follow từ nick có lịch sử tốt an toàn hơn. Kết hợp: nick yếu follow budget THẤP hơn (xem video gate dưới).
> - Switcher chỉ phiên 1 (cùng acc trong ca); verify nhẹ phiên 2/3. Organic follow 6%; follow chéo 3-7/phiên; max_workers 30.
> - Nguồn chi tiết: `.hermes/plans/2026-08-16_follow-hook-3-session-jitter.md` + `blocks.py` (BLOCK_ANCHORS 06:00/12:30/19:00, 3 session/ca).
> - ⚠️ **Bài học: user nói "bỏ lane/đủ-3-acc đi" 17/08 KHÔNG có nghĩa bỏ block/session — chỉ bỏ RÀNG BUỘC lane đủ 3 acc khiến máy ít acc bị skip. Khi user chốt thiết kế, đối chiếu lại PLAN đã APPROVED (16/08) trước khi viết lại picker từ đầu; đừng tự diễn giải thành model mới (6 row/ngày) mà chưa xác nhận với user.**

ROW-SLOT picker 17/08 (đã commit — hiện TRONG CODE) vẫn giữ ở dưới làm HISTORY: 1 entry/acc, bỏ lane bắt buộc, slot theo 6 row — **nhưng user đã xác nhận đây là hiểu sai thiết kế (chạy 6 row/ngày = sai), cần sửa lại về 3 ca × 3 phiên trước khi coi cron live đạt chuẩn.** Chi tiết row-slot đã implement: `references/2026-08-17-row-slot-cutover.md`.

- **1 entry/account**, slot_time cố định theo `account_row`: {1:'06:00', 2:'08:00', 3:'10:00', 4:'12:30', 5:'15:00', 6:'17:30'}. Manifest `blocks=[]`; entry KHÔNG có block_id/session_index. Máy không có acc trên row → KHÔNG có entry row đó (skip tự nhiên — đúng ý user).
- `generate_cron_source_config.py`: cho phép physical slots không liên tục (1,2,4 — 8 máy có hàng 3 trống: 22,33,34,39,40,53,61,66). GIỮ row vật lý, KHÔNG nén acc (user chốt B). Builder script thật: `D:\Taadaa\tmp_build_cron_inputs.py` (ngoài repo) — projection + journal + feed/post state từ `taikhoan_run_safe.xlsx`; serial thật từ `Tik1.xlsx` device map (⚠️ máy 38/66 trong safe workbook có serial bị nhập nhầm thành ngày `21/07/2026`).
- **State JSON schema bắt buộc (blocker thật 17/08 — INVALID_FEED_STATE 41 acc)**: `feed_state.json`/`post_state.json` KHÔNG phải `{"status":"ready"}` đơn giản — picker validate STRICT key set. Feed state cần 5 keys: `account_id, last_feed_success_at (None), unresolved_reservation (False), terminal_facts ([]), state_revision`; post state cần `account_id, status (DUE), video_available (bool), target_count (int|None), state_revision` — và **`state_revision` PHẢI khớp `state_revision` trong source config** (đọc từ `feed_state_revisions`/`post_state_revisions` SAU khi generate config). Journal facts cho generator chỉ cần `{"status":...}` (generator hash chúng), state JSON runtime mới cần full schema. Sai schema → picker skip `INVALID_FEED_STATE`/`POST_STATE_UNAVAILABLE` im lặng (entries=0 trông như picker hỏng).
- `feed_session_workbook.py`: row chọn mà username rỗng → config error skip máy (thêm check `not account.expected_username`).
- `manifest.py` validate no-block: max 6 starts/máy, min gap 90' (row slots cách ≥120' nên pass). Golden vector contract test đã cập nhật theo row-slot.
- **MaxWorkers = 30** (user chốt "đã đc chứng minh 30 vẫn ổn"): `run-feed-session.ps1` `[int]$MaxWorkers = 40` → `30`.
- **State layout**: `D:/Taadaa/runtime/kibe/cron-state` (NGOÀI repo!) — manifests/<day>/ + journal/ + snapshot_bundles/; offline_root = PARENT của state_root (StatePaths yêu cầu `off in resolved.parents`). Source config: `D:/Taadaa/runtime/kibe/cron-source/hermes_cron_source_config.json`. Xóa manifest cũ để re-pick: rm CẢ `manifests/<day>/` LẪN `snapshot_bundles/<day>/` bằng path đầy đủ (relative path trong repo sai chỗ).
- Picker qua wrapper: `--seed` chỉ PICKER cần; runner/watcher argparse KHÔNG nhận --seed → wrapper runner/watcher KHÔNG được append (exit 2).
- **Follow hook LUÔN `--skip-identity-verify` (user chốt cuối 17/08)**: "lúc chọn acc lướt đã chọn acc chuẩn r, follow hook vào follow liền luôn đéo cần verify" — `_run_follow_hook` (multi_machine_feed_session.py) thêm flag `--skip-identity-verify` vào subprocess run_follow; bên follow engine khi flag bật bỏ `switch_account_and_verify`, set `active_account_handle = row.tik_id` thẳng rồi follow. Feed preflight đã chọn đúng nick row → verify lại = thừa + dễ dương tính giả (VPN shade/lag). Đừng quay lại "follow hook phải verify identity".
- **Chu trình Pipeline Ca/Phiên chuẩn (User chốt 26/08)**:
  - Phiên thường (phiên 1 & 2 trong ca): **Nuôi feed ➔ Follow hook (`tiktok-follow`)**.
  - Phiên cuối ca (phiên 3): **Nuôi feed ➔ Follow hook ➔ Upload video**.
  - Phân định 2 nguồn follow: Organic feed 20% tại nhịp Deep Inspect tab For You + Follow chéo từ script `tiktok-follow` sau khi hoàn thành feed.
- **Video gate 3 bậc (user chốt 18/08, commit `8f6aa26` tiktok-follow):** follow budget theo `Video Đã Đăng` của nick — `≥10` → FULL (6-10/phiên), `1-9` → NỬA (3-5), `=0` hoặc chưa có cột/file (tik4 chưa tồn tại) → 1/3 (2-3). `None` (thiếu cột) tính NHƯ 0 video (nick mới chưa upload KHÔNG follow nhiều). Logic: nick yếu (ít video) follow ít → tránh flag. Đừng set budget cố định cho mọi nick; nếu ticket failed follow từ nick yếu, GIẢM budget chứ không tăng.
- **Timing sau dismiss popup + ATX stub restart (máy 5/máy 19 row 5, 17/08 tối)**: `_sleep_and_recapture` 0.8s→2.5s (deny popup xong chờ host app trả foreground trước khi verify focus); restart stub `com.github.uiautomator` bằng `monkey -p` (am startservice fail); follow hook dùng code trực tiếp từ repo tiktok-follow (không copy). Chi tiết: `references/2026-08-17-canary-row5-timing-and-atx-stub.md`.
- **Popup "Follow bạn" → bấm "Không quan tâm", TUYỆT ĐỐI không "Follow lại" (user chốt 17/08 tối, máy 33)**: TikTok hiện popup gợi ý khi có người follow nick (text "Follow bạn" + 2 nút "Follow lại"/"Không quan tâm"). Flow feed gặp popup này → nếu thiếu rule sẽ `classify manual-needed:gemphonefarm_blind_popup` → dừng giữa feed (swipe 12 máy 33). Encode vào `GEMPHONEFARM_BLIND_POPUP_RULES` (feed_swipe_smoke.py, tuple dòng ~741): rule `follow_friend_dismiss` — detect `//node[@text="Follow bạn"]` → tap `//node[@text="Không quan tâm" and @class="android.widget.Button"]` loop=True. **Xpath action PHẢI thêm `@class="android.widget.Button"`** (audit P2 17/08): text "Không quan tâm" có thể xuất hiện ở context menu khác (menu video "Not interested") → nếu chỉ match text sẽ tap nhầm; nút popup thật là Button (XML máy 33: bounds `[36,1649][426,1757]`, resource-id `cv6`). ⚠️ KHÔNG dùng `following-sibling` để nối "Follow bạn" với "Không quan tâm" — XML thật cho thấy 2 text nằm ở **2 nhánh cây khác nhau** (node[0] vs node[1]) nên sibling xpath không match. Verify xpath bằng `_gem_blind_find(xml_artifact_thật, xpath)` trước khi chạy máy. **Vì sao không bấm "Follow lại"**: follow phải đi qua script follow hook (có budget/order/verify riêng), bấm follow ngoài script = follow không kiểm soát, làm sai budget + có thể follow nhầm nick (user: "k đc bấm follow lại"). Quy tắc chung: mọi popup mời follow/tương tác kèm nút tác vụ → chỉ dismiss ("Không quan tâm"/"Đóng"/"Để sau"), KHÔNG bao giờ thực hiện hành động tác vụ của popup (follow/mua/cho phép) — hành động thật chỉ chạy qua script. Bảng kết quả row-5 + commit trail + cron trạng thái cuối: `references/2026-08-17-row5-canary-popup-policy.md`.
- ⚠️ **Patch tool vs CRLF: khi sửa tuple dài (GEMPHONEFARM_BLIND_POPUP_RULES) bằng patch tool dễ match nhầm block lân cận (fuzzy) → nát cấu trúc (lồng rule sai, mất `)`)** — thấy `SyntaxError: '(' was never closed` sau patch thì đừng patch tiếp: dùng python script line-based viết lại CẢ block từ anchor `GEMPHONEFARM_BLIND_POPUP_RULES = (` tới dòng `)` ở cột 0, giữ EOL từng dòng (split `\n`, join `\n`), rồi `py_compile` + import thật verify đủ N rules (regex `GemPhoneFarmBlindPopupRule\(\s*"([a-z_0-9]+)"` chính xác hơn grep).
- **Máy 19 `OPEN_TIKTOK_FAILED` dù feed thật OK (17/08 tối) — ATX stub chết, KHÔNG phải lỗi follow/máy**: follow hook báo "TikTok không load feed sau retry" nhưng screencap cho thấy TikTok ĐANG Ở FEED For You (video phát bình thường). Root cause: `capture_atx_session_ui` fail `ATX_SESSION_STUB_NOT_RUNNING` (stub `com.github.uiautomator` không chạy) → rơi xuống shell uiautomator → `could not get idle state` (video animation) → flow tưởng chưa vào feed. Dumpsys vẫn báo SplashActivity cũ (stale). **Quy tắc chẩn đoán: screencap = ground truth; dumpsys/ATX dump fail ≠ máy kẹt.** Fix + lệnh restart stub: skill `atx-agent-primary-ui-xml` mục `ATX_SESSION_STUB_NOT_RUNNING` (dùng `monkey -p com.github.uiautomator 1`, KHÔNG `am startservice`).
- **`launch_evidence` UnboundLocalError khi MỌI máy config-error (17/08)**: sau khi thêm skip row-trống (username rỗng → config-error), batch toàn máy rỗng → `execute_multi_machine_feed_session` không bao giờ gán `launch_evidence` (chỉ khởi tạo trong `if accounts:`) → crash ở `_aggregate_rows(machine_launch=...)`. Fix: khởi tạo `launch_evidence: dict | None = None` TRƯỚC `if accounts:`. Bài học: biến dùng ở cuối hàm phải có default ở đầu hàm bất kể nhánh nào đi qua.

**Pitfall commit mất file (17/08, lặp lại 2 lần)**: `git add` 4 file → `git commit` chỉ bắt 2 file (2 file còn lại mất khi interrupt/rewrite giữa chừng — config.py/run_follow.py patch không được ghi). Bắt buộc TRƯỚC commit: `git diff --cached --stat` đối chiếu ĐỦ file; SAU commit `grep` field mới trong working tree + `git show HEAD:file | grep` — thiếu = patch chưa lên đĩa, phải patch lại + commit thêm (đừng để engine đọc `self.cfg.skip_identity_verify` mà config thiếu field → AttributeError).

## Live spawn qua cron runner (17/08 — wire xong, canary row 5: 2 success / 3 manual-needed / 1 fail)

- **Adapter production `self.enabled=False` LÀ CỐ Ý** (3 test bắt buộc `enabled is False` kể cả `enabled=True` — fail-safe offline harness). KHÔNG sửa adapter. Live = wrapper runner tự spawn `run-feed-session.ps1` TRỰC TIẾP: gom due entries theo row → 1 lần `-Row R -Machines <list> -Run` (pattern canary đã chứng minh), `Popen` detached + lease file (`state_root/runner-live-lease/<day>.json`: pid, rows, expires 4h) chống double-spawn giữa tick.
- **BẪY env child cho PowerShell 5.1**: child env tối thiểu (allowlist hẹp) → `Internal Windows PowerShell error 8009001D` (managed CLR không load). Fix: forward GẦN ĐỦ env (trừ forbidden: SECRET/TOKEN/PASSWORD/CREDENTIAL/API_KEY/AGENT/HERMES_WORKDIR/HERMES_LIVE_PERMIT_FILE/KEY), PATH vẫn sanitized. **BẪY key case**: MSYS env có `PSMODULEPATH` (UPPERCASE) — PowerShell cần `PSModulePath` (PascalCase); forward qua generic loop là đủ.
- **BẪY `\v` escape**: path `WindowsPowerShell\v1.0` viết trong string thường → Python biến `\v` thành vertical tab 0x0B → path sai. Dùng raw string + verify `cat -A`.
- **BẪY repo_root() khi deploy**: wrapper chạy từ `~/hermes/scripts/` (không có .git ancestor) → repo_root() walk sai → permit/env.json không thấy → silent exit 0 mãi (cron vô dụng, test không lộ vì chạy từ repo copy). Fix: ưu tiên `HERMES_CRON_REPO` env → probe path cố định (`"D:/Taadaa/tiktok-luot nuoi acc"`, `"D:/Taadaa/tiktok-follow"`, `"D:/Taadaa/automation-core"`) → `os.getcwd()` → mới walk __file__.
- **🔴 ROOT CAUSE LỚN NHẤT (18/08 sáng — cron tưởng chạy nhưng không làm gì)**: Hermes cron `no_agent` script KHÔNG chạy với `workdir` của job — `scheduler._run_job_script` (hermes venv `cron/scheduler.py` ~2106) spawn script với **`cwd=str(path.parent)` = `HERMES_HOME/scripts`** (thư mục đặt script), workdir job CHỈ dùng cho agent-job. → wrapper chạy từ hermes/scripts → repo_root() fallback sai → permit không thấy → **silent exit 0, cron ghi `last_status: ok` "empty stdout — silent run" NHƯNG MANIFEST KHÔNG ĐƯỢC TẠO**. Chẩn đoán: `cronjob run` thủ công cũng silent; `cron/output/<id>/*.md` ghi `Status: silent (empty output)`; nhưng chạy tay wrapper từ repo → tạo manifest. **Quy tắc: `last_status: ok` của no_agent cron ≠ script đã làm việc — phải verify ARTIFACT thật (manifest/source config mới) chứ không tin status.** Reproduce cron đúng: chạy deployed wrapper bằng hermes python (`~/hermes/hermes-agent/venv/Scripts/python.exe`) với cwd = hermes/scripts, KHÔNG env đặc biệt.
- **🔴 BẪY escape path Windows trong Python source (18/08 — 3 lần cùng sai)**: (1) raw string `r"D:\\Taadaa\\tiktok-luot nuoi acc"` trong source giữ NGUYÊN 2 backslash → path `D:\\Taadaa` không tồn tại; (2) string thường `"D:\Taadaa\automation-core"` → `\a` bị Python interpret thành bell char 0x07 (`D:\Taadaa\x07utomation-core`) + `\t` thành tab; (3) `\v` trong `WindowsPowerShell\v1.0` thành vertical tab. **Fix chuẩn: dùng FORWARD SLASH `"D:/Taadaa/..."` (Windows chấp nhận, không escape gì cả)** — verify bằng `ast.literal_eval` + `Path(r).exists()` trước khi deploy, đừng tin `grep`/repr. Khi patch qua script generator: viết chuỗi chứa `\\` trong source = generator phải tạo literal `\\` (write `\\\\` trong heredoc python) — dễ sai, forward slash loại bỏ hẳn vấn đề.
- Child env thiếu `PYTHONPATH=repo` → `ModuleNotFoundError: python_runner`; thiếu `PYTHONTZPATH=D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo` → `ZoneInfoNotFoundError Asia/Ho_Chi_Minh`.
- Chi tiết session (cron cwd root cause + escape path + audit P2 recipe): `references/2026-08-18-cron-cwd-silent-nop-and-path-escape.md`.
- **verify_artifacts KHÔNG dùng được cho multi-machine**: nó đòi `root/<1 run dir>/summary.txt`, nhưng run-feed-session multi-machine tạo `root/machines/machine_N/<ts>/summary.txt` → sync verify luôn FAILED sai. Verify bằng summary.txt từng máy (final_status: success/manual-needed/fail).
- Wrapper test chạy được chỉ khi permit files VẮNG MẶT (`test_wrapper_default_off*`) — tạm mv permits/ ra ngoài → test → mv lại.
- Cron job staged có `repeat: once` → resume xong PHẢI update `repeat=0` mới forever. Job có thể biến mất khi interrupt — luôn list lại trước khi claim.

## Live-wire hoàn tất — activation qua permit file (17/08 tối, commits 5e35ee9 + tiếp)

**Phát hiện then chốt: Hermes cron tool KHÔNG có field env** — job tạo bằng `cronjob` không thể set `HERMES_CRON_*` → wrapper default-off (cần `HERMES_CRON_*_ENABLED=1`) sẽ LUÔN inactive khi chạy qua cron thật. Giải pháp không đụng Hermes core:

- **Activation = repo-anchored permit file**: `runtime/hermes-cron/permits/<kind>.permit` (regular, non-symlink). `is_activated(env)` fallback: `env HERMES_CRON_*_ENABLED=1` → `HERMES_CRON_PERMIT_FILE` env → `_default_permit_file()` = `repo_root()/runtime/hermes-cron/permits/<wrapper-stem>.permit`. Có file = bật; không có = im lặng exit 0 (fail-closed). Test cũ `test_wrapper_default_off*` vẫn pass vì file chưa tồn tại.
- **Config = `runtime/hermes-cron/env.json`**: wrapper gọi `merged_env(os.environ)` (process env THẮNG, file chỉ setdefault) — chứa `HERMES_CRON_STATE_ROOT/SOURCE_CONFIG/OFFLINE_ROOT/OWNER_ID/WORKER_ID/FEED_STATE_JSON/POST_STATE_JSON/REPORT_JSONL/REPO/FEED_WORKBOOK`. Thiếu file + thiếu env → exit 3 (fail-closed). File CHỈ do operator tạo lúc approve; KHÔNG để sót trong repo khi chạy test (wrapper test sẽ thấy file → spawn child → fail).
- **Runner execute gate**: `hermes_cron_runner.py` giờ chấp nhận `--execute/--repo/--feed-workbook` CHỈ khi `runtime/hermes-cron/permits/tiktok_runner.permit` tồn tại; offline vẫn `parser.error`. `ProductionFeedLauncherAdapter` enabled = live. Wrapper runner forward thêm `HERMES_CRON_REPO`/`HERMES_CRON_FEED_WORKBOOK`.
- **BẪY MSYS→Windows path trong wrapper (bug thật gặp khi E2E)**: `TARGET_PYTHON_DEFAULT = "/d/Taadaa/..."` (MSYS) → `subprocess.run` qua Windows `CreateProcess` fail `FileNotFoundError: [WinError 2]`. Test wrapper dùng fake python path Windows nên KHÔNG lộ. Fix: `target_python()` convert `/d/...` → `D:\...`. **BẪY phụ**: sửa bằng patch tool dễ để `return value` thụt vào trong `if` → hàm trả `None` → `subprocess list2cmdline` ném `TypeError: expected str... not NoneType` (triệu chứng `os.fsdecode(None)` trong `<frozen os>`). Chẩn đoán nhanh: in `child_argv[0]` trước spawn — None = hàm thiếu return ở mức function. Luôn `py_compile` sau patch và chạy wrapper E2E với permit+env.json thật (không chỉ pytest).
- **MaxWorkers = 30** (user chốt 17/08: "đã đc chứng minh 30 vẫn ổn"): `run-feed-session.ps1` `[int]$MaxWorkers = 40` → `30`. Verify bằng `[System.Management.Automation.Language.Parser]::ParseFile` (không chạy).
- **Bật checklist (khi user duyệt resume)**: (1) generate `hermes_cron_source_config.json` bằng `scripts/generate_cron_source_config.py` (input: safe projection + assignment manifest + journal facts — assignment thật = `%LOCALAPPDATA%\automation-core\assignments\tiktok-feed.json`, 74 máy); (2) tạo `env.json` + 3 permit files; (3) resume 3 job. ⚠️ **Xung đột data đang mở (17/08)**: generator yêu cầu slot liên tục 1..N nhưng 8 máy (22, 33, 34, 39, 40, 53, 61, 66) có acc ở hàng 1,2,4 (hàng 3 trống) do nguồn `taikhoan_dat_v2` — chờ user chốt A (nén acc về đầu = đổi row mapping) vs B (giữ row vật lý, sửa generator cho phép slot gián đoạn); mình nghiêng B (không đụng data cũ).
- Chi tiết recipe + evidence: `references/2026-08-17-live-wire-activation-permit.md`.

### Giải thích dễ hiểu cho user (correction lặp lại 17/08 — "Giải thích dễ hiểu đi", "15ph có ng giám sát là cc gì v")

User 2 lần yêu cầu giải thích đơn giản khi mình báo cáo kỹ thuật dày đặc. Pattern hiệu quả: **ví von bằng đồ vật quen thuộc, liệt kê vai trò từng thành phần như con người, không jargon**:

- Picker 6h sáng = "người xếp lịch" (ngày 1 lần: hôm nay máy nào chạy acc nào, ghi vào giấy/manifest).
- Runner 15' = "người gác cửa bấm giờ" (gọi từng máy chạy đúng slot, tránh 73 máy chạy cùng lúc kẹt mạng).
- Watcher 15' = "người canh lỗi" (chỉ báo khi máy treo cả tiếng, im lặng khi ổn).
- Cron không cần key AI = "giống Windows Task Scheduler cũ" (script-only, 0 token).
- Permit file = "tờ giấy phép trong ngăn kéo" (có giấy = máy bán hàng tự động chạy).
- 3 bước bật = "tạo danh sách máy, đặt giấy phép vào ngăn kéo, mở khóa hẹn giờ".
- Khi user hỏi "đang sửa cái gì giải thích dễ hiểu ra" → tóm 3-5 dòng plain-language trước, chi tiết kỹ thuật để sau nếu cần.

## Phases
- **P1** Core Harness: picker + manifest schema + tests. KHÔNG đụng automation-core / consumer scripts / workbook. feed_then_post chỉ là contract (adapter thật ở P4).
- **P2** Chuẩn hóa source mapping. **P3** cadence/video quota. **P4** adapter feed→upload + migrate từng consumer tuần tự (feed nuôi → upload → reg tiktok → reg mail → login/2FA), mỗi cái verify xong mới chuyển cái kế.
- **P5** Watchdog ngoài Hermes: heartbeat (cron 10' ghi file) + tray kiểm tra stale → Telegram qua bot API (curl) + restart Hermes. Hermes chết thì cron chết → bắt buộc người gác ngoài; giữ ĐÚNG 1 Windows task "At logon" (tray: proxy watcher + watchdog).
- **P6** Cutover: xóa các Windows tasks theo giờ, chạy song song 1-2 ngày rồi mới tắt hẳn.

## Quy trình (theo AGENTS.md D:\Taadaa)
Task COMPLEX → plan bằng subagent (read-only) → audit 1 model xuyên suốt (Sol qua `codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol`, stdin pipe, prompt >30KB không qua argv) → worker build (leaf) → coordinator verify diff + tests. Coordinator read-only; mọi write qua worker.

**Bậc thang effort (user rule, xác nhận nhiều lần 17/08 — KHÔNG tự động plan/audit mọi thứ)**: user hỏi "có phức tạp để gọi plan vs audit k, k thì tự làm" → rule là: việc đơn giản/đã hiểu rõ → **tự làm trực tiếp** (patch + test + commit, không plan, không audit); việc phức tạp/rủi ro/mới → plan + audit. Đừng mặc định kéo theo ceremony nặng cho fix nhỏ; cũng đừng tự ý bỏ qua khi scope lớn (như patch all-repo VPN). Khi user hỏi "có cần plan không" — đánh giá nhanh rồi trả lời thẳng, không hỏi lại.

## Nguồn đọc tham chiếu
- D:\Taadaa\automation-core\src\automation_core\scheduler\{base.py, time_windows.py, tray.py} + device_lock.py
- D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1 (param: -Row 1..6, -Preset full, -Machines, -RandomizeMachineOrder, -Run, -RecoveryTestSwipes)
- D:\Taadaa\Tiktok-video\run_tiktok_upload_batch.ps1 + scripts/random_batch_render.py
- Ledger: D:\Taadaa\tiktok-luot nuoi acc\python_runner\runs\scheduler.jsonl, D:\CodexRuntime\tiktok-video\recovery\handoff-ledger.jsonl
- Machine config: D:\CodexRuntime\tiktok-video\config-machine-<N>.yaml
