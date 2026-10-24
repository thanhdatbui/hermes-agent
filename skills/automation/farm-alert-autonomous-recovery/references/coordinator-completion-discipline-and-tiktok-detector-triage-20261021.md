# Coordinator completion discipline and TikTok detector triage

## Durable lessons

- A mixed farm alert is an active recovery task, not a reason to stop after read-only triage. Split infrastructure/transient failures from actionable software or detector failures, then continue the actionable lane to a bounded worker dispatch or exact evidence-backed escalation.
- Do not report `BLOCKED` merely because some devices are offline, timed out, or require manual handling when a reproducible detector/flow issue has already been isolated. Report the blocked device subset separately and keep the repair lane moving.
- Use the machine-level manifest as the per-device source of truth. Reconcile aggregate counters against it and explicitly report counter discrepancies.
- For TikTok profile/switcher incidents, inspect captured UI XML and screenshot artifacts before changing the classifier. A screen containing `Follow bạn bè của bạn`, `Follow bạn`, or `Follow lại` may be a benign TikTok suggestion surface that must be handled before identity verification; do not classify it as an unknown TikTok state without tracing the detector path.
- User frustration is a signal to execute, not ask for permission or stop. A completion report should contain actual modified files, focused test output, and diff/stat evidence. Model identity may be stated when asked, but is not a reason to stop.

## Reproduction evidence from the session

- Kibe M3 artifact UI XML contained TikTok suggestion text: `Follow bạn bè của bạn`, `Follow bạn`, `Follow lại`.
- The relevant detector path was `_detect_follow_friends` / `_dismiss_follow_friends` in `python_runner/flows/benign_popup_registry.py`, with profile identity verification in `python_runner/flows/feed_swipe_smoke.py` and screen classification in `python_runner/core/classifier.py`.
- The first response incorrectly stopped at a mixed-farm `BLOCKED` report even though an actionable detector issue had already been isolated. The corrected workflow dispatched a bounded worker with an explicit file scope, evidence, focused-test requirement, and no device interaction.

## Usage

Load this reference when a farm watchdog report mixes device failures with a reproducible UI/classifier issue, especially during TikTok profile switching or preflight identity verification.
