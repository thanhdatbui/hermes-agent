# Targeted live-canary acceptance and recovery-path notes

Use this reference when a user requests a fixed-machine/fixed-row owner-recovery or live canary for `multi-machine-feed-session`.

## Resolve the real entrypoint first

1. Verify the requested script exists in the checkout before invoking it. Do not infer that a bootstrap scope, handoff note, or user-mentioned filename means the file is present.
2. If the named owner-recovery wrapper is absent, do not invent a bypass. Trace the actual consumer entrypoint and its supported recovery flags. In the Taadaa feed consumer, the supported path is `scripts/run-feed-session.ps1` → `python_runner/run_tiktok.py --mode multi-machine-feed-session`.
3. Keep the target fixed. Pass the explicit machine and row, and use an explicit artifact root for the canary.

## Official targeted recovery path

The consumer maps `--recovery-test-swipes 1..3` to its same-project recovery path. It enables the guarded `SAME_PROJECT_RECOVERY` takeover request with explicit authorization and the reason `artifact-backed same-project recovery handler`. This is different from a normal schedule run, which must not reclaim a retained handoff/blocked lock. Do not substitute `FULL_SCOPE_TAKEOVER` unless the user explicitly requests a cross-project/operator takeover and the repository contract authorizes it.

A representative command shape is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1' `
  -Machines 69 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync `
  -ArtifactRoot 'D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<canary-id>' -Run
```

If the target is not currently focused in TikTok, use the entrypoint's supported `-PrepareTikTok` option on the same target and retry; do not change machines, delete lock files, or manually unlock. Classify an initial focus/preflight stop separately from the retry result. A successful retry is the useful lesson; do not turn a resolved transient focus state into a permanent tool limitation.

## Acceptance is branch-specific, not runner-specific

A successful runner, completed swipe count, or final feed screen proves only the direct feed path. It does **not** prove a Story Reply detector or BACK+recapture branch ran.

For a Story Reply canary, require all of the following in the same target run:

- exact attempt `ui.xml` and matching screenshot exist and are inspected;
- the UI evidence contains the intended Story reply/composer ownership markers, or the structural fallback's complete bounded evidence;
- the log records the Story Reply detection/handler decision;
- the log records the BACK action and a fresh recapture after it;
- the post-action artifact proves the composer/overlay is gone and the target is back in the feed;
- final `final_status`, `stop_reason`, swipe/step counts, and lock handoff proof are collected.

If the run only shows ordinary feed swipes and keyboard cleanup, report Story Reply coverage as **UNPROVEN**, even when `final_status=success`. Never promote a generic feed success into proof of a conditional recovery branch.

## Evidence and lock closeout

Read the target run's `log.jsonl`, machine summary, run manifest, exact attempt XML/screenshot, and `recovery_lock_handoff.json`. Redact serials, account identifiers, worker IDs, command secrets, and credentials in reports. Confirm the lock state through the repository/core inspection API or handoff artifact; never unlink, overwrite, or reap the lock manually during the canary.

Report separately:

- command and fixed target;
- runner result and child-target result;
- branch coverage (`CONFIRMED`, `EXCLUDED`, `UNPROVEN`);
- `final_status` and `stop_reason`;
- absolute artifact paths;
- post-run lock proof;
- code failure versus preflight/device-state failure.
