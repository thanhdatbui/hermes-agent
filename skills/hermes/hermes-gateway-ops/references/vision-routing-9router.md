# Vision Routing Through 9Router

There are two primary modes for handling user-attached images with 9Router:

## Mode 1: Native Multimodal Model (Recommended for Gemini / Claude / GPT-4o on 9Router)

When using a vision-capable model directly (e.g. `ag/gemini-3.7-flash-high`, `ag/gemini-3.7-flash-low`, `gpt-4o`):

1. **Set native image input mode:**
   ```bash
   hermes config set agent.image_input_mode native
   ```
2. **Remove auxiliary vision config AND disable the vision toolset at platform level:**
   Do not configure `auxiliary.vision.provider` when using a native vision model. Additionally, disable the `vision` toolset so Hermes never injects `vision_analyze` into the tool schema or calls it as an intermediary:
   ```bash
   hermes tools disable vision --platform cli
   hermes tools disable vision --platform telegram
   ```
   Verify with `hermes tools --summary` that `Vision / Image Analysis` is disabled across all platforms.
3. **How it works:**
   Hermes packages the attached image directly as an OpenAI-compatible `image_url` element in `/v1/chat/completions` payload to 9Router. The model reads the pixels in the primary turn with zero intermediary hops.

## Mode 2: Text-Only Main Model + Auxiliary Vision Pool

Use this when the active Hermes main model is strictly text-only (e.g., DeepSeek V4 Flash) but images must still be understood through a vision-capable pool model served by 9Router.

### Architecture

```text
image attachment
  -> Hermes image_input_mode=text
  -> vision_analyze / auxiliary.vision
  -> 9Router /v1/chat/completions
  -> vision-capable pool model
  -> text description
  -> text-only main model
```

`agent.image_input_mode=text` is the safe explicit setting for a non-vision main model: Hermes pre-analyzes the image and sends the description to the main model instead of sending raw `image_url` content to it.

### Configuration for Mode 2

Apply settings with `hermes config set`; do not hand-edit `config.yaml` and never put the API key itself in config.

```bash
hermes config set model.default deepseek-v4-flash
hermes config set model.provider custom:9router
hermes config set agent.image_input_mode text
hermes config set auxiliary.vision.provider custom:9router
hermes config set auxiliary.vision.model ag/gemini-3.6-flash-low
hermes config set auxiliary.vision.base_url http://127.0.0.1:20128/v1
hermes config set auxiliary.vision.key_env NINEROUTER_API_KEY
hermes config set auxiliary.vision.api_mode chat_completions
hermes config show
hermes config check
```

The `key_env` value is only the environment-variable name. Do not print or copy the secret value into chat, YAML, logs, or a skill.

## Verification

1. `hermes config show` must show the main provider/model and the auxiliary Vision provider/model without exposing secrets.
2. `hermes config check` must pass.
3. Confirm the selected model is actually available from 9Router via `/v1/models`.
4. Run one offline/local endpoint smoke test with a small image encoded as a data URL and a short prompt. Use the API key from the environment; never print it. Confirm HTTP 200 and a non-empty assistant description.
5. Start a new Hermes process/session. A running gateway does not reliably reload provider/task configuration; restart it only from an external shell and never during a live farm batch.

A successful response may report a routed model name different from the requested pool alias (for example, a tiered Gemini name); verify the HTTP response and non-empty content, not only the requested alias.

## Failure interpretation

- `429 FreeUsageLimitError` from a selected vision model means that vision pool/model is rate-limited. It does not prove that Hermes bypassed 9Router. Switch the auxiliary vision model to another known vision-capable pool entry and retest.
- `400 Unsupported model` means the alias is not accepted by the active 9Router catalog; query `/v1/models` and use an ID returned there.
- A text-only main model receiving raw image parts indicates the image mode is wrong or the process has stale config. Set `agent.image_input_mode=text` and start a fresh process.
- `hermes config get` is not a valid command in current Hermes CLI; use `hermes config show`, `hermes config set`, and `hermes config check`.

## Validated example

On the local 9Router endpoint (`http://127.0.0.1:20128/v1`), `ag/gemini-3.6-flash-low` returned HTTP 200 with an image description. `oc/mimo-v2.5-free` returned a provider-side 429 rate-limit error, and `mmf/mimo-auto` returned an unsupported-model error. Treat these as routing/model-selection evidence, not as proof that the Hermes vision path is outside 9Router.
