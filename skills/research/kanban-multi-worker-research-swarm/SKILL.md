---
name: kanban-multi-worker-research-swarm
description: Coordinate parallel researchers into audited synthesis.
---

# Kanban Multi-Worker Research Swarm Skill

Use a bounded Kanban swarm to investigate a broad question through independent evidence lanes and produce one audited synthesis. Preserve each worker's scope, sources, uncertainty, contradictions, and handoffs so parallelism improves coverage instead of multiplying unsupported summaries.

## When to Use

Use for broad market, policy, technical, scientific, competitive, or due-diligence questions where independent research lanes can verify different claims or challenge one another before synthesis.

## Prerequisites

- Confirm the research question, decision audience, deadline, evidence standard, and allowed sources.
- Set a bounded worker count, task budget, and stopping condition before fan-out.
- Define confidentiality and authorization boundaries for external sources or private files.
- Do not contact third parties, purchase data, or perform consequential actions without explicit approval.

## How to Run

Create a root task with `workflow_template_id="multi-worker-research-swarm-v1"` and `current_step_key="classifier"`. The classifier decomposes the question into non-overlapping claims, creates bounded parallel researchers, and reserves reviewer/challenger and synthesizer/final-auditor stages. Use the workflow report as the normalized final evidence projection.

## Quick Reference

- `kanban_create`: create the root, evidence workers, challenger, reviewer, and final auditor with durable role steps.
- `kanban_link`: encode fan-out, cross-check, and fan-in dependencies.
- `kanban_comment`: record source citations, commands, claim status, confidence, uncertainty, and artifact references.
- `kanban_complete`: finish a lane only when its assigned claims have durable evidence or explicit negative findings.
- `kanban_block`: stop a lane when access, scope, budget, or evidence quality prevents a trustworthy conclusion.
- `web_search`, `browser_navigate`, and `read_file`: gather permitted public or local evidence while retaining exact provenance.

## Procedure

1. Create the root task with the question, scope, audience, deliverable, budget ceiling, worker limit, and acceptance criteria.
2. Run the classifier. Break the question into a claim matrix with stable claim IDs, required evidence, exclusions, and dependencies. Avoid assigning the same open-ended scope to every worker.
3. Create bounded lanes such as `researcher:primary`, `researcher:counterevidence`, `researcher:data`, and domain-specific researchers. Give each lane explicit claim IDs and a source-diversity requirement.
4. Require workers to record exact citations, source dates, observed facts, interpretations, confidence, uncertainty, failed searches, and artifact references. A negative finding must include what was searched and where.
5. Keep workers independent until their evidence is durable. Do not let later workers merely repeat an earlier summary without checking the underlying source.
6. Create a challenger after primary evidence lanes finish. The challenger searches for counterexamples, stale assumptions, source dependence, missing populations, and alternative explanations.
7. Create a reviewer after the challenger. The reviewer maps evidence to claim IDs, detects duplicate sources, resolves or preserves contradictions, and requests only targeted follow-up tasks within the remaining worker/budget bound.
8. Stop fan-out when acceptance criteria are met, marginal evidence is low, the budget is exhausted, or unresolved gaps require user input. Do not create workers indefinitely to chase certainty.
9. Create a synthesizer/final auditor. Produce a claim-by-claim conclusion with supporting and opposing evidence, confidence, limitations, and decision implications. Separate consensus from majority repetition.
10. Complete the root task with the normalized workflow report reference, concise recommendation, residual risks, and the evidence needed to revisit uncertain claims.

## Pitfalls

- Do not use worker count as a proxy for independent evidence; several workers citing one source are one evidence lineage.
- Do not create overlapping prompts that produce duplicate summaries and inflate apparent confidence.
- Do not average incompatible claims or hide contradictions in a smooth narrative.
- Do not reopen completed scope without a concrete evidence gap and remaining budget.
- Do not expose confidential inputs, credentials, or raw provider metadata in durable comments or reports.
- Do not create a second swarm engine or research database; use Kanban tasks, links, comments, runs, events, and the workflow report.

## Verification

- Confirm every worker has explicit claim IDs, non-overlapping scope, and a terminal status.
- Confirm material claims include source provenance, date, confidence, uncertainty, and counterevidence where available.
- Confirm the reviewer detects duplicate evidence lineages and addresses contradictions before synthesis.
- Confirm worker count, follow-up rounds, and spend remain within the declared bounds.
- Confirm the final report distinguishes facts, interpretations, consensus, disagreement, limitations, and unresolved questions.
