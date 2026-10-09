# Semantic Detector Fixes from Confirmed UI XML

Use this when a UI detector falls through to `unknown` even though the captured XML proves a known screen.

## Workflow

1. Read the exact case docs requested by the coordinator before editing.
2. Open the exact XML artifact(s), identify the package-owned nodes, and record resource-id plus visible text. Do not infer from a summary.
3. Trace the detector and its caller. Prefer the smallest existing-style change at the canonical detector (`detect_after_continue`, parser, or classifier), not a new state or recovery flow.
4. Reuse the existing accent-normalization helper and add a semantic phrase/co-occurrence marker grounded in the XML. Prefer stable title/description/action combinations over an email address, bounds, or a single generic word.
5. Return the existing canonical state already handled by the caller. Do not alter downstream OTP behavior, invent login behavior, or add recovery actions.
6. Preserve fail-closed behavior: truly unknown XML must still return `unknown` and reach the existing bounded failure path.
7. Keep the scope locked to the named file. Run exactly one focused offline check using the existing harness or a minimal mocked parser invocation; do not use live ADB or create a broad test suite.

## Example pattern

For an XML screen containing a normalized title such as `xac minh email`, a description containing `su dung lien ket nay hoac nhap ma`, an OTP input resource-id, and a resend-code action, add the smallest semantic match that returns the already-supported `registered_otp` state. The match should be specific enough not to classify unrelated screens and should be checked before timeout/unknown fallback handling.

## Verification evidence

Report the exact modified file, `git diff --numstat`, the single focused command and its real output, and any remaining uncertainty. If the patch or check cannot be completed within the coordinator's budget, stop rather than claiming implementation or test success.

## Bottom-sheet and fallback-gap pattern

For a known login-choice bottom sheet, classify from package-owned semantic co-occurrence rather than a generic word or bounds: normalized title text plus the stable title/action resource IDs (for example, a title node and repeated button IDs). A resource ID alone is not sufficient, and raw whole-XML matching is unsafe because Android attributes can create false positives.

Trace both detection surfaces before editing. If the caller has a secondary `unknown` fallback scan, mirror the same narrow marker there so a slow/late capture cannot regress to `[07]`; route both surfaces to the caller's existing canonical state (such as `registered`) and existing safe branch. Do not add a new state, click any sheet option, solve OTP, or bypass the UI.

The focused offline check must exercise every fresh fixture named by the task plus one minimal unrelated/unknown XML and assert the negative remains `unknown`. Keep it mocked/XML-only, under the requested time budget, and never compensate for an incomplete offline check with a device run.
