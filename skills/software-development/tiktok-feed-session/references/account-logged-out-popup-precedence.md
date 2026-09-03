# Account-logged-out popup precedence

## Trigger
Use when a TikTok feed-session alert or screenshot shows an account-status dialog such as:
- `Trạng thái tài khoản` + `đã bị đăng xuất`
- `Account status` + `logged out`

## Required classifier behavior
Treat the paired title/body markers as an account/login safety state, not as a benign popup. Classify before generic popup detection as:

- `screen: manual-needed:login`
- `manual_needed: true`
- quarantine/manual review path

Do not add this dialog to the benign allowlist. Do not tap its `OK`, swipe through it, or attempt automatic re-login.

## Regression shape
Add an XML fixture containing the exact title, logged-out body, and any visible button. Assert:

1. the classifier returns `manual-needed:login`;
2. `manual_needed` is true;
3. the generic popup path is not selected;
4. the generic two-swipe recovery seam is not consumed for this state.

## Live evidence gate
Code-level classification proof is separate from live-incident proof. Before a target canary, read the exact target `log.jsonl`, matching `ui.xml`, and matching `screen.png`. Resolve machine → row → serial from the canonical mapping first. If target mapping or matching artifacts are unavailable, report `TARGET_RESOLUTION_UNPROVEN` / `capture_artifact_missing` and do not run live.
