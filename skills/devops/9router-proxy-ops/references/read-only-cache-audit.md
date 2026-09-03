# Read-only 9Router cache audit

Use this when the user asks to inspect 9Router, verify prompt caching, or compare a screenshot claim with the machine's actual usage. This is an evidence workflow, not a configuration change.

## Scope and safety

- Read only: do not edit combos, provider pools, model routes, Hermes config, or the database.
- Do not restart 9Router or send a probe request merely to measure cache; use existing traffic.
- The preferred local evidence source is `%APPDATA%\\9router\\db\\data.sqlite`, opened with SQLite read-only mode.
- Dashboard/API endpoints may return `401 Unauthorized` until authenticated. That does not mean the local usage ledger is empty.

## Evidence extraction

`usageHistory` contains:

- `timestamp`, `provider`, `model`
- `promptTokens`, `completionTokens`, `cost`
- JSON `tokens`, commonly containing `prompt_tokens`, `completion_tokens`, `total_tokens`, `cached_tokens`, and `cache_creation_input_tokens`

Inspect the schema first. Parse `tokens` JSON and aggregate by `provider + model + date/window`; never rely only on a global total. Calculate:

```text
cache ratio = sum(cached_tokens) / sum(promptTokens) * 100
```

Only calculate a ratio when the cache field is present. Keep missing-field coverage explicit. Do not count `cache_creation_input_tokens` as cache-read tokens, and do not silently turn a missing field into proven zero.

## Route matching

Check Hermes' configured provider/model, then report the matching 9Router provider/model rows. A combo name is not proof of the final upstream route: fallback may select another model. Report both the configured route and observed route when they differ.

## Interpretation

- Cache is provider-, account-, prefix-, workload-, and timing-dependent. A route near 0% can coexist with another route at 70–90% on the same machine.
- High cache ratio proves reusable prompt-prefix hits only. It does not prove token compression, a larger ChatGPT/Claude subscription quota, or an AI Coworker feature.
- Keep prompt caching separate from Hermes context compression.
- `usageHistory.cost` is a 9Router local estimate, not authoritative provider billing.

## Reporting format

For this user, report in short Vietnamese with facts only:

1. measured date/window;
2. provider/model actually observed;
3. prompt total, cached total, and calculated ratio;
4. evidence path/table;
5. blocker or uncertainty, if any.

Do not reproduce a long dashboard explanation when the user asks only whether the claim applies to their setup.
