# PCCC translation failure lessons — 2026-10-05

## Non-negotiable acceptance

A PDF that keeps the Chinese scan and adds an invisible/selectable text layer is **not translated**. Never report it as complete. Reject any pipeline that uses `fontsize=1`, white text, or a DOCX containing only full-page source images.

Visual proof is mandatory: inspect rendered previews of the cover, a dense table, and certificate/model pages. The Chinese must no longer be the primary readable content in translated regions. If a page is unchanged or the output falls back to raw source after a Vision parse failure, mark the run BLOCKED.

## Manifest coordinate trap

The existing PCCC manifest uses `rect=[x,y,w,h]` in source-image pixel coordinates, not normalized `[ymin,xmin,ymax,xmax]`. Render with `x1=x`, `y1=y`, `x2=x+w`, `y2=y+h`. Do not reuse a renderer written for `box_2d` normalized coordinates without an explicit conversion.

## Safe page handling

For certification pages 16–18, preserve the full source page or an equivalent full-resolution region so seals and QR codes remain usable. Do not replace them with small crops. For dense tables, erase only text interiors and preserve table strokes; padding must not cut borders. Use Times New Roman and never shrink below a legible floor (8 px/pt policy agreed for the artefact).

## Anti-hallucination boundary

Terra review found the clean re-typeset draft had invented or changed report numbers, model prefixes, dates, validity, addresses, and test results. Do not synthesize technical values from a review summary. Every translated block must be traceable to source OCR/manifest evidence. Known corrections for this document include report `Gn202108154`, models `T-ZSTZ 80-68°C Q5` and `T-ZSTZ 115-68°C Q5`, certificate `Z2022081803000538`, validity `02/06/2022–01/06/2027`, and the ten `T-ZSTZ 115-<temperature>°C Q5` model entries.

## Executor routing

Terra is useful as a read-only content reviewer or a narrowly contracted executor, not as an open-ended DTP author. Give it one owned renderer file, an explicit manifest schema, exact output paths, a hard stop on missing blocks/parse failures, and a final visual check. Store the full prompt in a file with a native Windows path before launching Codex; do not rely on a shell heredoc or an uncreated prompt path.

## Delivery wording

Report `FIXED` only after independent checks show: 18 rendered pages, every page has visible translated blocks, output exists, page dimensions match, and previews visibly show Vietnamese. Otherwise report `BLOCKED` with the actual command/error. Never use a worker's self-report or file existence alone as proof.

## Independent referee review loop (Claude Sonnet 5 via CLI)

When auditing final translated technical PDFs, run an independent referee pass using Claude Code CLI:
```bash
claude -p --dangerously-skip-permissions "Bạn là reviewer độc lập. Hãy dùng Python PyMuPDF (fitz) mở và kiểm tra đối chiếu trực tiếp giữa BẢN GỐC <input.pdf> và BẢN DỊCH <output.pdf>..." --model claude-sonnet-5
```
*(Always pass `--dangerously-skip-permissions` to prevent non-interactive headless confirmation deadlocks).*

### Common review findings and required fixes:
1. **TCVN 6305 Terminology Enforcement:**
   - `溅水盘` (Deflector) must be strictly translated as **"Tấm tán nước"** (NOT "tấm định hướng").
   - `动作元件` / `热敏感元件` (Operating / thermal element) must be strictly **"Phần tử kích hoạt"** (NOT "bộ phận cảm ứng nhiệt", "cơ cấu cảm nhiệt", or "bộ phận cảm nhiệt").
2. **Page-Aware Address Trap (Communication vs Registered Address):**
   - In PCCC test reports and certificates, the company's communication address (`通讯地址` on test report pages 4, 6) often differs from the registered certificate address (`住所/企业地址` on certificate pages 16–18).
   - Global find-and-replace on addresses destroys factual accuracy. The normalization logic must be page-aware:
     * Pages 4, 6: Communication address (*Khu phát triển Thành Công*).
     * Pages 16–18: Registered certificate address (*phường Khê Mỹ*).
3. **Company Name Uniformity:** Ensure consistent usage across all pages (e.g. `Công ty TNHH PCCC Thiên Thái Phúc Kiến` instead of alternating between full and abbreviated names).
4. **Desktop App vs CLI Refusal:** If Claude Desktop app hangs on skeleton loading under `computer_use`, pivot immediately to headless `claude -p` instead of waiting on the GUI.
