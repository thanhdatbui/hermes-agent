# Model-comparison evidence bank: Terra vs Opus research pattern

## Session-derived lessons

- The user clarified that “Terra” referred to **GPT-5.6 Terra**, not an unknown router alias. The correct response pattern is to acknowledge the correction, verify the official model documentation, and then revisit the comparison.
- Official ChatGPT model documentation described **5.6 Terra** as a balanced GPT-5.6 model with performance “competitive with GPT-5.5 at a lower cost.” This is provider positioning, not a Terra-vs-Opus head-to-head benchmark.
- The same documentation described **5.6 Sol** as the flagship model and **5.6 Luna** as the fast/affordable tier. Do not treat Terra as the flagship merely because it shares the GPT-5.6 family label.
- Anthropic’s Opus 4.8 announcement and system card provided provider-reported benchmark tables and configuration notes. The published comparison included Opus 4.8 and GPT-5.5, not GPT-5.6 Terra. Example reported rows included SWE-bench Verified, SWE-bench Pro, Terminal-Bench 2.1, OSWorld-Verified, GPQA Diamond, and other evaluations.
- A nearby-model comparison can support a directional statement such as “Terra is positioned in the GPT-5.5 class,” but it cannot support “Terra equals Opus 4.8” unless Terra-specific, comparable scores are available.

## Source-quality rules

1. Treat search snippets as discovery only; open the source page or download the system card.
2. Preserve exact URLs and cite the official model documentation/system card.
3. For each score capture benchmark version, harness, tools, effort/reasoning setting, token/time budget, sample count, and provider/independent provenance.
4. Do not combine scores from incompatible harnesses into a single average or ranking.
5. If no target-specific public score is found after targeted searches, report “no public score located” rather than filling the cell with a sibling model’s score.

## Worked comparison structure

| Layer | Terra evidence | Opus evidence | Interpretation |
|---|---|---|---|
| Identity | Official product tier: GPT-5.6 Terra | Official Anthropic model: Claude Opus 4.8 | Verified identities, different providers |
| Provider positioning | Competitive with GPT-5.5, lower cost | Flagship/Opus tier with published capability evaluations | Positioning is not equivalence |
| Exact public benchmark | Terra-specific scores must be located; do not assume GPT-5.5 scores | Opus 4.8 system card has reported scores | Evidence is asymmetric |
| Bottom line | Likely GPT-5.5-class balanced tier, confidence limited for Terra-vs-Opus | Stronger published evidence for long-horizon coding/agent capability | Do not claim parity without a matched eval |

## Caveat

This file records the research method and evidence pattern, not a permanent ranking. Model names, versions, benchmark results, and official documentation change; re-fetch the sources for every new comparison.
