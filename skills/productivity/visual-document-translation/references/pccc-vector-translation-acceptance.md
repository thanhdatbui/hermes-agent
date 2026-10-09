# PCCC vector-translation acceptance checklist

Use this checklist before calling a translated scanned test report or certificate complete.

## Artifact classification

- `DRAFT_NEEDS_REVIEW`: the original scan is retained and only labels/glossary/model notes or partial blocks were added; this is not a finished translation.
- `VECTOR_TRANSLATION_READY`: every page has structured translation blocks and the renderer consumed them; this still requires visual review of representative pages.
- `DONE`: only after content validation and visual evidence pass. File existence, selectable text, or a worker self-report alone is insufficient.

## Manifest checks

1. Manifest schema contains `pages`, with page numbers 1 through 18 exactly once.
2. Every page has at least one non-empty block containing `source`, `translation`, `rect`, and typography metadata.
3. Renderer output text is checked with PyMuPDF and the preview images are inspected directly.
4. Confirm the original Chinese is not still the primary readable text in translated regions. A PDF with an unchanged scan plus a few vector notes is not a translation.

## PCCC glossary checks

- `℃` must be rendered as `°C` (degree sign plus ASCII C).
- `溅水盘` → `Tấm tán nước`.
- `动作元件` → `Phần tử kích hoạt`.
- `型式试验` → `Thử nghiệm kiểu loại`.
- `认证单元` → `Nhóm chứng nhận`.
- `出水口口径` → `Đường kính lỗ phun`.
- `街道` in the address → `phường`, e.g. `phường Khê Mỹ`.
- Canonical company name: `Công ty TNHH Phòng cháy chữa cháy Thiên Thái Phúc Kiến`.

## Critical certificate check

Page 18 must contain all ten certified models, with no substitution or omission:

`115-93, 115-107, 115-121, 115-141, 115-163, 115-182, 115-204, 115-227, 115-260, 115-343`.

A wrong model list is a blocking content error even if every other page looks good.

## Visual review set

Always inspect at minimum:

- page 1: cover/title, company and issuing-body names;
- page 8: dense inspection table and line wrapping;
- page 18: certificate model list, seal/QR preservation, and degree symbols.

Reject output if white rectangles erase table rules or paper texture, if text shrinks to illegibility, if Chinese remains over translated regions, or if the output is described as complete while marked draft.
