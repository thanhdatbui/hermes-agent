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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
