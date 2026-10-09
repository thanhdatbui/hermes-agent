# Vision structured-document capture

Use this reference when a multi-page scanned document must become a selectable-text
artifact and the model output must remain auditable.

## Proven capture pattern

1. Call the local OpenAI-compatible 9Router Vision endpoint (`127.0.0.1:20128/v1/chat/completions`)
   with the API key resolved by the repository's `get_ninerouter_api_key()` helper.
2. Send each page image independently. Require a JSON array of detected blocks with
   `box_2d: [ymin, xmin, ymax, xmax]` in the model's 0..1000 coordinate system,
   `source`, `translation`, and optional `bold`/`align`.
3. Capture the parsed response before any raster drawing. A practical integration
   technique is to wrap/replace the renderer's drawing callback so the existing
   Vision request and parser are exercised while the normalized blocks are persisted
   to JSON.
4. Convert each normalized box to image pixels using the actual page width/height,
   then convert once more to PDF points at the rendering boundary. Do not mix image
   pixels and PDF points in the same JSON without an explicit `coordinate_space`.
5. Persist the contract shape:
   `{"pages": [{"page": N, "blocks": [{"source": ..., "translation": ..., "rect": [x,y,w,h], "fontsize": ..., "bold": ..., "align": ...}]}]}`.

## Mechanical acceptance checks

- Page keys are exactly the required set (for the PCCC job: 1..18).
- Every page has a non-empty block list; every block has a non-empty translation and
  a four-number rectangle.
- Report per-page block counts and total blocks from the file actually written.
- Check required terminology and model identifiers against the persisted translations;
  do not infer that Vision used the glossary merely because the prompt mentioned it.
- Use a fail-closed renderer: incomplete JSON keeps draft labels and
  `DRAFT_NEEDS_REVIEW`; complete JSON is the only condition that can suppress them.
- After rendering, open the produced PDF independently and verify page count,
  `page.get_text()` contains representative translations, and previews exist for
  the first, middle, and final pages.

## Pitfalls

- A renderer that only accepts `text` will silently ignore a valid `translation`
  schema; normalize the field explicitly at load time.
- Supporting only a flat `{page: blocks}` mapping will treat a valid nested
  `{"pages": [...]}` document as empty.
- A successful Vision response is not proof of full coverage. Empty/malformed pages,
  missing glossary terms, stale JSON, or raster-only output must remain blocked.
- Avoid opaque white-out when the contract says to preserve the scan. Add vector text
  without claiming that a draft overlay is a finished translation.
