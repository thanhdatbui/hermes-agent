# Offline real-boundary fixtures

Use this pattern when a closeout contract requires proof through a large orchestration loop without live network/device access.

## Recipe

1. Keep the test in the existing focused test module and invoke the public production entry point (for example, `run_conversation`).
2. Monkeypatch only the per-turn context/prologue builder, the model middleware/API callback, and fallible post-loop finalizer or side-effect sinks.
3. Build a narrow fake agent with explicit fields and methods used by the one-response path. Include a deterministic fake transport whose `validate_response()` succeeds and whose `normalize_response()` returns a text response with no tool calls.
4. Patch the real dispatch seam (`_ra()` or equivalent) to a handler that records calls and returns both an OK result and an unavailable result in separate turns.
5. Exercise an explicit trigger, an imperative/non-trigger, and an unavailable-advisor turn. Assert primary text preservation, the rendered advisor separator only on OK, exactly one advisor call per advice turn, and metric deltas for triggered/ok/unavailable/skipped.
6. Reset process-global counters at test start or compare against a baseline, so prior tests cannot affect the assertion.

## Evidence discipline

Run the required focused pytest command after the final edit, then the exact compile and diff-check commands from the contract. A red fixture run is useful TDD evidence, but it is not final verification. If a tool-call budget or timeout prevents the mandated commands, report the gates as unverified instead of claiming completion.

## Pitfalls

- Calling only `_compose_advisor_response()` proves formatting, not integration with the real loop boundary.
- A permissive fake (`__getattr__` returning mocks) can hide a missing production dependency; prefer explicit methods.
- Patching the helper under test defeats the regression. Patch the advisor dispatch seam and model/side-effect boundaries instead.
- Declaring a redaction regex is insufficient: call it through the request-payload path and assert the secret value is absent.
