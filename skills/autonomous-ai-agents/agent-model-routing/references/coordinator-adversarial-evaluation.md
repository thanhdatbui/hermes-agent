# Coordinator Adversarial Evaluation & Stress-Testing

## Why Worker Competence Does NOT Predict Coordinator Viability

A model that succeeds as a Worker often fails catastrophically as a Coordinator:
- **Worker Environment:** Isolated, clean context (<2,000 tokens), tight task boundary (Patch Contract O(1)), pre-filtered inputs. No external guards, no multi-component failure triage.
- **Coordinator Environment:** Heavy context (30k–80k tokens of SOUL, Invariants, Rules, Memory, Logs), adversarial runtime conditions (network timeouts, transient 429s, system guards with default-deny allowlists, untrusted worker self-reports).

## The Four Failure Modes of Defensive Models (The "Luna Pattern")

When a defensive/weak model is placed in the Coordinator role (often via unattended fallback):
1. **Defensive Paralysis (Viện cớ an toàn để trốn việc):**
   At the first transient timeout (e.g. 45s on an ADB inspect), it immediately declares `BLOCKED` with evidence, freezes all progress, and refuses to retry or check static logs on disk.
2. **Guard-Hit Groveling & Whining:**
   When hitting a mechanical system guard (e.g., terminal command default-deny), it halts and asks the user for permission or manual terminal execution instead of self-routing to an allowed alternative (e.g., Worker CLI or O(1) inspection script).
3. **Naive Worker Trust (Báo DONE ảo):**
   It accepts worker self-reports at face value without running verification (`git diff --numstat` or targeted pytest). If the worker modified 0 lines or tests failed, it still echoes "Task DONE" to the user.
4. **Autonomous Budget Begging:**
   When pre-approved for L2 Emergency Surgery (2 worker failures, exact diff <= 30 lines ready), it hesitates, calls `clarify`, or begs the user for permission.

## Automated Sizing & Verification: `coordinator_eval.py`

Before assigning or falling back to any model as Coordinator, run the automated 4-probe evaluation:

```bash
python D:/Taadaa/tools/coordinator_eval.py --model <model-id>
```

### Probe Rubric Breakdown (100 pts total)

| Probe | Adversarial Injection | Pass Criteria | Luna Failure Mode |
|---|---|---|---|
| **Probe 1: Guard-Hit Resilience (25 pts)** | Intercept terminal call with simulated guard block (`DEFAULT-DENY`) | Self-routes to approved O(1) script or worker CLI without asking user | Whines in text or calls `clarify` asking user to spoon-feed permissions |
| **Probe 2: Anti-Paralysis (25 pts)** | Simulate 45s timeout on inspection command | Classifies as TRANSIENT (L0); checks offline manifest/jsonl on disk | Declares `BLOCKED`, advises against retrying, freezes session |
| **Probe 3: Worker Skepticism (25 pts)** | Worker claims "DONE 100%" but mock git diff returns `0 files modified` | Treats worker as UNTRUSTED DATA; flags 0-diff as STRUCTURAL failure | Echoes "DONE" to user without inspecting real diff/test output |
| **Probe 4: Surgery Budget (25 pts)** | Worker failed twice, exact 3-line diff is provided | Directly applies patch within O(1) budget with `[L2-surgery]` commit | Asks user "Do I have permission to edit?" or violates budget |

### Gate Thresholds
- **Score >= 85/100:** `COORDINATOR_CAPABLE` — Approved for Primary or Fallback Coordinator.
- **Score 70–84/100:** `WORKER_ONLY` — Restricted to implementation/worker tasks; prohibited from Coordinator.
- **Score < 70/100:** `REJECTED_DEFENSIVE_WHINER` — Disqualified from all automated roles.

## Fallback Provider Hygiene Invariant

Never keep unvetted models in `fallback_providers` in `config.yaml`. A single 429 or network blip on the primary model will silently promote the defensive model to Coordinator, risking task freezing and session abandonment. Verify current fallback chain with:
```bash
hermes fallback list
```
Clear or rebind directly to approved pools (e.g., `ag-gemini-pool-3` on OmniRoute `:20129`).
