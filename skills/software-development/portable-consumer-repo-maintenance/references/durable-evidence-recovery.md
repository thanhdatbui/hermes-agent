# Durable-Evidence Recovery (attested outcomes + re-hash proof + reservation-before-action)

Verified 2026-08-09, Tiktok-video `scripts/tiktok_workflow/state_machine.py`, round R8a.
Applies to any consumer-automation state machine with **bounded recovery loops**
(reboot budgets, ATX-kill ladders) where evidence must survive process restarts and
double-execution must be impossible.

## Contract pieces

1. **Attested outcome gate** — an enum with an `allows_coordinate_fallback()`-style
   classmethod. Only the FULLY-VERIFIED outcome authorizes the risky last-resort
   fallback (coordinate tap). `ATTEMPTED_FAILED` blocks too: "attempted but
   unproven" must never tap blindly. Implement as `return outcome == VERIFIED` —
   a whitelist set that grows as new outcomes are added is a bug magnet.
2. **Durable proof** — VERIFIED is decided by *classification-time re-verification*,
   not by string markers in the checkpoint:
   - shape written by the live success path:
     `durable_proof = {signature, timestamp, before{path,size,sha256,signature,timestamp}, after{...}, verifier{identifier, success, timestamp}}`
   - validator re-reads the artifact files: exists + `size` == len(bytes) +
     `sha256` == recomputed digest; entry `signature` == proof signature;
     entry `timestamp` == record timestamp; `verifier.success is True` with
     non-empty identifier and timestamp.
   - legacy checkpoint (marker strings only, no `durable_proof`) → EVIDENCE_MISSING,
     never auto-migrated to VERIFIED. This was the core P1 fix: the old VERIFIED
     branch trusted `reboot_action_started + post_reboot_verified + path strings`.
3. **Reservation-before-action (idempotent)** — for side-effect recovery (ATX-kill):
   - persist a reservation (`atx_kill_reservations[signature]`) through the
     canonical `_save_checkpoint` BEFORE calling the side-effect function;
     save failure → return False, no action, no budget burn.
   - once the action starts, flip the reservation to terminal
     `ACTION_STARTED_UNVERIFIED` and NEVER roll it back — even when the later
     evidence/persist save fails. The consumed signature blocks a second
     execution. Rolling back on later failure was the old bug (allowed a second
     ATX-kill on a device mid-recovery).
   - persist in `_save_checkpoint`, restore in `_load_checkpoint` with type
     validation (dict-of-dict).

## Test migration when a gate tightens

When the new contract narrows an outcome enum (here: `ATTEMPTED_FAILED` used to
allow coordinate fallback), pre-existing tests asserting the OLD contract fail RED
legitimately. Update the test to the new contract (`assert not allows_...`), never
weaken production. Then pin each change with new regressions:

- enum: only VERIFIED allows the fallback (loop over all other outcomes → False);
- proof: valid `durable_proof` → VERIFIED; mutating the `after` file bytes →
  EVIDENCE_MISSING; missing/`None` fields → not VERIFIED; legacy marker-only
  checkpoint → EVIDENCE_MISSING;
- reservation: reporter save fails at reservation → side effect never called;
  save fails AFTER the action → reservation stays `ACTION_STARTED_UNVERIFIED`,
  signature stays consumed, second call returns False without re-running.

## Pitfalls (from the session)

- **Edit-script conversion discipline**: keep exactly ONE `\n` → `\r\n` conversion
  point (`apply_blob` / `apply_insert` helpers that convert old+new blocks). Any
  edit path that bypasses it — a regex slice with `re.S` (`.replace`/slice of the
  raw string), direct concatenation — injects bare LF into a CRLF file (144 bare
  LFs in one session). Purity assert after every write:
  `b.count(b"\r\n") == b.count(b"\n")`. If it breaks, repair with a bare-LF-only
  normalizer `re.sub(rb'(?<!\r)\n', b'\r\n', b)` — safe ONLY after confirming the
  original file had 0 bare LF (a pure-CRLF file; git status alone doesn't prove it).
- **Windows `Path.write_text` default `newline=None` translates `\n` → `\r\n`** —
  for LF-pure files use `write_bytes(text.encode("utf-8"))` (or `open(..., newline="")`).
- **Writer/validator timestamp scheme must match**: first draft of the validator
  required `before.timestamp != after.timestamp` (reboot changes the frame), but
  the live writer stamps both entries with one proof timestamp → contradiction.
  Drop invariants the writer cannot satisfy, or stamp per-artifact timestamps.
- **`search_files`/ripgrep can throw `IO error ... The system cannot find the path
  specified` on some drive paths** (both `D:\...` and `C:\Users\<u>\D:\...` forms).
  Fallback that always worked: `python -c` reading the file with `Path` + line scan
  (also yields line numbers + context for `pytest -k` selections).

## Verification recipe

1. RED: run the new regressions, confirm each fails for the expected reason
   (feature/contract missing, not a typo).
2. GREEN: focused set first (`pytest -k "TestRecoveryP1R8a or test_soft_reboot_verified..."`),
   then the wider slice (`-k "soft_reboot or atx_kill or coordinate_fallback or wait_for_feed ..."`).
3. EOL check per file — the same repo mixes conventions: `state_machine.py` pure
   CRLF, `test_tiktok_workflow.py` pure LF. Check each file's
   `count(b"\r\n") == count(b"\n")` (CRLF) or `count(b"\r\n") == 0` (LF).
4. `python -m py_compile` both files; `git diff --numstat` scoped to the two files;
   confirm the repo was already dirty and your delta is only the scoped files.
