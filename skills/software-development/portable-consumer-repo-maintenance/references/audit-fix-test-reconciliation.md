# Audit-Fix Test Reconciliation — stale tests → new safety contract

Verified 2026-08-09 on Tiktok-video "Follow-up A7": an audit-only round ("Sol R6 blind
re-audit") had already changed `scripts/tiktok_workflow/state_machine.py` for fail-closed
safety; the task was to reconcile the existing test suite, add regression tests per
finding, document the round (Vietnamese), run the full suite green, preserve per-file EOL,
and commit nothing.

## Phase 1 — Reproduce the exact stale set (one batch)

```bash
PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" "/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m pytest tests/test_tiktok_workflow.py -q --tb=short -k 'test_a or test_b or ...'
```

Classify each failure by symptom:
- **assert False on a value** → contract/enum/signature changed by the fix.
- **"evidence fail-closed" log / recover counter 0** → the new contract requires artifacts
  the test never supplied (fixture gap, not behavior bug).
- **AttributeError / TypeError** → helper never landed in this round's diff, or a call
  signature changed.

## Phase 2 — Read the round's findings, not the old assertions

The audit transcript (e.g. `%TEMP%\hermes-audit-sol-r6-blind-*.txt`) lists each P1-`NN`
finding with file:line, concrete bug, and the fix. Map 1:1: each stale test ↔ the finding
that changed its contract. Then read the CURRENT code at those functions — the audit may
describe intent; the diff is truth.

## Phase 3 — Update per contract (patterns seen)

| Stale test symptom | Fix pattern |
|---|---|
| New evidence required (ATX-kill now needs pre/post artifacts + save_checkpoint) | add `tmp_path` fixture; `monkeypatch.setattr(machine, "_capture_soft_reboot_artifact", lambda phase: tmp_path / f"{phase}.png")`; keep the assertion, add evidence |
| Enum semantics split (old `NOT_RESERVED` meant "fresh, may act"; fix split into `READY_TO_RESERVE` vs terminal `NOT_RESERVED`) | update the assertion to the new member; verify RED (old value) → GREEN |
| VERIFIED now requires full proof (started marker + post_reboot_verified + before/after artifact + verifier id) | direct unit test of `_soft_reboot_recovery_outcome` with/without each field → not-VERIFIED always when a field is absent |
| Verifier rejects non-caption focused EditText (search box `gx_` contains caption text) | test XML nodes need semantic identity (`resource-id="...:caption_edit_text"`) added, else `_caption_field_text_from_xml` returns None → fail-closed |

Never edit production to make a stale test pass: the audit fix is the contract.

## Phase 4 — Regression tests (one per finding, pin fail-closed)

1. Same signature already reserved → `_maybe_soft_reboot_recovery` second call returns
   False, reboot counter stays 1, run budget unchanged.
2. VERIFIED denied when any proof field missing (started/post_reboot_verified/before/
   after/verifier) → allows_coordinate_fallback False; RECAPTURED/RETRYING without
   proof → `EVIDENCE_MISSING`, never auto-migrated to VERIFIED.
3. ATX-kill recovery fail-closed: missing pre artifact OR `reporter.save_checkpoint`
   raises → returns False, `atx_kill_signatures[signature]` NOT consumed (rollback),
   no continue; happy path consumes exactly once.
4. Coordinate fallback passes the POST-TAP fresh artifact path into `_wait_for_feed`
   (`screenshot_path == cf-after.png`), never the pre-tap frame.
5. Non-caption focused EditText (gx_) returns False from `_caption_typing_ratio_ok` and
   `_caption_chunk_landed` even when its text contains the caption; semantic
   `caption_edit_text` node passes.

Insert with a Python editor script (see `snippet-splice-edits.md` for the splice
pattern), keyed on the unique `def test_...` anchor of a neighboring test,
`assert text.count(anchor) == 1`, run, delete script.

## Phase 5 — Docs + verification + handoff

- Docs (`docs/*.md`, Vietnamese) gain a "vòng N" round bullet totalling the changed
  safety behavior and the new `- Regression tests:` list; preserve the file's EOL.
- Verify order: focused `-k` green → full `pytest tests/ -q` green → EOL asserts → git
  status shows only the expected files → no commit/push.

## Edit-tool and EOL findings (hard-won)

- **Heredoc trap**: `python - <<'PY'` fails with `unexpected EOF while looking for
  matching quote` when the payload contains nested triple-quoted strings with
  apostrophes. Fix: `write_file` the editor to `_edit_xxx.py`, run `python _edit_xxx.py`,
  delete after.
- **`Path.read_text(newline='')` raises TypeError** (no such kwarg in 3.x). Use
  `open(p, 'r', encoding='utf-8', newline='')` / `write` with `newline=''` for
  byte-exact EOL round-trip; assert `'\r\n' not in text` on pure-LF files.
- **`patch` (V4A) on duplicated anchors**: "Found N matches for old_string" aborts the
  whole patch — use replace_all or unique context; multi-hunk patches fail wholesale if
  ONE hunk is ambiguous.
- **fresh anchor across files typed**: after repeated patch failures, stop and switch to
  the Python editor script rather than looping (`patch` loop warning fires ~3×).
- **`patch` EOL inconsistency**: the first multi-hunk/large-lines patch inserted LF
  lines into a CRLF source file; later single-hunk edits preserved CRLF. Never trust
  patch output for EOL-integrity claims — re-verify with the EOL assert, and for
  "preserve EOL" requirements do the whole edit in the Python script.