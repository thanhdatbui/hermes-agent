---
name: kanban-product-price-comparison-vn
description: Compare products and landed costs across Vietnam and China.
---

# Kanban Product Price Comparison Skill

Use a durable Kanban workflow to compare equivalent products, supplier offers, and landed costs between Vietnam and China. Separate observed prices from estimates, preserve source timestamps and assumptions, and make the recommendation auditable.

## When to Use

Use when a user asks whether to buy, source, import, or resell a product across Vietnam and China, including marketplace comparisons, supplier shortlists, landed-cost estimates, and price-versus-feature decisions.

## Prerequisites

- Confirm the product identity, required variant/specification, destination in Vietnam, quantity, currency, and decision deadline.
- Confirm whether the user wants retail purchase, wholesale sourcing, or resale economics.
- Set a maximum budget and risk constraints when the user provides them.
- Do not place orders, contact sellers, make payments, or claim live availability without explicit authorization.

## How to Run

Create a root task with `workflow_template_id="product-price-comparison-vn-v1"` and `current_step_key="classifier"`. The classifier fixes the comparison unit and creates parallel evidence workers for Vietnam offers, China offers, logistics/tax assumptions, and product equivalence. A reviewer checks normalization; a synthesizer/final auditor produces the recommendation from the workflow report.

## Quick Reference

- `kanban_create`: create the root and role tasks; use `current_step_key` for role identity and `workflow_template_id` for the workflow.
- `kanban_link`: enforce fan-out and fan-in dependencies.
- `kanban_comment`: store URLs, seller, SKU/variant, observed price, currency, timestamp, shipping, tax, and confidence.
- `kanban_complete`: finish a lane only when its evidence and assumptions are durable.
- `kanban_block`: record missing variant, inaccessible source, ambiguous shipping, or an approval-sensitive action.
- `web_search` and `browser_navigate`: gather public evidence when available; cite the exact source URL and access time.

## Procedure

1. Create the root task with the decision question, destination, quantity, budget, required specifications, and acceptance criteria.
2. Run the classifier. Define the canonical comparison unit (same model, capacity, bundle, warranty, and condition) and list disqualifying mismatches.
3. Create parallel workers such as `researcher:vn-retail`, `researcher:cn-supplier`, `researcher:equivalence`, and `researcher:landed-cost`. Keep workers read-only and independent.
4. For each offer, capture product identity, seller, SKU/URL, variant, condition, stock signal, base price, currency, domestic shipping, international shipping, platform fees, taxes/duties, minimum order quantity, warranty/returns, and timestamp.
5. Normalize prices into a declared currency and unit. Compute landed cost as base price plus shipping, fees, taxes/duties, and other explicitly stated costs. Keep exchange-rate source and rate date beside every conversion.
6. Distinguish facts from estimates. Use ranges for uncertain freight, tax classification, exchange rates, or seller-dependent fees; record the assumptions that drive the range.
7. Complete evidence workers only after recording source links and confidence. Block a worker when a claimed equivalence or landed-cost component cannot be verified.
8. Create a reviewer after all evidence lanes finish. The reviewer checks duplicate listings, variant mismatches, stale prices, currency errors, double-counted shipping, and unsupported tax claims.
9. Create a synthesizer/final auditor. Rank options against the user's objective (lowest landed cost, lowest risk, fastest delivery, or best value), show the calculation and uncertainty, and state what must be reconfirmed before purchase.
10. Complete the root task with the recommendation, comparison table reference, assumptions, and residual risks. Never represent an estimate as a guaranteed final price.

## Pitfalls

- Do not compare different capacities, bundles, conditions, seller warranties, or delivery terms as if they were identical.
- Do not convert currencies without recording the rate, source, and timestamp.
- Do not treat a marketplace listing price as landed cost; shipping, platform fees, duties, VAT, and brokerage may be separate.
- Do not infer customs duty or legal eligibility from a search snippet. Mark the classification as uncertain and require confirmation when material.
- Do not contact sellers, purchase goods, or publish a commercial commitment without explicit user approval.
- Do not create a second research database or workflow engine; the Kanban subtree is the durable source of truth.

## Verification

- Confirm each offer has a source URL, access timestamp, exact variant, currency, and seller identity.
- Recalculate every normalized unit price and landed-cost range from the recorded inputs.
- Confirm Vietnam and China lanes use the same comparison unit and destination assumptions.
- Confirm reviewer comments resolve or explicitly preserve contradictory evidence and uncertainty.
- Confirm the final report states observed facts, estimates, assumptions, confidence, and reconfirmation steps without credentials or raw provider metadata.
