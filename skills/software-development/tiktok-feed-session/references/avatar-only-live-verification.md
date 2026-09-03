# Avatar-only live verification

Use this reference when the operator explicitly requests avatar-only TikTok work and forbids video/post/workbook activity.

## Safe execution contract

1. Read the repository rules first. The required runtime shape is:
   `--no-dry-run --avatar-smoke --force-avatar-upload --force-avatar-machines N`.
   Do not substitute a normal upload run or use `--force-avatar-upload` without `--avatar-smoke`.
2. Fresh-check **all** live workers, not only `tiktok_workflow`: scan WMIC for both
   `tiktok_workflow` and `run_tiktok`/`--machine`/`config-machine`. Only the explicitly
   documented watcher and Hermes services are exceptions. Do not kill an unrelated live worker;
   wait for it to exit and re-check.
3. For stale target locks, validate every target alias before archiving: exact machine,
   exact serial, `project=tiktok-upload`, `status=handoff`, `owner_active=false`, and recorded
   PID dead. Archive only the named machine and serial aliases; never sweep foreign locks. Write
   a timestamped evidence JSON listing the archived aliases and `foreign_locks_touched=[]`.
4. Run one independent process per machine, with at most two concurrent processes. Preserve the
   target-specific log path and report path.

## Confirmation-token pitfall

The shell recipe may show `echo "YES"`, but the installed runtime can enforce a literal
interactive token such as `AVATAR-SMOKE`. If the log ends immediately with `Aborted.` at the
confirmation prompt, classify it as a pre-action abort (not a live attempt): no report/action
should exist. Do not edit source/config to work around it. Re-run with the exact avatar-only
flags and the token the runtime actually requests, after another fresh process/lock check.

## Success gate

For each new report and log, require all of the following:

- report `status=AVATAR_SMOKE_SUCCESS`, `avatar_status=FORCED_REPLACED_VERIFIED` (or the
  explicitly authorized avatar success signature), and no `AVATAR_*_BLOCKED` marker;
- log contains the avatar save-surface verification and source-similarity result. Record the
  similarity, threshold, and poll/attempt (especially whether post-save verification passed);
- state/log evidence is limited to the avatar path (`RESOLVE_DEVICE -> ENSURE_AVATAR -> RELEASE`).
  There must be no `POST`, `VERIFY_POST`, `UPDATE_WORKBOOK`, or video media-push state, and the
  report should not contain `post_submission_state` for a true avatar smoke;
- process exit is not sufficient by itself; independently inspect report and log, then confirm
  the target machine and serial lock aliases are absent after a verified success.

## Exact ladder reporting

Report each target separately. Distinguish normal TikTok startup relaunch from recovery ladder:

- B1 ATX-kill: exact log line or `not invoked`;
- B2 force-stop/relaunch recovery: exact log line or `not invoked`;
- B3 soft reboot: exact log line or `not invoked`;
- visual fallback/picker: exact evidence or `not used`;
- coordinate fallback: exact evidence or `not used`;
- `MANUAL_REVIEW`: exact evidence or `not reached`.

A normal `[OPEN_TIKTOK] Force-stop + relaunch 1/2` line is startup activity, not proof that the
B2 recovery rung ran. If a target fails, preserve the handoff lock and report its path; do not
archive/delete it after failure.
