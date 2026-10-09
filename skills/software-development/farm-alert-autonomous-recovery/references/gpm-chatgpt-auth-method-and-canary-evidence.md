# GPM ChatGPT-Web Auth Method and Canary Evidence

## Scope
Reusable evidence pattern for a single-profile ChatGPT-Web recovery canary on GPM.

## Ground truth before launch
1. Read the exact workbook row for the target email.
2. If `PASS CHATGPT` is populated, treat the target as Direct Email + Password unless a source artifact explicitly proves another auth method.
3. Do not infer SSO from a Gmail address, an existing provider row, or a prior summary.
4. Check whether the production watchdog has a single-target CLI. If it does not, do not run it as the canary; use a dedicated driver that imports the one-account recovery function.

## Canary success gate
A live canary is not PASS from process exit 0, GPM stop response, provider `isActive=true`, or a `COMPLETED_UNCONFIRMED` report. Require all of:

- fresh screenshot from the exact GPM profile;
- OCR/readback of that screenshot;
- no `Log in`, `Sign in`, `Sign up`, or equivalent auth controls;
- visible account identity/profile artifact;
- session token/provider validation bound to the same account;
- fresh post-action evidence path that exists and is not stale.

If OCR shows `Sign in with Google`, `Email or phone`, `to continue to OpenAI`, or another auth surface, classify the run as failed/unproven. It is not evidence of a bad password.

## Auth-flow mismatch pitfall
A driver that clicks `Continue with Google` for a Direct Email account can redirect to `accounts.google.com` and produce a misleading failure. The correct remediation is to change the driver to:

1. locate the OpenAI email input;
2. fill the target email;
3. click Continue/Next;
4. locate the OpenAI password input;
5. resolve the password from the workbook without logging it;
6. fill and submit;
7. verify the post-login UI and token.

If Google SSO appears unexpectedly, fail closed. Do not enter the OpenAI password into Google and do not manufacture a success by continuing through an unrelated flow.

## Evidence/reporting
Keep unique before/after screenshot paths and verify existence, size, timestamp, and OCR before reporting. State separately:

- `Confirmed`: exact screen text/artifact observed;
- `Excluded`: claims disproved by the fresh artifact;
- `Unproven`: provider state not revalidated or success gate incomplete.

Never call offline/mock pytest a live canary. Never call a successful cron trigger or a worker self-report live evidence.

## Observed case pattern
A target with workbook `PASS CHATGPT` was tested by a driver that still clicked Google SSO. The resulting screenshot OCR read `Sign in with Google`, `Email or phone`, and `to continue to OpenAI`; the correct conclusion was `FAILED/UNPROVEN auth-flow mismatch`, not `wrong password` and not success.
