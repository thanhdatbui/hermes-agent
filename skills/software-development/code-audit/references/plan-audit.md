# Plan Audit — Checklist & Worked Example

Read-only verdict audit of a Markdown implementation plan against acceptance criteria (invariants handoff + locked design). First worked case: audit of `2026-08-10_fleet-account-block-scheduler.md` (~866 lines) against 9 invariants in `schedule-random-audit-handoff.md` + chốt design (window 06:00–02:00, 3 blocks/máy/ngày, 2 sessions/block, pair gap 60–90, inter-block 180–300, lane A/B parity, seed per-machine-per-day, clear-cache cuối ngày, offline-only, không scheduler thứ hai). Verdict: `MINOR_FIXES` (3 MAJOR + 4 MINOR + 4 NIT).

## Probes used (all disposable, run from repo root)

- `git status --short` → revealed plan's baseline claim stale; hermes_cron module files still untracked (`?? python_runner/hermes_cron/` etc.).
- Exact pytest command from plan → `121 passed` NOT "117 passed, 3 failed".
- `python - <<'PY'` one-liners: `int(hashlib.sha256(b'2026-08-10|1|7').hexdigest()[:8], 16)` → 3155031709 (deterministic seed format OK); `random.Random(seed).sample([1,2,3],3)`, `.choice(...)` → order/gaps vary by seed (determinism claim OK).
- `rg` for invariant keywords and for under-spec markers (`\.\.\.`, "nếu cần", "có thể", "khuyến nghị", "tối thiểu", "giữ nguyên") across tests + plan.
- `read_file` of manifest.py / runner.py / source_config.py / watcher.py / journal.py to verify "ĐÃ ĐÓNG" claims (append & replay share `reduce_and_validate`; runner grace `slot <= current <= slot + 90`; CLI requires `--source-config`).

## Checklist

- [ ] Read FULL plan + ALL acceptance-criteria sources (invariants doc, locked design). Note phase headings, acceptance lines, test skeletons, commit messages, per-phase file lists.
- [ ] Build invariant→phase→named-test matrix. Unmapped invariant or prose-only coverage = finding (e.g. Inv 1 forged notification: plan reuses r11 notification test but never re-runs it in any phase verify command).
- [ ] Re-run every baseline claim verbatim (`git status`, exact pytest line). Stale numbers = MAJOR.
- [ ] Execute the plan's formulas in python. Timing math and seed/rng claims are the highest-yield targets.
- [ ] Verify existing-code claims by reading the actual functions (named test must exist + implement the invariant).
- [ ] Grep plan for `...`, "nếu cần/có thể/khuyến nghị/tối thiểu/giữ nguyên/xem Phase N" → every hit is a potential under-spec finding.
- [ ] Check cross-phase consistency of any single change (grep the mốc/constant across all phases).
- [ ] Verify acceptance-line math (`grid_slots == 77`, boundaries) against actual window semantics.
- [ ] Report: verdict dòng đầu; findings with locator (plan dòng + code file:line); MAJOR/MINOR/NIT; note probes as evidence. Do NOT edit any file.

## Findings from the worked example (shapes to reuse)

1. **MAJOR — plan's session math self-contradicts.** Locator: Phase 2 Step 2.1 test (plan dòng 221–225) + Step 2.3 `build_block_sessions` (303–310) vs locked design (dòng 22/33). Pair gap semantics = interval between S1_end and S2_start (S2_start = S1_end + gap; total 60+60+90=210' → B1 07:00–10:00, B3 ends 00:30+1). Plan code adds gap after S2 → wrong end times and a test asserting 09:00–09:30 that contradicts the plan's own feasibility table.
2. **MAJOR — stale baseline.** Plan claims "117 passed, 3 failed" (dòng 14/65/846) and builds Phase 0 RED steps around 3 named failing tests; actual suite is `121 passed` (those 3 already green) → Phase 0's "RED đã có sẵn" cannot reproduce; worker would have to invent new tests.
3. **MAJOR — golden-vector / mốc change repeated across phases.** Same fix (window mốc `01:30 → 02:30` in `test_r11_picker_rejects_requested_day_at_next_day_0600_and_crossover`) appears in Phases 1, 3, 5 — must be applied once and identically; "cập nhật reference hash" notes hide schema-change coupling (CONSTRAINTS change → assignment_id → golden vector) across phases.
4. **MINOR — invariant not actually testable by planned test.** "2 phiên liền block, không entry khác chen giữa" has no tamper test that inserts another block's entry between S1_end and S2_start; the planned "tách phiên" tamper goes through a different branch.
5. **MINOR/NIT — placeholder bodies.** `test_runner_cli_block3_dry_run_offline` and Phase 7 tests are `...` skeletons; `test_account_block_dataclass_shape` has `assert X if cond else True` (determinism silently skipped); grid assertion computes minutes-of-day, not grid fitness.

## Re-audit after a fix round (round-2 workflow — worked case: 2026-08-11, plan grew 866→956 lines)

When the task is "re-audit plan sau vòng sửa: confirm findings R1 closed, no new cross-phase contradictions, invariants + design chốt intact", do NOT re-derive R1 from scratch. Verify closure claims instead:

1. **Re-read the FULL current plan** (line numbers shift — plan rewritten/expanded). Grep for the R1 fixing markers (`MAJOR 1`, `MỐC WINDOW THỐNG NHẤT`, etc.) and locate each fixed construct at its CURRENT dòng.
2. **Re-open the invariant/handoff source** to confirm chốt-design numbers did not drift (window mốc, anchors, gap set) while the plan was being patched.
3. **For each R1 finding, run a closure probe at the new locator** — the plan's own math (`python -c` slot arithmetic; B3/gap90 must still end 00:30+1 ≤ 02:00), the exact baseline pytest command (still `121 passed`), grep that the old bad mốc (`01:30` as ngoài-window) no longer appears in new tests. Closure = the fix is present AND self-consistent, not that the R1 text was deleted.
4. **NEW ROUND-2 GATE: audit the plan's PLANNED code against its PLANNED tests** (not just code-vs-prose). Two failure shapes found in the fleet round:
   - **Planned test that cannot reach the branch it claims** (gate masking inside the PLAN): Phase 4 `test_validation_rejects_more_than_6_sessions` appends an entry with a forged `entry_id` (`entry-v1-ffff…`) — but `_validate_entry` (planned to stay, entry_id re-verified from formula) rejects it BEFORE `_validate_block_structure` ever runs, so the block-structure branch is never exercised. A planned test passing = nothing tested.
   - **Planned validation code that doesn't implement its own test's mutation**: Phase 4 `test_validation_rejects_wrong_pair_gap` mutates ONLY `block["pair_gap_minutes"]=120` (slots untouched) — the planned `_validate_block_structure` gap check recomputes gap from the slot timestamps, so 120 passes the gate and the test FAILs GREEN. Every planned `pytest.raises` needs a corresponding planned reject-branch whose failure reason is hit by the mutation, not an earlier unrelated gate.
   - Fix pattern for the plan: pair these tests with a value-level check (e.g. block's declared `pair_gap_minutes` and `entry_ids` vs recomputed values) rather than hoping the top-level validator catches it.
5. **Re-grep under-spec markers** (`...` etc.) — skeleton bodies that survived the fix round are a residual MINOR, not a blocker, IF the flow/adversarial coverage exists elsewhere in the plan (name the covering tests when downgrading).
6. **Verdict discipline**: R1 MAJORs closed + no new contradictions → `MINOR_FIXES`, never `APPROVED` while planned code contradicts planned tests or `...` skeletons remain. Report each R1 finding as a numbered closure table (finding → locator at new dòng → probe → ĐÓNG), then round-2 findings with their own locators.

## Re-audit after the MINOR_FIXES round (round-3 workflow — worked case: 2026-08-11, plan grew 956→1151 lines, verdict APPROVED)

Round 3 verifies the R2 residuals are closed and decides APPROVED vs another MINOR_FIXES round. Do NOT re-derive R1/R2 from scratch — probe each residual at its CURRENT dòng against CURRENT source code.

1. **Closure probe per R2 residual, value-level shape.** For a residual like "add value-level pair_gap_minutes + entry_ids checks":
   - The planned `_validate_block_structure` must contain the value check (declared value in the block dict vs value recomputed from slot timestamps / re-hashed from entries) — locate exact lines.
   - The planned test's mutation must touch ONLY the field that branch reads. Gate-masking closure proof: read the CURRENT `_validate_entry` in source and show it does NOT read the mutated field → the later branch is genuinely exercised by that mutation.
   - The re-hash formula inside the planned check must match the CURRENT `entry_id_for` signature (parameter ORDER matters). Match = closure; mismatch = MAJOR.
2. **`...` marker disambiguation:** grep hits for `...` inside COMMENTS of GREEN code snippets (e.g. `# journal.append(CLEAR_CACHE_REQUESTED, ...)`) are NOT test skeletons — only `...` in a test BODY (inside `def test_...`) is a residual MINOR. Classify each hit per phase with line numbers; a phase with zero body-hits has its skeleton residual closed even if several comment-hits remain.
3. **Harmless drift vs stale claim:** re-run the exact baseline pytest command. If the plan's named claims are verified by the re-run (e.g. "the 3 previously-red tests now pass" confirmed), a drift in a DIFFERENT quoted fact (HEAD hash `f707bde` vs actual `b72100a`) is a NIT, not MAJOR — Phase-0 assumptions still hold. MAJOR drift = the named baseline numbers are wrong. Re-run `git status` immediately before finalizing; the worktree can drift mid-audit (concurrent writer) — record observed drift as a risk, not an error.
4. **Under-defined helper sweep:** list every identifier planned tests call that the plan never defines (`_fleet_pick`, `seven_source`, `fleet_feed`, `FakeFeedLauncherAdapter(...)`). If the plan commits to creating those helpers in that phase's file list ("worker defines in new test file"), the gap is a NIT; if a helper is used but NO phase creates it, that is a MINOR/MAJOR gap.
5. **Verdict discipline round-3:** `APPROVED` is allowed when every R2 residual is closed (value-level checks in BOTH planned test and planned code, full test bodies, no cross-phase contradictions, invariants + design chốt intact, baseline re-verified). Do NOT hold APPROVED hostage to documented NITs the plan already assigns to worker file-creation steps (define-helper, unused import, harmless baseline drift) — list them as "residual ghi chú — không chặn". Keep `MINOR_FIXES` if any planned test still cannot reach its claimed branch or any body skeleton remains.

## Report format used (match this)

```
# MINOR_FIXES
## Bối cảnh kiểm chứng (chạy thực tế, read-only) → các probe đã chạy + kết quả thật
## <6 findings vòng 1> — mỗi finding: locator mới, probe, trạng thái ĐÓNG (kèm lý do đóng)
## Findings vòng 2 → locator (plan dòng + code file:line), sai lầm, bằng chứng (_verify probes)
## Kết luận: 1 dòng rationale cho verdict
```