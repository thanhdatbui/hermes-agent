# Reset-Aware Runtime Ordering vs Static DB Order

## Core Finding (2026-09-11)

**`reset-aware` strategy DOES reorder targets at runtime per-request** - it fetches live quota snapshots and sorts by remaining quota before dispatch. However, this is **ephemeral runtime behavior only** - the static order in `combos.data.models` array remains unchanged.

### Why Static Order Still Matters

Even with `reset-aware` runtime reordering, the static DB order controls several critical mechanisms:

| Mechanism | Uses | Impact of Bad Static Order |
|-----------|------|----------------------------|
| **Session Stickiness** | `executionKey` from static order | Pin can land on exhausted account at position #3 even if runtime puts it at #50 |
| **LKGP (Last Known Good Provider)** | `executionKey` from static order | Records success against wrong executionKey if static order ≠ runtime winner |
| **Prompt Cache Affinity (global scope)** | `executionKey` for rendezvous hashing | Hash distributes based on static position, not runtime quota rank |
| **Pre-screen cache** | `target.executionKey` from static order | May fetch quota for wrong connection if static order diverges |
| **Decision Trace / Debug** | `comboStepId` = `executionKey` | Logs show static position, hard to correlate with actual quota state |

## Evidence from Session

**Pool: `ag-gemini-pool-3` (strategy=reset-aware, 63 targets)**
- Static order: Exhausted accounts at positions #3, #7, #12, #13, #14, #15, #17, #18
- Runtime: `jinrakal@gmail.com` (position #1, quota=100%) correctly selected for all recent requests
- BUT: 8 concurrent workers quickly saturated concurrency cap (2/acc) on top accounts → spill to `omni-free` before runtime ordering could reach healthy accounts deeper in pool

**Pool: `ag-claude` (strategy=reset-aware, 63 targets)**
- 45/63 accounts exhausted (0% quota) concentrated in first 30 positions
- Only 18 healthy accounts scattered at positions #35-#61
- `maxGlobalAttempts=80` sufficient budget, but static order causes unnecessary scan

## Recommended Practice

1. **Run physical reorder script** (`pool-reorder-script.md`) periodically to align static order with quota reality
2. **Set combo config**:
   ```json
   {
     "disableSessionStickiness": true,
     "disablePromptCacheAffinity": true
   }
   ```
3. **Reorder GRP0-4 groups**:
   - GRP0: Pro tier + live proxy
   - GRP1: Free tier + quota >= 10%
   - GRP2: Free tier + quota < 10%
   - GRP3: Standard-tier (403 candidate)
   - GRP4: Dead proxy / expired / inactive

## Related Skills
- `references/pool-reorder-and-fallback-chain.md` - Full reorder procedure
- `references/pool-reorder-script.md` - Python reorder script
- `references/session-stickiness-pool-safety.md` - Stickiness interaction with ordering
- `references/priority-combo-unrolling-and-tier-fallback.md` - Tier fallback mechanics