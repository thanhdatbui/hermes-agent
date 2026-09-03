# OmniRoute Model Catalog Update Pattern

Session: 2026-09-03 — Added Muse Spark 1.3 to omni-free combo Tier 1

## Trigger
New model available upstream (opencode.ai/zen) that needs to be exposed in OmniRoute and promoted in a free-tier combo.

## Files to Update

### 1. Provider Registry (opencode + zen)
```typescript
// open-sse/config/providers/registry/opencode/index.ts
{
  id: "muse-spark-1.3",
  name: "Muse Spark 1.3",
  supportsReasoning: true,
  targetFormat: "openai-responses",
},
{
  id: "muse-spark-1.3-contributor-free",
  name: "Muse Spark 1.3 Contributor Free",
  supportsReasoning: true,
  targetFormat: "openai-responses",
},

// open-sse/config/providers/registry/opencode/zen/index.ts
// Same entries + comment about wire-format overlay
```

### 2. Executor Effort Tiers
```typescript
// open-sse/executors/opencode.ts
const EFFORT_TIERS = {
  "muse-spark-1.2-contributor": ["minimal", "low", "medium", "high", "xhigh"],
  "muse-spark-1.3-contributor": ["minimal", "low", "medium", "high", "xhigh"], // ADD
  // ... other models
};
```

### 3. Update Combo via API
```bash
# GET current combo
curl http://127.0.0.1:20129/api/combos/5a72c9bc-94d8-4e35-a9c6-51545cb73d7a

# PUT updated models array (reorder with new model at Tier 1)
curl -X PUT http://127.0.0.1:20129/api/combos/5a72c9bc-94d8-4e35-a9c6-51545cb73d7a \
  -H "Content-Type: application/json" \
  -d '{"models": [...], "description": "..."}'
```

### 4. Build & Restart Verification
```bash
cd /c/Users/Kibe/OmniRoute
npm run typecheck:core
npm run build
taskkill -F -PID <omniroute-pid>
node scripts/dev/run-next.mjs start &
# wait for /api/health status: ok
curl -s http://127.0.0.1:20129/v1/models | jq '.data[] | select(.id | contains("muse"))'
# Test combo routing
curl -X POST http://127.0.0.1:20129/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "omni-free", "messages": [{"role": "user", "content": "test"}], "max_tokens": 50}'
```

## Key Discovery
- `muse-spark-1.3-contributor-free` already existed in upstream (opencode.ai/zen/v1/models) but was not declared in OmniRoute registry
- Must declare in BOTH opencode (base) AND opencode-zen (separate registry for same upstream) with `targetFormat: "openai-responses"` — otherwise upstream returns empty content
- Effort tiers in executor must match for `*-contributor` variants (minimal/low/medium/high/xhigh)
- Combo `omni-free` uses priority strategy → first model in array = Tier 1

## Verification Checklist
- [ ] `npm run typecheck:core` passes
- [ ] `npm run build` succeeds (Turbopack)
- [ ] OmniRoute restarts, `/api/health` → status: ok
- [ ] `v1/models` shows new `oc/muse-spark-1.3*` entries
- [ ] Combo API returns updated model order
- [ ] Live chat completion routes to new model (check `model` field in response)