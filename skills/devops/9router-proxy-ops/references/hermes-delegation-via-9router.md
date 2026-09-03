# Route Hermes delegated workers through 9Router

## Trigger

Use this when `delegate_task` children repeatedly fail before their first tool call with a transport error (for example `API call failed after 2 retries: Connection error`) and the user wants workers routed through the local 9Router provider instead of Cockpit.

A child failure before its first tool call is not product/device evidence. Before redispatching a live task, reconcile the named target: exact process, exact lock aliases, and expected artifact count. This proves the failed child had no side effect.

## Configure future delegated children

Hermes has no `hermes config get` subcommand. Use `set`, then inspect the parsed YAML without printing secrets:

```bash
hermes config set delegation.provider 'custom:9router'
hermes config set delegation.model 'gpt-5.6-luna'
hermes config check
```

Important:

- Provider value is `custom:9router`, not bare `custom` or `9router`.
- This pins newly spawned children; it does not reroute a child already in flight.
- A gateway restart is not required merely to route a newly created delegation. Do not disrupt live farm jobs for this change.
- Do not modify 9Router combos or proxy pools as part of this operation.

Verify the active scalar values by parsing `~/AppData/Local/hermes/config.yaml` and printing only:

```text
delegation.provider
delegation.model
```

Never print `key_env`, API keys, tokens, or provider secrets.

## Prove the route before redispatch

Send one small OpenAI-compatible request to:

```text
http://127.0.0.1:20128/v1/chat/completions
```

with:

- `Authorization: Bearer $NINEROUTER_API_KEY`
- `model: gpt-5.6-luna`
- a deterministic short response request

Acceptance is all of:

1. HTTP 200.
2. Response JSON contains the intended model/route.
3. Expected response marker is present.

This proves 9Router transport/model resolution only. The subsequent `delegate_task` result is still required to prove worker execution.

## Cockpit residue is not an active route

A `custom_providers` entry named `cockpit` can remain available for manual selection without affecting current traffic. Determine whether Cockpit is active by inspecting:

- `model.provider` / active main model provider;
- `delegation.provider` / delegated-worker provider;
- `fallback_providers` for any Cockpit entry.

If main and delegation both use `custom:9router` and no fallback points to Cockpit, Cockpit is merely registered/selectable. Do not delete its provider block unless the user explicitly asks.

## Failure handling

- Do not keep submitting identical live workers after repeated pre-tool transport failures.
- After changing provider, run the route smoke once, reconcile target state again, then issue one fresh delegation.
- If the fresh worker executes but reports a product status such as `SKIPPED_LOCKED`, diagnose that product path separately; do not conflate it with the earlier transport error.
- For live device work, recheck exact process/lock/device state immediately before the new worker because conditions may have changed while transport was being repaired.
