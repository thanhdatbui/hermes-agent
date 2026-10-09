# Advisor Boundary Safety Remediation

Reusable offline verification pattern for read-only advisor/tool adapters.

## Production contract

- Parse advisor output into a strict object schema. Permit only a small allowlist of safe fields (for example recommendation, reasoning, confidence, next_steps, and plan); reject unknown keys, nested arbitrary objects, oversized strings/lists, and non-object advice.
- Normalize text with Unicode NFKC and remove zero-width/control-format characters before policy checks. Reject command-like content such as ADB/shell, curl, PowerShell, rm/delete, execute, tap, or swipe patterns. Keep the primary answer fail-open when advisor output is rejected.
- Bound the complete serialized UTF-8 request body after envelope escaping. Trim every user-controlled field, not only state/evidence. If values remain unserializable or the final body exceeds the limit, return an unavailable result before constructing or dispatching network I/O.
- Preserve existing safety invariants: loopback endpoint guard, empty tools, explicit no-tool choice, disabled check function, and bounded timeout.

## Offline seam tests

1. Call the production output-normalization/composition seam with an allowed object, an unknown-key/nested object, oversized values, and Unicode-obfuscated dangerous text.
2. Call the payload builder with oversized decision class, question, state, evidence, candidate actions, and constraints; measure `len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))` on the final payload.
3. Pass an unserializable value and patch the `urlopen` seam; assert unavailable output and zero network calls.
4. Reject a non-loopback endpoint and assert the registry entry still has `check_fn() is False`.
5. Return malformed provider JSON through the fake response seam and assert a fail-open error result with no advisor advice.

## Evidence discipline

Run the focused test after the final test/source edit, then compile checks and scoped `git diff --check`. Report exact pass count and commands. Offline seams do not constitute farm or live-provider end-to-end evidence.
