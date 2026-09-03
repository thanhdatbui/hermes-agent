# Focus-loss triage: preflight vs post-swipe recovery

## Incident pattern

A recurring `TikTok focus lost` alert can be a real launcher/SystemUI foreground transition even when a later run is healthy. Do not attribute it to the newest recovery commit from counters or an alert screenshot alone.

For one machine/run, preserve this evidence chain:

```text
exact log.jsonl window
  -> preceding focus/navigation event
  -> exact attempt ui.xml
  -> matching screen.png
  -> manifest/summary terminal status
  -> source call chain and commit diff
```

Redact account/credential identifiers in reports.

## Provenance checks

1. Convert timestamps consistently before comparing Telegram alert time with run logs. A Telegram screenshot time alone does not identify the run.
2. Prefer the machine-scoped `run_manifest.json` and `summary.txt` for run boundaries and stop reason.
3. Search candidate runs narrowly by date/row/machine; do not recursively scan the whole runtime tree when large roots can time out.
4. Require the exact artifact to exist and inspect both XML and screenshot. A directory, parser field, `xml_available`, or alert image is not proof.
5. Compare the failed run with the next run. A healthy later run can exclude a persistent device state, but does not explain the earlier transition.

## Call-chain distinction

Separate these recovery seams:

- **Post-swipe recovery:** after a swipe capture lands on Launcher/SystemUI, the post-swipe helper may force-stop/relaunch TikTok and recapture the feed.
- **Navigation/preflight recovery:** `dismiss_notification_shade -> verify_systemui_focus -> tap_navigation_target -> verify_tiktok_focus`. A focus loss here can happen before the post-swipe helper is called.
- **Baseline preparation:** launcher handling at startup is a different path again; do not assume it covers profile navigation.

A fix in one seam is not coverage for the others. When reviewing a candidate commit, map the changed helper to the actual failing event step and prove the caller reaches it.

## Strong evidence for a launcher/SystemUI focus loss

The failure is confirmed when the same event window contains:

- `focused_package` or `focus_package` equal to `com.sec.android.app.launcher` or `com.android.systemui`;
- a `verify_tiktok_focus`/navigation failure with reason `TikTok focus lost`;
- matching XML whose root package is Launcher/SystemUI, or matching screenshot showing Android Home/notification shade;
- preserved blocker status such as `manual-needed` and `cleanup_close_all=skipped` where policy requires scene preservation.

If the screenshot/XML is absent or timestamps do not correlate, report `UNPROVEN` rather than inferring the screen.

## Regression attribution rule

A commit is not the cause merely because it changes a recovery counter or is the newest fix. To call a regression, require:

1. the failing run started with the candidate code;
2. the event enters the changed call path;
3. the changed behavior creates or worsens the foreground transition;
4. an old/new comparison or focused regression test reproduces the difference.

Otherwise classify the result as `coverage gap`, `other actor`, or `UNPROVEN`.

## Verification pattern

For a code-fix request, remain read-only until the incident is proven. Add or run an offline fixture for: TikTok focused before navigation, tap/command returns OK, then post-action focus becomes Launcher/SystemUI. Assert fail-closed behavior and exact reason. Separately test that the recovery owner (if policy allows one) is actually called at that seam and that post-recovery XML/screenshot confirms TikTok.

Focused test output is supporting evidence only; it does not replace target-run artifacts.
