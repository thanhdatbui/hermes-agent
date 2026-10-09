# OmniRoute Combo vs client-side fallback

## Decision model

Treat these as two layers, not competing implementations:

- **OmniRoute Combo**: execution-layer routing inside the proxy. It can select another credential in the same model pool, apply pool tiers, preserve or disable session/prompt-cache affinity, observe quota/cooldown state, and fail over before retry when configured.
- **Client/Hermes fallback**: gateway-level rescue when the selected OmniRoute request or the whole proxy path fails. It normally sees only the final HTTP outcome and cannot reliably select a healthy credential inside the OmniRoute pool.

Preferred topology:

```text
Hermes -> OmniRoute `omni-worker` Combo -> credential/model tiers
       -> Hermes/9Router fallback only if OmniRoute or its gateway path is unavailable
```

## Evidence pattern from AI-Tools

In `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`, `omni-worker` is a priority combo with Gemini Pro, Gemini Free, Codex, and Claude tiers. Its relevant controls include `failoverBeforeRetry`, `maxGlobalAttempts`, and nested combo execution. The Gemini pool uses `stickyRoundRobinLimit` and session-stickiness controls to balance account spread against prompt-cache affinity.

The custom fail-fast design documented in `docs/ai/omniroute-failfast-semaphore-custom-patch.md` treats blocked/rate-limited semaphore states as immediate capacity errors and skips to the next target instead of waiting 30–90 seconds. Verify that the production bundle was rebuilt/restarted before claiming this behavior is live.

## Diagnostic rule

Do not infer that fallback worked merely because the UI says `retry`, `auto`, or `poolSize`. A response showing `attempted: 1` and a terminal 403 only proves that one route was attempted. Check:

1. The request model actually resolved to `omni-worker` (not a direct provider alias such as `antigravity/claude-sonnet-4-6`).
2. The active runtime has the expected Combo and patch loaded.
3. The error class is recognized as failover-capable rather than terminal permission/auth failure.
4. Logs or call telemetry show the second target and final outcome.

## Operational recommendation

Use `omni-worker` as the normal Hermes model when account-pool resilience is desired. Keep Hermes fallback as a coarse last-resort layer. Avoid redundant nested fallback chains unless logs identify which layer made the switch; otherwise debugging and session affinity become ambiguous.

## Pitfalls

- A well-designed Combo does not help a request that bypasses the Combo with a direct provider/model alias.
- `health 200` does not prove the dashboard/build is correct; production updates must preserve the full dashboard and verify routing separately.
- A quota/permission failure can be terminal even when a generic retry label is displayed; classify the actual error and inspect route attempts.
