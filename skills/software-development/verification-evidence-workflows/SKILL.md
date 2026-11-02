---
name: verification-evidence-workflows
description: "How to produce fresh, isolated verification evidence after code edits — ad-hoc temp-script verification when a harness reports 'unverified', and edit-hygiene pitfalls for large modules under TDD."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [verification, testing, tdd, evidence, edit-hygiene]
    related_skills: [test-driven-development, systematic-debugging]
---
# Verification Evidence Workflows

## When this applies

- A host/harness re-scans after each edit and posts `Verification status: unverified`
  because no canonical test/lint/build command was detected in-band.
- You have finished a TDD cycle (RED→GREEN→verify) but the harness still wants
  proof the changed behavior actually runs.
- You are editing a large implementation module (hundreds of lines) with several
  structural changes and `patch` calls start colliding.
- A vision/OCR service produces structured blocks that must be rendered into a
  selectable-text artifact; use the same fail-closed completeness and fresh-artifact
  gates before claiming the document is final.

### Structured vision-document artifact gate

For multi-page vision translation or OCR pipelines, treat the model response as
source data, not as a finished artifact. Persist one machine-readable record per
page with `page`, `source`, `translation`, `rect`, `fontsize`, `bold`, and `align`;
reject missing pages, empty block lists, malformed rectangles, or missing translations
before rendering. If the schema is nested (for example `{"pages": [...]}`), make the
loader explicitly support that shape and test it against the live JSON rather than
assuming the older flat mapping shape.

When the vision API returns normalized image coordinates, convert them exactly once
at the render boundary into the target PDF coordinate system, scaling both rectangles
and font sizes from the captured image dimensions. Preserve source scan pixels and
add selectable vector text without opaque white-out unless replacement is explicitly
required. A valid schema alone does not prove coverage: report page/block counts and
spot-check required terminology and model identifiers from the persisted JSON.

Keep the draft state fail-closed: emit draft labels and `DRAFT_NEEDS_REVIEW` whenever
any page/block validation fails, and suppress those labels only after all 18 pages (or
the contract's full page set) pass validation. Run the focused compile check and a
fresh render, then verify page count, selectable text extraction, and representative
previews from the first, middle, and last pages. The concrete 9Router/Vision capture
pattern is documented in `references/vision-structured-document-capture.md`.

This is the *evidence* layer on top of TDD. TDD proves the test catches the bug;
this skill proves the edit is live-verified and the file is coherent.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
