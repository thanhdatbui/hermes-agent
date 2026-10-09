# Antigravity Gemini Thinking Budget & Tier Resolution

Authoritative reference for how OmniRoute (`:20129`) / 9Router (`:20128`) configure, cap, and translate reasoning budgets (`thinkingConfig.thinkingBudget`) for Google Cloud Code / Antigravity Gemini models (e.g. `gemini-3.7-flash-high`, `gemini-3.7-flash-tiered`, `gemini-3.8-flash-tiered`).

---

## 1. Request Pipeline & Thinking Injection

```
Client (Hermes / OpenAI format)
  ↓
openaiToGeminiRequest() [open-sse/translator/request/openai-to-gemini.ts]
  ↓ (injects thinkingConfig if absent)
wrapInCloudCodeEnvelope()
  ↓
AntigravityExecutor.transformRequest() [open-sse/executors/antigravity.ts]
  ↓ (cleanModelName: maps aliases via ANTIGRAVITY_MODEL_ALIASES)
  ↓ (applyAntigravityGenerationDefaults: ensures maxOutputTokens > thinkingBudget)
  ↓ (resolveAntigravityOutputCap: clamps maxOutputTokens by catalog cap)
fetch() upstream Google Cloud Code endpoint
```

---

## 2. Thinking Budget Determination Rules

When a client sends a standard chat completion request with **no explicit** `reasoning_effort` or `thinking` block:

### Logic in `openai-to-gemini.ts` (lines 283–301):
```typescript
if (!result.generationConfig.thinkingConfig) {
  const modelLower = model.toLowerCase();
  if (
    modelLower.includes("gemini") &&
    !modelLower.includes("gemini-1") &&
    (!modelLower.includes("gemini-2.0") || modelLower.includes("thinking")) &&
    getModelSpec(model)?.thinkingBudgetCap !== 0
  ) {
    result.generationConfig.thinkingConfig = {
      thinkingBudget: getDefaultThinkingBudget(model) || capThinkingBudget(model, 24576),
      includeThoughts: true,
    };
  }
}
```

### Resolution by Model:

| Model ID Requested | `getDefaultThinkingBudget(model)` | Fallback `capThinkingBudget(model, 24576)` | Sent `thinkingBudget` | Upstream Alias Target |
| :--- | :--- | :--- | :--- | :--- |
| `gemini-3.7-flash-high` | **24576** (from `modelSpecs.ts`) | *(not reached)* | **24,576** (HIGH) | `gemini-3.7-flash-tiered` |
| `gemini-3.7-flash-medium` | **8192** (from `modelSpecs.ts`) | *(not reached)* | **8,192** (MED) | `gemini-3.7-flash-tiered` |
| `gemini-3.7-flash-low` | **1024** (from `modelSpecs.ts`) | *(not reached)* | **1,024** (LOW) | `gemini-3.7-flash-tiered` |
| `gemini-3.7-flash-tiered` | **8192** (from `modelSpecs.ts`) | *(not reached)* | **8,192** (MED) | `gemini-3.7-flash-tiered` |
| `gemini-3.8-flash-tiered` | **0** (unregistered in `modelSpecs`) | `Math.min(24576, 32768) = 24576` | **24,576** (HIGH) | `gemini-3.8-flash-tiered` |
| `gemini-3.8-flash-high` | **0** (unregistered in `modelSpecs`) | `Math.min(24576, 32768) = 24576` | **24,576** (HIGH) | `gemini-3.8-flash-high` |

**Key findings:**
1. **Gemini 3.7 Flash High:** Truly ran reasoning High (24,576 tokens). The upstream endpoint accepts `gemini-3.7-flash-tiered` with `thinkingConfig.thinkingBudget = 24576`.
2. **Gemini 3.8 Flash Tiered:** Automatically defaults to High (24,576 tokens) because `getDefaultThinkingBudget` returning 0 triggers `capThinkingBudget(model, 24576)` which resolves against `GEMINI_FALLBACK_THINKING_CAP = 32768`.

---

## 3. Output Token Ceiling & Cap Interaction

In `open-sse/executors/antigravity.ts` (`applyAntigravityGenerationDefaults`):
```typescript
if (Number.isFinite(thinkingBudget) && thinkingBudget > 0 &&
    (!Number.isFinite(maxOutputTokens) || maxOutputTokens <= thinkingBudget)) {
  generationConfig.maxOutputTokens = Math.floor(thinkingBudget) + 1; // 24577
}
const cap = resolveAntigravityOutputCap(modelId);
if (Number.isFinite(finalMax) && finalMax > cap) {
  generationConfig.maxOutputTokens = cap;
}
```

In `open-sse/executors/antigravityOutputCap.ts`:
- Known models in `ANTIGRAVITY_PUBLIC_MODELS` (e.g. `gemini-3.7-flash-high`, `gemini-3.7-flash-tiered`): cap is `65536`.
- Unregistered models (e.g. `gemini-3.8-flash-tiered`): fallback cap is `MAX_ANTIGRAVITY_OUTPUT_TOKENS = 16384`.
- **Effect on 3.8:** `thinkingBudget` remains **24,576**, but `maxOutputTokens` is capped at **16,384** (safe for standard reasoning and completions).

---

## 4. How to Fully Register New Tiers (e.g. 3.8) in OmniRoute

To grant `gemini-3.8-flash-high` and `gemini-3.8-flash-tiered` full 65,536 token output caps:

1. **`src/shared/constants/modelSpecs.ts`:**
   ```typescript
   "gemini-3.8-flash-high": {
     maxOutputTokens: 65536,
     contextWindow: 1048576,
     defaultThinkingBudget: 24576,
     thinkingBudgetCap: 24576,
     supportsThinking: true,
     supportsTools: true,
     supportsVision: true,
   },
   "gemini-3.8-flash-tiered": {
     maxOutputTokens: 65536,
     contextWindow: 1048576,
     defaultThinkingBudget: 24576,
     thinkingBudgetCap: 24576,
     supportsThinking: true,
     supportsTools: true,
     supportsVision: true,
   }
   ```

2. **`open-sse/config/antigravityModelAliases.ts`:**
   - Add `"gemini-3.8-flash-high": "gemini-3.8-flash-tiered"` to `ANTIGRAVITY_MODEL_ALIASES`.
   - Add model definitions to `ANTIGRAVITY_PUBLIC_MODELS`.

---

## 5. Live Reasoning Verification Methodology

Google Antigravity exposes reasoning tokens via SSE streaming:
- **`choices[0].delta.reasoning_content`:** Streamed from parts marked with `thought: true`.
- **`usage.completion_tokens_details.reasoning_tokens`:** Extracted from Google's `usageMetadata.thoughtsTokenCount`.
- **Non-streaming:** Note that non-streaming OpenAI responses fold thoughts into `total_tokens` where `hidden_thoughts = total_tokens - (prompt_tokens + completion_tokens)`. SSE streaming is preferred for direct verification.

### Empirical Scaling Validation (Port 20129):
- **Budget 1,024 (Low):** ~4.8s elapsed, 0 reasoning tokens (exhausted by quick answer).
- **Budget 8,192 (Med):** ~13.5s elapsed, 2,949 reasoning tokens (1,683 reasoning chars).
- **Budget 24,576 / Default 3.7 & 3.8 (High):** ~21s–30s elapsed, 5,600–8,500 reasoning tokens (4,000–5,700 reasoning chars).
