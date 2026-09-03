# Phase Acceptance Probe: Journal Event + Maintenance Manifest + Offline CLI

Worked case: read-only Phase 6 audit of commit `33f6c4d` (tiktok-luot nuoi acc) — verdict
`APPROVED`. Reusable numbered probe plan (P1–P7) for any commit that adds a journal
event pair + a manifest `maintenance` block + an offline CLI flag, plus the Windows/MSYS
execution gotchas found while running it.

## Numbered probe plan (P1–P7)

Run all probes from **disposable temp state roots** (`tempfile.mkdtemp`) — one fresh root
per probe section, never reuse (see pitfalls). Assemble fixtures the same way the repo's
own test module does (source/feed/post dicts + `Picker.pick` with a `FixedClock`).

- **P1 Golden shape**: build the manifest via the real picker; assert the maintenance
  block's exact shape (`run_once_per_day is True`, `due_after_block == 3`, 6-element
  command starting `python` and containing the named script); then `validate_manifest`
  must pass on the untouched payload.
- **P2 Tamper matrix** (maintenance): deep-copy the payload, mutate ONE maintenance
  aspect per case — extra top-level key, extra key inside `clear_tiktok_cache`, flag
  false, due value changed, command lengthened, script path swapped, secret/workbook
  tokens spliced into the command, machine `0`, serial with a space, serial not in the
  source mapping. Record REJECTED reason per case (`SOURCE_CONFIG_INVALID` vs
  `MAPPING_CONFLICT` — the mapping case must reach the source-binding branch, not an
  earlier shape gate). Include one benign mutation that must stay ACCEPTED (same
  machine re-serial) to prove the validator is not reject-everything.
- **P3 Journal canonical append/replay**: append REQUESTED (assert auto-stamped
  manifest_id/sha256/path + timestamp present, terminal False); re-reduce the stored
  event through `reduce_and_validate(prior, event)` (replay == append validator);
  then assert rejections: DONE with wrong machine/serial (`IDENTITY_MISMATCH`), DONE
  before REQUESTED, REQUESTED after DONE, duplicate DONE (rejected at the transition
  gate, not by terminal dedup), unknown event name, wrong terminal flag both ways.
  Finish with a FRESH store reading the whole stream (proves replay of a full stream
  with the two cache events interleaved with nothing else).
- **P4 Timing sweep**: `clear_cache_due` across the window: before block-3 max
  `slot_end` → False; at/after block end → True; `02:00`–`06:00` → always False;
  and after a DONE exists → False even mid-window. Print the anchor `slot_end` so the
  report cites the real boundary, not the test comment.
- **P5 CLI offline idempotence**: static analysis first (no `subprocess` import in the
  CLI module, `--execute/--repo/--feed-workbook` refused via `parser.error`), then
  monkeypatch `subprocess.run` to record calls, run `main([...])` twice with
  `--clear-cache`, assert `calls == []`, exactly one REQUESTED event after run 1 and
  still exactly one after run 2, rc == 0, and the printed JSON carries the command +
  `"offline": true`.
- **P6 Cross-stream transition**: a cache REQUESTED must not follow another event on
  the same entry's stream (e.g. after DRY_RUN_PREVIEW) — rejected as invalid
  transition, not as a value error.
- **P7 Cleanup**: verify no repo bytecode, delete temp roots, re-run `git status
  --short` and compare to the pre-audit baseline line-for-line.

## Windows/MSYS execution gotchas

- Write the probe script to `%TEMP%`, run from the repo root.
- **Native Python cannot resolve MSYS paths.** `PYTHONPATH="$(pwd)"` fails with
  `ModuleNotFoundError` even with cwd = repo root (script lives in %TEMP%, so the
  script dir is not on sys.path). Use
  `PYTHONPATH="$(cygpath -w "$(pwd)")"` so the package resolves.
- Always set `PYTHONPYCACHEPREFIX="$(mktemp -d)"` for both probes and `py_compile` —
  no `.pyc` may land in the repo during a read-only audit.
- Cleanup command `rm -rf "$LOCALAPPDATA/Temp/hermes-audit-p6-"*` (flag-able by the
  approval system: "recursive delete"/"delete in root path") — scope it to the
  `%TEMP%` prefix and it auto-approves; or just leave dirs and remove the probe file.

## Journal probe pitfalls (probe bugs ≠ repo findings)

- **exact_fields are strict.** Appending `DRY_RUN_PREVIEW` without `idempotency_key`
  fails "journal event fields are not canonical" — that is a probe bug. Always supply
  every field of the event's canonical shape, usually from the manifest entry itself
  (`entry["idempotency_key"]`).
- **CLI source config must live under `--offline-root`.** `StatePaths.regular_file`
  rejects any path outside the offline root (`INVALID_PATH`); write `fleet-source.json`
  into the offline root, not the probe temp root.
- **One state root per probe section.** A DONE appended in one section makes
  `clear_cache_due` return False forever after (by design) — timing probes need a
  fresh root. Journal/pointer share filesystem state; reused roots silently pollute
  later probes.

## Provenance checks on Windows git

- `git ls-tree -r --name-only <commit> -- <path>` can return **empty for tracked
  files** on MSYS git — do not conclude "absent from parent". Fall back to
  `git ls-tree -r --name-only <commit> | rg '<path>'`.
- Prove the inspected worktree == committed blob:
  `git hash-object <path>` vs `git rev-parse <commit>:<path>` (match for every file
  in scope, both A and M). For `A` files this also proves the untracked baseline is
  byte-exact and gives you a hash to cite.
- `git diff --numstat <parent> <commit>` separates narrow edits (`M`, small +/-) from
  full-file additions (`A`, 0 deletions) — only claim "only the named lines changed"
  for real modifications.
- The suite command is the acceptance gate: run the exact pytest invocation the user
  named, record the pass count, then `py_compile` + `git diff <parent> <commit>
  --check` + final `git status --short` in one batch.

## Verdict discipline

Line 1 `APPROVED | MINOR_FIXES | REJECT`; evidence table per gate (commit scope,
provenance, probes with ACCEPTED/REJECTED per case, suite output, compile/diff-check,
final status unchanged); NITs (stale comments, harmless duplication) listed separately
and explicitly marked non-blocking; state "no repo files modified".