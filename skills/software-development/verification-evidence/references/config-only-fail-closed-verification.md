# Configuration-only fail-closed verification

Use this reference for small runtime configuration changes that must disable a network fallback without exercising providers or live traffic.

## Source-of-truth checklist

1. Identify the actual runtime launcher and process command line.
2. Inspect launcher/service environment assignments first; these can override `.env`.
3. Trace bootstrap precedence: persisted `server.env`, preferred `.env`, process environment, then defaults.
4. Inspect the runtime feature-flag store/database for overrides; DB overrides may outrank environment variables.
5. Bind the edit allowlist to the authoritative `.env` and any launcher that actively sets the target keys.
6. Preserve unrelated dirty paths and do not touch concurrency, retry, routing, provider tests, GPM, or account state.

## Minimal patch contract

For direct-IP fallback disablement, the relevant values must be exactly:

```text
PROXY_FAIL_OPEN=false
OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=false
```

Patch existing assignments rather than appending duplicate keys. If a watchdog injects `true`, changing only `.env` is insufficient.

## Fresh evidence window

Run a side-effect-free verifier against the live files. Assert:

- both `.env` keys parse to `false`;
- watchdog/service launcher assignments parse to `false`;
- no higher-precedence feature-flag DB override enables the control-plane fallback;
- each edited format parses successfully;
- scoped diff/whitespace checks pass.

On Windows, create any required `hermes-verify-*.py` under `%TEMP%` using `tempfile`, execute the literal path in a fresh interpreter, and remove only the verifier created in the current run. Report the verifier as ad-hoc verification, not as a full test-suite pass.

## Live-process boundary

A static/bootstrap readback proves what a fresh runtime would receive. It does not prove an already-running process reloaded the values. Capture the current process PID and start time. Restart only when the service's restart mechanism is explicitly safe and bounded; otherwise report `restart required` and do not claim live effective values.

## Evidence wording

Report exact commands and real outcomes. Separate:

- fresh config/static verification;
- parser/compile/diff checks;
- live process freshness or restart requirement;
- explicitly excluded operations (provider test, outbound request, GPM, SIM/account actions).
