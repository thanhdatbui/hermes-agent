# Live Canary After a Code Fix

## Trigger
Use only when the user explicitly authorizes live execution to validate a just-completed fix. Offline tests alone do not establish runtime acceptance; a wrapper exit code alone is not evidence.

## Bounded recipe
1. Resolve the named machine and serial from the authoritative mapping. Do not infer a target from an alert screenshot. Check the serial is online, TikTok package is installed, and no active lock is held by another owner.
2. Capture a fresh preflight screenshot and focus record before state-changing actions.
3. Run only the smallest production path that exercises the fix. For classifier/feed regressions, use the target-scoped `feed-session-smoke` path with `--allow-navigation-only --allow-feed-swipe`, `--max-swipes 1..3`, and no follow/like/upload. Do not add `--prepare-tiktok` unless explicitly required.
4. Inspect the run directory's `summary.txt`, `run_manifest.json`, and `log.jsonl`. Locate the exact final attempt artifacts named by the log and open both `ui.xml` and the matching `screen.png`.
5. Evaluate acceptance from fresh evidence:
   - final status is `success`;
   - requested/completed swipes match;
   - target package is TikTok;
   - classifier records expected feed (`for-you` for this regression), `manual_needed=false`, and safety `ok`;
   - zero records contain `unknown TikTok state`;
   - any transient typed popup has a bounded, evidence-backed handler and a fresh post-action known-feed capture.
6. Verify the live lock root after completion. Historical backup/quarantine lock files do not prove an active lock. Report exact evidence paths and stop after the canary; one target does not prove fleet-wide success.

## Evidence pattern from a successful canary
- `summary.txt`: `final_status=success`, `total_swipes_requested=3`, `total_swipes_completed=3`.
- `log.jsonl`: multiple `classify_screen` records with `detected_screen=for-you`, `manual_needed=false`, `safety_status=ok`; no `unknown TikTok state` records.
- Matching screenshots visually show TikTok Home/For You with the selected `Đề xuất` tab and no unknown-state screen.
- A typed popup can appear during the run without failing the canary only when its post-dismiss capture returns to a known feed and the safety row remains `ok`.

## Reporting
Keep the operator report short: target, canary scope, PASS/FAIL/BLOCKED, completed swipes, classifier/safety result, exact summary/log/screenshot paths, transient popup facts, and whether the lock was released. Do not claim that the fix is fleet-wide or that a live result proves code provenance beyond the exercised path.

## Pitfalls
- Do not report PASS from `success` printed by the launcher before reading artifacts.
- Do not count a historical `machine_65.lock.json` in backup/quarantine as an active lock.
- Do not replace the matching screenshot with a later Home/Launcher screenshot.
- Do not expand a permitted canary into a full batch or blind retries.
- Do not include credentials, workbook account values, or secrets in the reference or final report.
