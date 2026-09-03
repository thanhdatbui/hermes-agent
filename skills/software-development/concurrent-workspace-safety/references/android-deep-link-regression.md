# Android deep-link regression pattern

Use this pattern when a browser/UI coordinate tap visibly foregrounds the target app but leaves it on the pre-link screen:

1. Preserve the evidence-backed coordinate tap; do not replace it with a generic text or bare `here` tap.
2. If CDP/DOM inspection already verified the exact deep-link `href`, issue an explicit Android VIEW intent immediately after the coordinate tap:
   `am start -a android.intent.action.VIEW -d <exact-href>`.
3. Keep the strict postcondition verifier. Foreground package alone is insufficient; require the real target state (for example registration-entry, password-required, or verified success). A screen such as “check your inbox” must remain non-success.
4. Test both sides: exact intent arguments/order and fail-closed behavior when the strict return verifier rejects the unchanged screen.
5. In a dirty Windows repository, never run live device/mailbox/workbook actions for this regression. Use fixtures/mocks and preserve CRLF in legacy files.

When the harness cannot identify a canonical test command, create a deterministic temporary probe with `tempfile.NamedTemporaryFile(prefix="hermes-verify-", dir=<OS temp dir>, delete=False)`, run it in the project’s real target environment, report it explicitly as **ad-hoc verification** (not suite green), and remove it in a cleanup step.
