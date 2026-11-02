---
name: model-comparison-research
description: "Research and compare AI model identities, benchmark evidence, provider claims, and reseller/router aliases without conflating marketing claims with head-to-head results."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [Research, benchmarks, model identity, citations, fact checking]
    category: research
    related_skills: [grounded-citations]
---
# Model Comparison Research

## Trigger

Use when a user asks whether two AI models are equivalent, requests benchmark-based comparison, challenges a model name/alias, or wants a marketing claim checked against public evidence.

## Core workflow

1. **Lock the identity first.** Determine the exact provider, product family, public model name, API model ID/snapshot, and whether the label comes from an official provider page, a router, a reseller, or a UI. If the user corrects the identity, acknowledge the correction and re-check the authoritative model page before continuing.
2. **Separate claim types.** Classify each statement as exact model identity, provider positioning, reseller marketing, independent benchmark result, or inference from a related model. Never silently promote “competitive with,” “similar to,” or “as smart as” into equivalence.
3. **Collect primary evidence.** Prefer official model pages, model cards/system cards, benchmark papers, and transparent leaderboards. Search snippets are discovery hints only; inspect the underlying page before citing a score or capability claim.
4. **Find exact-match evidence.** Search for the target model name plus benchmark names. If no public score exists for the target model, state that plainly. Do not substitute scores from a sibling model without labeling them as proxy evidence.
5. **Normalize evaluation conditions.** For every score, record benchmark version, harness, tools, reasoning/effort setting, token/time budget, sample count, date/snapshot, and whether it is provider-reported or independent. Mark rows non-equivalent when important conditions differ.
6. **Compare by capability slice.** Separate coding/agent work, terminal use, computer use, science/reasoning, mathematics, and everyday knowledge work. Avoid collapsing all scores into one unsupported overall ranking.
7. **Write the answer in four parts:** verified identity; exact published scores; indirect/proxy evidence; bottom-line judgment and confidence. Keep the conclusion concise when the user asks for a direct answer, while preserving the key caveat.
8. **Cite while drafting and verify citations** using the grounded-citations workflow when that skill is available. Cite the primary page or system card, not a search snippet.

## Evidence labels

- **Same model:** exact provider model ID/snapshot and comparable evaluation configuration.
- **Provider-positioned peer:** provider says it competes with another model but publishes no same-benchmark score.
- **Proxy comparison:** evidence from a predecessor, sibling, or nearby tier; useful context but not proof about the target.
- **Independent head-to-head:** same task set, benchmark version, harness, tool access, and effort setting.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
