# Catalog vs picker boundary (OmniRoute/Hermes)

Use this when a local OpenAI-compatible app reports a large model count but the operator wants a curated model picker.

## Diagnosis

1. Query the app's actual `/v1/models` endpoint and record its count/list separately.
2. Trace the client picker path. Hermes's custom-provider picker can probe the endpoint and replace configured models with the live response.
3. Provider-dashboard visibility controls are not automatically client-picker controls. Hiding models in an app UI may change one provider's dashboard list while leaving the client's aggregate `/v1/models` count unchanged.

## Safe Hermes configuration pattern

For a named custom/provider entry, keep the endpoint and credentials unchanged, then configure only the catalog boundary:

```yaml
providers:
  omni:
    api: http://127.0.0.1:20129/v1
    transport: chat_completions
    discover_models: false
    models:
      antigravity/gemini-3.7-flash-high: {}
      antigravity/claude-sonnet-4-6-high: {}
      antigravity/claude-opus-4-6-thinking-high: {}
```

Use Hermes's supported config writer or programmatic API (`hermes_cli.config.save_config()`); do not bypass security guards by directly clobbering unparsed text.

**Dictionary structure pitfall:**
When using `hermes config set providers.<slug>.models '{"model": {}}'`, the CLI may store the string representation as a YAML string scalar rather than a nested dictionary. Always verify that `type(config['providers']['<slug>']['models']) is dict`. If updating via Python script, construct the dictionary object and pass it to `save_config(updated, strip_defaults=False, merge_existing=False)`.

Also ensure `default_model` under `providers.<slug>` is set to the intended curated model/combo alias, so default provider selection resolves directly to the pool.

## Acceptance checks

- Read back the effective config and verify `discover_models: false` plus exactly the intended model keys.
- Invoke the same picker inventory function/path used by the client and verify its provider row has the intended count/list.
- Query the app's `/v1/models` again and report its independent upstream count; it may remain large and is not, by itself, a failure.
- Send one minimal generation canary through the exact listener for every retained model. Record only HTTP status, finish reason, short response text, and elapsed time.
- Confirm global provider/model and neighboring ports/processes are unchanged.

## Pitfalls

- Do not claim “the app has three models” when only the Hermes picker has three configured choices; describe the two layers precisely.
- Do not delete runtime databases or OAuth/account state to reduce a client-facing count.
- Do not restart a gateway/farm merely to refresh a static picker configuration unless restart is explicitly in scope or demonstrably required.
