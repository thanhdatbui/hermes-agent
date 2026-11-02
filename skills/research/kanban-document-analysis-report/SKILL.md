---
name: kanban-document-analysis-report
description: Analyze documents and produce auditable reports.
---
# Kanban Document Analysis Report Skill

Use a durable Kanban workflow to extract, compare, and explain information from documents before producing a report. Preserve source locations, extraction quality, assumptions, and unresolved questions so the report can be reviewed without trusting unsupported summaries.

## When to Use

Use for contracts, policies, invoices, meeting packs, technical specifications, research papers, scanned files, and multi-document briefs that require cited findings, risk analysis, or a decision-ready report.

## Prerequisites

- Confirm the document set, intended audience, question to answer, and requested output format.
- Confirm access permissions and treat confidential content as restricted.
- Identify whether files are text-native, scanned/OCR, tabular, or mixed media.
- Do not alter source documents, upload private material to an unapproved service, or infer legal/financial advice beyond the evidence.

## How to Run

Create a root task with `workflow_template_id="document-analysis-report-v1"` and `current_step_key="classifier"`. The classifier defines the evidence schema and creates parallel extraction, cross-document, and risk workers. A reviewer checks citations and contradictions; a synthesizer/final auditor writes the report from the workflow report.

## Quick Reference

- `kanban_create`: create the root and role tasks with durable workflow fields.
- `kanban_link`: enforce extraction-before-review and review-before-synthesis dependencies.
- `kanban_comment`: store page/section/table citations, extracted facts, confidence, and artifact references.
- `kanban_complete`: finish a lane only after its evidence is traceable to a source location.
- `kanban_block`: record unreadable pages, missing attachments, access restrictions, or unresolved ambiguity.
- `read_file`: inspect text and structured source content through the normal Hermes file surface; use the relevant document skill for format-specific extraction.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
