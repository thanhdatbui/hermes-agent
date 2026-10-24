# Per-Machine Dynamic 3-Tier Account Selection Contract

## 1. Context & Motivation
In the 4-day nurture cycle (`Day 0 = Rows 1,3,5`, `Day 1 = Rows 2,4,6`, `Day 2 = Rows 7,8,Dynamic`, `Day 3 = Rest Day 3x Dynamic`), previous implementations attempted to select a single "healing row" farm-wide. This caused severe allocation mismatch:
- Machine A's Slot 2 was trending, but the farm picked Row 4.
- Machine B's Slot 5 was jailed for follow cooldown, but the farm picked Row 3.
- Machine C had all slots healthy, wasting a rest session on an already-aged account.

**The Solution:** Discard farm-wide row locking for dynamic sessions. In dynamic windows (`row_index = 0`), each machine independently inspects all 8 slots in its workbook and resolves the optimal account using a 3-tier funnel.

---

## 2. The 3-Tier Funnel

When `resolve_dynamic_account_for_machine(machine, rows)` executes:

### Tier 1 (Priority 1) — Trending Momentum (`is_account_boosted`)
- **Condition:** Account has rapid follower/heart surge ($\ge 20$ followers or $\ge 50$ hearts) or active viral views in `tiktok_tracker.db` via `flows.account_boost.is_account_boosted()`.
- **Action:** Select slot immediately. Bypasses organic rest (`_upload_in_organic_rest = True`) to upload a fresh video and ride the 24-48h algorithm wave.
- **Guard:** 0 follow (prevents follow rollback penalties while riding viral momentum).

### Tier 2 (Priority 2) — Penalty Healing / Jailed Accounts (`_is_account_follow_cooldown`)
- **Condition:** No slot qualifies for Tier 1, but at least one slot has active `follow_failed` or cooldown in `follow_state_{machine}_row_{r}.json`.
- **Action:** Select the cooling-down slot. Conducts pure feed session (0 follow, 0 upload) to clear penalty flags and recover account trust score.

### Tier 3 (Priority 3) — Young Account Accumulation (`min(video_count)`)
- **Condition:** Machine has no trending and no jailed accounts.
- **Action:** Pick the slot with the lowest `video_count` (prioritizing accounts with $< 10$ videos) to build channel depth.

---

## 3. Invocation & Interface Contract

1. **Row Convention:**
   - `Row = 1..8`: Standard static row shift.
   - `Row = 0`: Dynamic per-machine mode.
2. **PowerShell Launcher (`run-feed-session.ps1`):**
   - Param `$Row` validated as `[ValidateRange(0, 8)]`.
   - When `$Row -eq 0`, passes `--account-row-index 0` to `run_tiktok.py`.
3. **Workbook Selection (`feed_session_workbook.py`):**
   - `select_feed_session_accounts(..., row_index=0)`: For each machine in `machines`, resolves dynamic account via `resolve_dynamic_account_for_machine(machine, rows)`.
   - Filters out blank usernames or string `"none"`.
   - Gracefully handles `video_count = None` (treated as 0/least).
4. **Telemetry & Audit:**
   - Logs `[DYNAMIC_SELECT] machine=<M> tier=<1_boosted|2_jailed|3_youngest> row=<R> user=<U>`.
   - Never fails silently: exception in detector logs warning and falls back to subsequent tier.

---

## 4. Scheduler Bridge Pitfall (`tiktok_runner.py` vs `healing_selector.py`)

- **Bẫy Nghẽn Tầng Scheduler:**
  Sau khi hoàn tất logic 3 lớp phễu (`row_index = 0`) tại `feed_session_workbook.py` và cho phép `-Row 0` trong `run-feed-session.ps1`, một cạm bẫy thường gặp là **tầng wrapper cron (`tiktok_runner.py`) vẫn chưa chuyển giao sang `row = 0`**.
- **Cơ chế cũ:**
  Trong `_SCHEDULE` của `tiktok_runner.py`:
  - Ngày 3 (cycle_day 2) Ca 3 (18:00 / 20:00): gán `{2: None}`.
  - Ngày 4 (cycle_day 3) Toàn bộ các ca: gán `{3: None}`.
  Khi gặp `target_row is None`, script cũ mặc định gọi `determine_healing_row()` từ `tools/healing_selector.py`. Hàm này tính điểm trên quy mô toàn farm và trả về 1 row số duy nhất ($1 \dots 8$), khiến runner truyền `-Row <1..8>` vào PowerShell thay vì `-Row 0`.
- **Yêu cầu kết nối đồng bộ:**
  Để kích hoạt đúng thiết kế Dynamic Per-Machine trong các ca dưỡng sinh (Ca 3 Ngày 3 và toàn bộ Ngày 4):
  `tiktok_runner.py` bắt buộc phải gán `row = 0` cho các slot `None` (hoặc cấu hình `determine_healing_row` trả về `0`), đảm bảo tham số truyền vào PS1 luôn là:
  `powershell ... -File run-feed-session.ps1 ... -Row 0` -> `--account-row-index 0`.
- **Kiểm chứng O(1):**
  Chạy thử `select_feed_session_accounts(workbook, [machine], row_index=0)`:
  - Nếu máy có nick cắn đề xuất (`is_account_boosted=True`), log phải ghi: `tier=1_boosted`.
  - Nếu không, máy có nick dính cooldown nhả follow, log ghi: `tier=2_jailed`.
  - Nếu không, log ghi: `tier=3_youngest` (chọn nick có `video_count` thấp nhất).

---

## 5. Shift-Pool Architecture for Regular Shifts (`shift_pool_selector.py`)

To achieve biological diversity on regular shift days (D0, D1, D2) while avoiding starvation, accounts are partitioned into 3 fixed pools:
- **Ca 1 (Sáng 06:00 & 08:00):** Pool `{1, 2, 7}`
- **Ca 2 (Trưa 12:00 & 14:00):** Pool `{3, 4, 8}`
- **Ca 3 (Tối 18:00 & 20:00):** Pool `{5, 6}`

### Operational Cadence (4-Day / 96h biological cycle anchored to 2026-10-11):
- **Day 0 (D0):** Ca 1 pick Row 1, Ca 2 pick Row 3, Ca 3 pick Row 5.
- **Day 1 (D1):** Ca 1 pick Row 2, Ca 2 pick Row 4, Ca 3 pick Row 6.
- **Day 2 (D2):** Ca 1 pick Row 7, Ca 2 pick Row 8. **Ca 3 tối: Pool {5, 6} hết nick -> BẮT BUỘC fallback sang 3 Phễu Dưỡng Sinh (`resolve_dynamic_account_for_machine`)**.
- **Day 3 (D3 - Rest Day):** **Toàn bộ 3 Ca là Dưỡng sinh -> BẮT BUỘC chạy 3 Phễu Dưỡng Sinh**.
- **Session 2 Sticky Rule:** Session 2 (08h, 14h, 20h) BẮT BUỘC bám đúng row mà Session 1 (06h, 12h, 18h) đã chạy trong ngày cho từng máy.

---

## 6. Critical Pipeline Traps Across the Python / PowerShell / Cron Stack

When implementing end-to-end dynamic account selection across monolithic farm repos, beware of these 5 failure modes:

1. **Python Truthiness Coercion Bug (`args.row or 1`):**
   - *Symptom:* Calling `run_tiktok.py --account-row-index 0` silently runs Row 1.
   - *Root cause:* `config["_account_row_index"] = int(args.account_row_index or 1)`. In Python, `0 or 1` evaluates to `1`.
   - *Fix:* Bắt buộc dùng `int(args.account_row_index) if args.account_row_index is not None else 1`.

2. **Bridge Argument Omission Across Stack Layers:**
   - *Symptom:* `_shift_ca` remains `None` inside `prepare_multi_machine_feed_session()`, falling back to error.
   - *Root cause:* Parameter added in core logic but omitted in CLI wrappers.
   - *Fix:* Bắt buộc kiểm tra đủ 4 mắt xích:
     `tiktok_runner.py` (`-ShiftCa $ca`) -> `run-feed-session.ps1` (`param([int]$ShiftCa)`) -> `run_tiktok.py` (`--shift-ca`) -> `config["_shift_ca"]`.

3. **Pool Cycle Desynchronization vs 4-Day Cadence:**
   - *Symptom:* Shift pool loops independently per pool length (`cycle_day // len(pool)`), causing Ca 3 (length 2) to desync from the 4-day farm rhythm and never yield to dynamic rest.
   - *Fix:* Khóa chu kỳ chuẩn theo modulo 4: `cycle_day = (today.toordinal() - _ANCHOR_ORDINAL) % 4`. Khi rơi vào Ca 3 Ngày 2 hoặc bất kỳ ca nào Ngày 3, hàm pool selector phải trả về None hoặc raise để nhường quyền cho 3 phễu dynamic.

4. **Empty / Corrupted State File Crash:**
   - *Symptom:* `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` on empty state files.
   - *Fix:* `_load_state()` phải kiểm tra `state_file.stat().st_size > 0` và bọc `try...except (OSError, json.JSONDecodeError): return {}`.

5. **Watchdog Dynamic Label & Tik Index Formatting:**
   - *Symptom:* Watchdog reports show confusing `Row 0` and cannot reconcile follow deltas.
   - *Fix:* Trong `feed_session_watchdog.py`:
     - Header: ánh xạ tên ca sang nhãn Pool (`Pool {1, 2, 7}`, `Pool {3, 4, 8}`, `Pool {5, 6}`) qua `_row_or_pool_label()`.
     - Reconciliation: khi `active_row <= 0`, tra cứu `account` thực tế trong `all_machines` để map ngược lại index `[Tik X]` cho từng máy.

6. **Python Negative Index Wrap-Around in Machine Candidate Filtering (`_get_machines_for_row(0)`):**
   - *Symptom:* When triggering dynamic nurture with `Row = 0`, machines with only 5-7 accounts are reported as `Row 0 co 0 account hop le` and skipped.
   - *Root cause:* Legacy workbook parsing uses `slot_idx = row - 1`. When `row == 0`, `slot_idx` becomes `-1`. In Python lists, `slots[-1]` indexes the last element (Row 8). Machines without an account in Row 8 fail the candidate check even though they have healthy accounts in Slots 1-7.
   - *Fix:* Bắt buộc tách nhánh riêng cho `row == 0` trong `_get_machines_for_row`:
     ```python
     if row == 0:
         valid_machines = []
         for m, slots in machine_slots.items():
             if any(val and str(val).strip() and str(val).strip().lower() != "none" for val in slots):
                 valid_machines.append(m)
         return valid_machines
     ```

7. **Full Dynamic Rollout Bridge via Cron Runner (`tiktok_runner.py`):**
   - *Requirement:* To run dynamic across all nurture shifts (both regular shift pools and rest sessions), the runner must calculate `shift_ca` by hour window:
     - 06:00 / 08:00 -> `shift_ca = 1`
     - 12:00 / 14:00 -> `shift_ca = 2`
     - 18:00 / 20:00 -> `shift_ca = 3`
   - *Invocation:* Spawn with `-Row 0` and `-ShiftCa <shift_ca>`.
   - *Preflight Guard:* Bỏ qua `_preflight_ensure_accounts` khi `row == 0` vì tài khoản được phân giải độc lập per-machine tại thời điểm chạy.
