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

## Procedure

1. Create the root task with the question, document inventory, audience, deadline, confidentiality boundary, and report acceptance criteria.
2. Run the classifier. Assign stable document IDs and define the claim schema: source, location, quote/data, interpretation, confidence, and uncertainty.
3. Create parallel workers such as `researcher:extract`, `researcher:tables`, `researcher:cross-document`, and `researcher:risk`. Keep extraction workers read-only.
4. Extract facts without silently correcting them. Record page, section, paragraph, table, or timestamp locations; preserve units, dates, names, and qualifiers exactly.
5. Mark OCR or parsing uncertainty explicitly. Distinguish text directly observed in a source from an interpretation, calculation, or missing-data assumption.
6. For multiple documents, reconcile terminology, versions, dates, and duplicated claims. Record contradictions as separate evidence rather than choosing the convenient value.
7. Complete workers only when their findings include source locations, confidence, and artifact references where applicable. Block when a required page or attachment is inaccessible.
8. Create a reviewer after extraction. The reviewer checks citation coverage, arithmetic, version scope, privacy handling, unsupported conclusions, and contradiction treatment.
9. Create a synthesizer/final auditor. Organize the report around the user's question, include an executive conclusion, evidence table, assumptions, risks, open questions, and recommended next checks.
10. Complete the root task with the report reference and a concise result. Keep sensitive source text out of broad comments when a citation or restricted artifact reference is sufficient.

## Pitfalls

- Do not cite only a document title when a page, section, table, or timestamp is available.
- Do not treat OCR output as authoritative when scans are blurry, rotated, handwritten, or incomplete.
- Do not merge values from different document versions without stating the version and precedence rule.
- Do not turn an interpretation into a quoted fact or conceal missing attachments behind a confident summary.
- Do not expose confidential document contents in task titles, public comments, logs, or final output beyond the user's scope.
- Do not create a second document database or workflow engine; the Kanban subtree and approved artifacts are the durable record.

## Verification

- Confirm every material finding maps to a source location and document version.
- Recalculate derived values from recorded inputs and label estimates separately from observations.
- Confirm reviewer coverage for contradictions, OCR quality, privacy, and unresolved questions.
- Confirm the final report answers the requested question, states confidence and limitations, and identifies next checks.
- Confirm no credentials, unnecessary personal data, or raw provider metadata are included in comments or the report.
