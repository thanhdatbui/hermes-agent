# Live Canary: Worker Summary vs Verified Evidence

## Durable lesson
A worker's `completed` summary is not live-canary proof. In one OCR-primary rollout, unit tests passed, but the worker was blocked from creating the requested screenshot; the target device was still on Launcher/Sleep. The correct result was `UNPROVEN`, not PASS.

## Required evidence chain
1. Inspect the exact numeric machine first and record serial, model, power, and focus.
2. Run the official bounded runner once for that machine/serial and account row. Do not replace the official flow with a newly invented Python probe.
3. Preserve the literal command, exit code, stdout/stderr, `FOLLOW_RESULT`, and target artifact root.
4. Read the fresh target artifact directly: manifest/summary/log/state as applicable. A worker narrative and an exit code are not enough.
5. Verify a same-attempt screenshot exists, is fresh, non-trivial in size, and is not Launcher/Home/lock screen or a black/dozing capture.
6. Before sending `MEDIA:`, inspect the exact image with vision/OCR. Confirm the target app/screen, expected post-condition, and absence of popup obstruction or crop damage; then state what was seen.
7. Capture evidence before teardown/Home and reconcile both machine and serial lock aliases afterward.

## Reporting states
- `PASS`: official runner + target artifact + matching visual proof + lock reconciliation.
- `UNPROVEN`: code tests or worker summary exist, but live artifact/visual proof is missing or mismatched.
- `BLOCKED`: official runner could not execute or a safety/ownership gate prevented the canary.

Keep pytest evidence separate from device evidence: `281 passed` proves offline regression coverage, not that WinRT OCR ran on a real Samsung device.
