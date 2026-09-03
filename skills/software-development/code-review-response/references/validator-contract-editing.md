# Validator & Contract Editing (automation-core ui-compatibility)

Session detail for fixing Sol-audit findings — round 1: P1-08 / P2-02; round 2: P1-09 / P1-10 /
P1-11 (2026-08-09). Reusable whenever
extending `tools/check_ui_compatibility.py`, editing `docs/ui-compatibility-contract.md`,
or touching any consumer `docs/ui-compatibility.md` registry in the D:\Taadaa workspace.

## Workspace facts

- Repo layout: `D:\Taadaa\automation-core` (canonical contract + validator + tests) and
  sibling consumer repos (`add mail khoi phuc`, `gan-proxy`, `Hotmail`, `register gmail`,
  `Tiktok_Reg`, `tiktok-add-bao-mat-f2a`, `tiktok-log-in`, `tiktok-luot nuoi acc`,
  `Tiktok-video`). `Tiktok-video` uses `docs/tiktok-ui-compatibility.md`; all others use
  `docs/ui-compatibility.md`.
- ALL edited files are CRLF, no BOM. Verify after every write:
  `b.count(b'\r\n')`, `b.count(b'\n') - b.count(b'\r\n')`, BOM check.
- `git status --short` may show pre-existing dirty files (`src/automation_core/device_lock.py`,
  `tests/test_device_lock.py`) — do not touch them; report as pre-existing.

## Contract record structure (ui-compatibility-contract.md)

- Records are `### <title>` blocks; each carries 9 concepts: id_owner, ui_signature,
  evidence, fallback_order, safety_bounds, verification, regression_tests,
  preserved_branches, affected_consumers.
- Records with stable ID starting `ui-` (e.g. `ui-open-tiktok-auto-ladder-per-signature-20260809`)
  are "shared UI records"; the validator checks the NEWEST one (max 8-digit date in ID)
  for all 9 concepts.
- P1-08 carve-out pattern (already applied): the coordinate-fallback record now has a
  "Read-only visual verification vs. coordinate actions" bullet — read-only visual =
  screenshot + visual gate + foreground proof, NO side effects, allowed any time, only
  reduces ladder rounds, never skips fail-closed; coordinate action (tap/swipe/key with
  side effects) only after ladder exhausted. "Existing branches preserved" got a
  "Carve-out scope" continuation bullet stating the carve-out does NOT loosen the old rule.

## Validator design (tools/check_ui_compatibility.py)

- `REQUIRED_CONCEPTS`: 9-concept marker dict, VN template labels + EN labels.
- `RECORD_CONCEPTS` (round 2): `tuple(REQUIRED_CONCEPTS)` — all 9 concepts for NEW
  records (>= 2026-08-09 cutoff, strict bullet rule). `_LEGACY_RECORD_CONCEPTS` keeps the
  old 7 (id_owner, ui_signature, fallback_order, safety_bounds, verification,
  regression_tests, affected_consumers) for pre-cutoff records so old registries only
  warn (non-retroactive).
- Markdown parsing rules:
  - Strip fenced code blocks (`r"```.*?```"`, re.S) BEFORE splitting headings — a template
    inside a ``` fence would otherwise be parsed as a record heading.
  - Split records at `^#{2,3}\s+` headings (level-1 title `#` and `####`+ are not records).
  - Skip template headings whose text contains "mẫu".
  - Record discriminator `_has_concept_label_bullet`: block counts as a record only if a
    bullet opens with a known concept label (`- ID/owner:`, `- Signature UI:`,
    `- Giới hạn an toàn:`...). Structural sections ("## Quy tắc thay đổi",
    "## Checklist review", "## Các contract đang được bảo vệ") mention concepts only in
    prose → skipped. A real record with no bullets at all → skipped (not flagged).
  - Round 1: concept presence = marker anywhere in block (casefolded); bullet-start
    match only used for the record discriminator. ROUND 2 (P1-10): for NEW records,
    concept presence requires a DEDICATED bullet label (`- **Label:** value` /
    `- Label: value`) with a NON-EMPTY value via `_concept_bullet_values()`; prose never
    counts, and a combined bullet like `- UI signature and evidence:` satisfies ONLY
    ui_signature (evidence needs its own bullet). Old records keep the round-1
    marker-anywhere path (`_missing_concepts`).
- Marker variants observed in the wild (all legitimately map to a concept — extend the
  dict with these, not with loose words):
  - fallback_order: `selector/fallback`, `thứ tự xử lý`, `ordered handler`,
    `ordered semantic` (transition), `ordered selector`, `thứ tự recovery`,
    `thứ tự capture`, `recovery order`, `thứ tự handler`.
  - verification: `post-action verification`, `xác minh sau thao tác`, `postcondition`.
  - regression_tests: `regression tests`, `regression test`, `regression coverage`.
  - affected_consumers: `consumer bị ảnh hưởng`, `core version/consumer bị ảnh hưởng`,
    `affected consumers`, `core version/consumer`, `core impact`.
  - preserved_branches: `nhánh cũ phải giữ`, `không được làm`,
    `existing branches preserved`, `existing branches must remain intact`.
  - DO NOT add: bare `action`, bare `ordered`, bare `regression`, bare `evidence` — too
    loose, they mask genuine gaps.
- Real-workspace result: core contract 0 findings (newest ui- record complete); consumer
  per-record LEGACY WARNINGS = 66 (tiktok-luot nuoi acc 29, Tiktok-video 28, Tiktok_Reg 7,
  tiktok-log-in 1, Hotmail 1) — warnings, NOT findings: validator exits 0 with
  `OK: 9/9 consumers`. Round 2 kept this exact baseline (9/9, 0 findings, 66 warnings)
  while making new records strict. Registry fixes remain a separate task.

## Pitfalls hit this session

1. `str.replace` with `\n` against CRLF file → count==0 → assert trips. Use `\r\n`
   everywhere in search/replace strings, or line-splice.
2. Silent vacuous pass: `_core_record_findings` used `core_repo / CANONICAL_NAME`,
   missing the `docs/` segment → `is_file()` False → returned `[]` forever, so the real
   run "passed" the new check without ever reading the contract. Proof-of-life probe:
   call the internal function directly and print parsed `(id, heading)` tuples.
3. Line-splice overwrote `lines[i+2]` that held "and target (scaled by wm size), then" —
   content dropped until re-reading the git diff. Always review the final diff.
4. write_file → LF → must convert to CRLF (idempotent recipe above).

## Test pattern (tests/test_check_ui_compatibility.py)

- Build tmp workspaces with: template section (`## Mẫu contract`), structural section
  (prose mentioning concepts), one complete record, one incomplete record (only
  ID/owner + Safety bounds), one EN-style complete record → assert exactly ONE
  `registry_record_incomplete` finding naming the incomplete record and its exact
  `missing=` list.
- Core contract tests: write `automation-core/docs/ui-compatibility-contract.md` with an
  old `ui-` record (complete) + newest `ui-` record missing one concept → assert
  `core_contract_record_missing_<concept>` with `id=<newest>`; and a complete newest →
  assert no `core_contract_record_missing_*` findings.
- Run: `python -m pytest tests/test_check_ui_compatibility.py -v`; validator run:
  `python tools/check_ui_compatibility.py --workspace-root "D:\Taadaa"`.

## Round 2 (2026-08-09 — Sol RE-AUDIT P1-09 / P1-10 / P1-11)

- **P1-09 — rule 4 contradiction:** contract rule 4 rewritten as two sub-bullets with no
  textual overlap: (a) READ-ONLY OBSERVATION (screenshot/visual + visual-gate + foreground
  check, NO side effects, not a fallback action, allowed before ladder exhaustion, may only
  reorder ladder, never bypasses fail-closed, still needs foreground proof + immutable
  screenshot + regular verifier) vs (b) SIDE-EFFECTING FALLBACK (taps/swipes/keys ONLY
  after ladder exhaustion, evidence-backed, recapture, fail-closed). The ui-open record's
  Post-action verification bullet now states the `_wait_for_feed` visual-gate accept is a
  read-only observation (4a), coordinate taps stay 4b. Only rule 4 carried the offending
  "coordinate **or visual gates**" phrase; other records' "no coordinate fallback" lines
  were left untouched.
- **P1-10 — strict bullet-label presence:** `_BULLET_CONCEPT_RE =
  r"^-\s+(?:\*\*)?(?P<label>[^:]+?)(?:\*\*)?\s*:\s*(?P<value>.*)$"`; label matched by
  prefix of `marker.rstrip(":")`; value stripped of a trailing `**` before the emptiness
  check. `_missing_bullet_concepts(block, RECORD_CONCEPTS)` drives the NEW-record path;
  `_is_new_record` chooses fail vs warn. Finding key stays `registry_record_incomplete`,
  warning key stays `registry_record_incomplete_legacy` — do NOT rename these (tests and
  ops grep them).
- **P1-11 — fail-closed + date parsing:** (a) missing canonical contract →
  `return [f"core_missing:{contract}"]`, never `[]`; (b) `_heading_date` parses both
  `YYYY-MM-DD` and `YYYYMMDD` from headings and normalizes compact → ISO before `>=`
  cutoff (`"20260808" >= "2026-08-09"` is lexicographically True — a real bug); (c)
  records with no resolvable date/ID stay legacy (non-retroactive; Sol wanted
  fail-closed, user rule kept legacy — documented in `_is_new_record` docstring).
- **Tests added:** `test_core_contract_missing_is_finding` (unlink contract →
  `core_missing:` finding); `test_new_record_prose_does_not_count_as_evidence_bullet`
  (evidence present only inside the ui_signature bullet label → `missing=evidence`);
  `test_new_record_empty_bullet_value_is_missing` (`- Evidence:` empty → missing).
  COMPLETE_RECORD / ENGLISH_RECORD fixtures gained dedicated evidence + preserved-branches
  bullets; the expected `missing=` string grew to the 9-concept order
  (`ui_signature,evidence,fallback_order,verification,regression_tests,preserved_branches,affected_consumers`).
- **End gate (round 2):** pytest 10/10; real validator `OK: 9/9 consumers`, exit 0,
  `total legacy warnings: 66` unchanged (captured BEFORE editing, diffed after); EOL
  byte-pure after edits (contract 450 / validator 365 / tests 335 CRLF, 0 lone LF/CR);
  no commit/push; `device_lock.py` + `test_device_lock.py` left as pre-existing dirty.
- **Why 0 new FAILs on real data:** no consumer registry contains a record >= 2026-08-09;
  the only post-cutoff record (`ui-open-tiktok-auto-ladder-per-signature-20260809`) lives
  in the core contract, which is checked by the marker-based `_core_record_findings`, not
  the strict per-record path.

## Round 3 (2026-08-09 — Sol REJECT V3-6: one shared strict parser + fail-closed new)

- **Shared parser refactor:** round-2's `_BULLET_CONCEPT_RE` + `value.endswith("**")` hack
  REPLACED by `_BULLET_LABEL_RE = r"^(?P<label>\*{0,2}[^*:\n]+?\*{0,2})\s*:\s*(?P<value>.*)$"`
  + `_strip_decoration()` + `_record_bullet_values()` (label→value dict) feeding
  `_concept_bullet_values()` (concept→value). ONE parser drives BOTH `_core_record_findings`
  (9 concepts) and `_registry_record_findings` (7 legacy). Core check no longer
  substring-matches markers in the whole block.
- **`_strip_decoration`** removes surrounding `**`/`*`/backticks/`[text](url)` from label AND
  value BEFORE the emptiness decision: `- **Evidence:**` and `- Evidence: **` both collapse
  to empty → missing. (The old regex left value `"**"` — startswith AND endswith `**` made
  the `endswith`-only hack skip it → counted present; that was the "upgrade regex bug".)
- **Wrapped values:** label line ends `:` with an empty value → following non-bullet,
  non-blank, non-heading lines join as the value (markdown wrapping). A genuinely empty
  bullet followed by ANOTHER bullet stays empty (fail-closed).
- **`_record_owner_id` V3-6d:** matches `- **Owner:**` / `- Owner:` / `- ID/owner:`, ID
  backtick optional; MUST `value.lstrip("`")` before `re.split(r"[\s`]+", ...)` — a
  backtick-led value yields an empty first token otherwise.
- **`_is_new_record` V3-6e/f — REVERSES round-2 P1-11(c) "ambiguous → legacy":** heading
  date ≥ cutoff → new; else owner-ID date ≥ cutoff (both `YYYY-MM-DD` and `YYYYMMDD`) →
  new; else if ANY date parsed but all < cutoff → legacy (old dates also contain 20xx —
  do NOT fail-closed those); else a `20\d{2}` sign in heading/ID that won't parse to a full
  date → NEW (fail-closed); only records with NO date sign at all stay legacy.
- **`fallback_order` markers += `thứ tự selector/fallback`** (combined label used by ~100
  legacy records across add-mail/Hotmail/gan-proxy/register-gmail/tiktok-log-in/...).
- **The 66 → 173 warning spike:** switching the legacy path from substring to strict bullets
  flagged every record whose label variant wasn't in the marker list. Diagnostic: dump
  DISTINCT bullet labels across all 9 registries via `_BULLET_LABEL_RE` — the spike was ONE
  label. After adding the marker: exact baseline parity (66 records, 0 newly-warned,
  0 dropped; 6 records show +1 missing concept — real strictness, still warnings only).
- **Baseline-parity acceptance:** re-implement the OLD (substring) legacy detector in a
  scratch script and compare per-record warning SETS, not counts. Report: same record set,
  0 newly-warned, 0 dropped, N missing-set diffs each explainable. This is how "66 warnings
  unchanged" is actually proven after a semantics change.
- **Core contract doc edit:** the newest ui- record needed a DEDICATED `- Evidence:` bullet
  (`- Evidence: consumer registry Tiktok-video COMPAT-OPEN-TIKTOK-002 / COMPAT-CAPTION-004
  redacted runs...`) because merged "UI signature and redacted evidence" satisfies ONLY
  ui_signature. Also split the doc's "Required compatibility record" line into signature +
  evidence bullets with a strict-parser note. Consumer registries were NOT touched.
- **Tests (round 3):** `NEW_UI_RECORD_COMPLETE` and `OLD_UI_RECORD` gained dedicated
  Evidence bullets (they're the "complete" fixtures — merged-only would fail strict);
  new fixtures: `NEW_UI_RECORD_MERGED_BULLET` (merged → `core_contract_record_missing_evidence`),
  `BOLD_LABEL_EMPTY_EVIDENCE_RECORD` (`- **Evidence:**` → missing), `STAR_ONLY_EVIDENCE_VALUE_RECORD`
  (`- Evidence: **` → missing), `ID_ISO_DATED_INCOMPLETE/COMPLETE_RECORD` (YYYY-MM-DD in ID,
  no heading date → NEW; incomplete FAILs, complete passes), `AMBIGUOUS_NEW_YEAR_RECORD`
  (year-only `2026` in heading → fail-closed NEW). Finding text carries the HEADING, not the
  ID — assert on heading text. End gate: 14/14 passed.
- **Pitfall (this round):** a bash `<<'PY'` heredoc whose replacement text contained `"\\n"`
  produced a REAL newline inside the generated test file's string literal
  (`OLD_UI_RECORD + "` + LF + `" + NEW_UI_RECORD_MERGED_BULLET` → unterminated string,
  caught only by pytest collection). The final merged-bullet core test was left UNFINISHED
  (fixture defined, test not yet inserted — insert `test_core_contract_fails_when_newest_ui_record_merges_concepts_in_one_bullet`
  after `test_core_contract_passes_when_newest_ui_record_complete`, expect 15 passed).
- **End gate (round 3):** pytest 14/14 (15 pending); real validator `OK: 9/9 consumers`,
  exit 0, `total legacy warnings: 66` = EXACT round-2 baseline via per-record set parity;
  CRLF byte-pure on validator/tests/docs; no commit/push; `device_lock.py` + tests left
  as pre-existing dirty.

## Round 4 (2026-08-09 — Sol REJECT V4-05 / V4-06 / V4-08): decoration strip + MAX-date + A/B attribution

- **V4-05 — `**Label:**` markdown decoration gotcha (record discriminator).** The closing
  `**` of `- **ID/owner:**` sits AFTER the colon (bold wraps `**ID/owner:**` including the
  colon), so `_BULLET_LABEL_RE` on `"**id/owner:** x"` yields label `'**id/owner'` + value
  `'** x'` — trailing stars land in the value, the label keeps LEADING stars, and wrapper-only
  `_strip_decoration` cannot strip them (no closing match). Fix in the block discriminator:
  strip leading decoration in a loop BEFORE the prefix match
  (`while bullet_body.startswith(("**","*","`")): bullet_body = bullet_body[2:] if
  bullet_body.startswith("**") else bullet_body[1:]`) so `- **ID/owner:**` matches `id/owner` —
  a record whose labels are all bold is CHECKED, never silently skipped (the audit's complaint).
  Real world: ZERO bold-label bullets across all 9 registries + core contract → byte-neutral on
  the validator; the fix + tests are pure robustness. Debugging key: print regex group SPANS
  (`mo.span("label")`, `mo.span("value")`) + per-index chars — my mental model of where the
  colon sits was wrong twice; the span dump settled it in one shot.
- **V4-06a/b — MAX of ALL dates, not earliest-found.** `_is_new_record` rewritten: newest =
  `_record_latest_date(heading, owner_id)` (helper: per-identifier `_record_date` then outer
  max; '' if none) — BOTH new-ID + old-heading AND new-heading + dateless-ID are NEW; only when
  EVERY parsed date < cutoff is legacy; `20xx`-ambiguous stays fail-closed NEW. `_core_record_findings`
  newest key likewise becomes `max(ui_records, key=lambda item: _record_latest_date(item[0],
  item[1]))` (ID date + HEADING date) — a record with a NEW heading date but dateless `ui-` ID
  must win "newest" (old code keyed only on ID date). NOTE: the reviewer's literal repro ("line
  `if hd or id_date: return False` hạ legacy sai") was unreachable — the ID-date `>= cutoff`
  early-return fired first — but implement the max-of-all rewrite anyway: correct defensive
  structure, satisfies the audit, and the requested tests lock the invariant.
- **Contract doc vs. the REAL implementation.** Before rewriting a text spec (caption verifier:
  "full caption or >= 60% typed-character overlap" → Structured `_caption_typing_ratio_ok`),
  grep the consumer code first and mirror its constants exactly: NFC-normalized text with
  hashtag coverage >= 70% AND SequenceMatcher ratio >= 60% (caption < 20 chars: edit distance
  <= 25%), each typed chunk verified by cumulative-prefix `startswith`. Docs that drift from
  code are the next audit finding.
- **Attribution A/B proof — "did MY change cause this finding?"** When the real validator
  shows a finding absent from the parent's baseline, do NOT assume you broke it and do NOT
  silently claim clean: reconstruct the pre-change implementations (re-write old `_is_new_record`
  / `_has_concept_label_bullet` from the pre-edit reading), monkey-patch them onto the
  freshly-loaded module (`m._is_new_record = old_func`), and re-run
  `check_workspace(Path("D:/Taadaa"), legacy_warnings=w)` on the REAL workspace. Identical
  finding + identical warning count under OLD logic ⇒ pre-existing — usually uncommitted
  consumer WIP (the round's `Sponsored-ad feedback overlay swipe fallback (2026-08-09)` record
  was added SAME DAY, dated >= cutoff, referencing `.ai-runs/20260809-*`). Report the proof;
  never silently fix out-of-scope consumer records to force 0 findings.
- **Baseline drift within hours.** Consumer registries mutate mid-session (uncommitted records
  dated today), so the parent's "OK 9/9, 0 findings, ~67 warnings" may already be stale —
  expect ±a few warnings and possibly one NEW-record finding. The honest report = current
  validator output + the A/B attribution, not the claimed baseline.
- **End gate (round 4):** pytest 18/18 (15 old + 3 new: all-bold record → checked, not
  skipped; old heading + ID `ui-20260809` → finding not warning; core heading-dated newest
  with dateless ID → no `core_contract_record_missing_*`). Real validator: 1 finding
  (A/B-proven pre-existing, uncommitted consumer WIP) + `total legacy warnings: 66`; CRLF
  byte-pure on validator/tests/docs; no commit/push; pre-existing dirty files untouched.

## Round 5 (2026-08-09 — Sol REJECT V5-2: bold label parse ĐÚNG in the SHARED parser)

- **V5-2 — V4-05 fixed the discriminator, NOT the value parser.** `_has_concept_label_bullet`
  (record discriminator) got the leading-decoration strip in round 4, but
  `_record_bullet_values()` still fed `- **ID/owner:** ui-new-20260809` through the plain
  `_BULLET_LABEL_RE = r"^(?P<label>\*{0,2}[^*:\n]+?\*{0,2})\s*:\s*(?P<value>.*)$"` and produced
  label `'**ID/owner'` (LEADING `**` kept, TRAILING `**` lost) + value `'** ui-new-20260809'`
  (leading `**` leaks into value). Root cause: `[^*:\n]+?` refuses stars, so for
  `**ID/owner:**` it stops at `ID/owner`, `\*{0,2}` matches 0 (next char is `:`), then `\s*:`
  eats the colon and the closing `**` falls into `value`. `_strip_decoration('**ID/owner')`
  can't strip it (no closing match) → label `**id/owner` never matches marker `id/owner` →
  EVERY bold-labeled record false-missing. Prove it fast: run the regex in a scratch `python -`
  over the exact bullet and print `repr(label)`/`repr(value)` for both bold and plain forms.
- **Fix: dedicated bold pattern tried FIRST, plain as fallback.**
  `_BOLD_BULLET_LABEL_RE = r"^\*\*(?P<label>[^*:\n]+?):\*\*\s*(?P<value>.*)$"` matches
  `**id/owner:**` correctly (`**`open + label + `:` + `**`close, colon INSIDE the bold pair).
  In `_record_bullet_values`: `if body.startswith("**"): m = _BOLD_BULLET_LABEL_RE.match(body);
  if m is None: m = _BULLET_LABEL_RE.match(body)`. Plain `- Label: value` AND colon-outside-bold
  `- **Label**: value` both still resolve via `_BULLET_LABEL_RE`. Continuation lines (wrapped
  values) and `**value**`-decorated values keep working because `_strip_decoration` runs after.
- **Tests (round 5, 22 total = 18 old + 4 new):** (1) direct `_record_bullet_values` on
  `-B-**ID/owner:** ui-new-20260809` / `- **Safety bounds:** giới hạn` / `- **Evidence:** **`
  (decoration-only value → `''`); (2) `- **Evidence:**` (empty bold value) → `evidence`
  missing; (3) all-bold 9-concept record → PASS (no false missing); (4) all-bold record
  missing evidence → finding `missing=evidence` exactly. The all-bold fixtures must use REAL
  marker labels (`- **UI signature:**`, `- **Ordered selector/fallback:**`), not invented
  labels (`- **Tai khoan:**` matches nothing → extra missing concepts).
- **Validator reality vs. parent's claim.** Parent said "keep the 1 Sponsored-ad finding
  (out of scope), 0 others"; the REAL run shows TWO findings (`Sponsored-ad feedback overlay
  swipe fallback` + `Shop CTA ad in-feed swipe-first`, both in tiktok-luot nuoi acc — prose
  records of another session) and `total legacy warnings: 66`. Baseline-before == after, 1:1
  finding set identical, no new finding → report honestly with the diff, don't chase the
  claimed "0 others" (out-of-scope records). Note `search_files` (ripgrep) threw "IO error:
  path not found" on perfectly valid `D:\Taadaa\...` paths while terminal `grep -n` worked —
  fall back to grep when search_files errors on existing Windows paths.
- **End gate (round 5):** pytest 22/22; real validator findings set byte-identical to
  baseline (2 pre-existing, out-of-scope), warnings 66; CRLF byte-pure on
  validator/tests (assert 0 bare-LF via `out.count(b'\r\n') == out.count(b'\n')`); edits via
  Python script `newline=""` read/write preserving CRLF (patch/sed banned); no commit/push;
  `device_lock.py` + `test_device_lock.py` left as pre-existing dirty.
