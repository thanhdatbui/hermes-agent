# Mechanical Gate 2: Monolith Anchor & Broad Verb Enforcement in Dispatch Worker

## Context & Problem
Coordinator often violated GATE 2 by sending broad/open-ended fix prompts ("refactor", "toàn bộ", "clean up") against monolith files (> 1,500 lines) like `run_post.py`. 
Because prompts were unanchored:
1. Fast one-shot workers (e.g. Qoder DeepSeek-Flash) feared breaking complex monolithic context and returned `NO_DIFF` (unchanged files).
2. The dispatch gateway automatically fell back to Sol Worker (`sol_worker.py`), which got stuck reading thousands of lines across turns and eventually gave `NEEDS_INPUT`.
3. Cascade failures burned time and quota across all tiers (Qoder -> Sol -> Agy -> Haiku).
Text-based prompt instructions ("do not violate Gate 2") failed because prompt guidelines are soft; mechanical enforcement in code was required.

## Mechanical Solution Architecture (`dispatch_worker.py`)
Directly inside `dispatch_worker.py` at the very beginning of `main()` (pre-dispatch):
1. **Target File Discovery**: Resolve target paths from `--file` and scan prompt strings for regex `[\w:./\\-]+\.(?:py|js|ts|tsx|ps1)\b`.
2. **Line Threshold (> 1500 lines)**:
   - Check if any target file exceeds 1,500 lines.
   - If threshold exceeded:
     a. **Broad Verb Rejection**: Reject immediately if prompt contains broad action verbs (`refactor`, `rewrite`, `audit`, `clean up`, `toàn bộ`, `whole file`, `tối ưu`, `review file`).
     b. **Required Anchor Symbol**: Must provide `--anchor <file>::<symbol>` or explicitly declare `def <symbol>` / `class <symbol>` in prompt.
     c. **Exact Uniqueness**: Anchor symbol must match exactly 1 occurrence in the monolith file (`len(hits) == 1`).
     d. **Span Ceiling (O(1))**: The function/class scope must not exceed 150 lines (`span <= 150`).
3. **Dedicated Failure Exit Code (`exit(3)` - RC_GATE_BLOCKED)**:
   - Exit immediately with exit code 3.
   - **Crucial Rule: NO FALLBACK on exit 3**. Do not roll over to Sol, Agy, or Haiku. A flawed prompt must be blocked and corrected by the caller rather than retried on downstream workers.
   - Output structured JSON hint detailing exact reason (`BROAD_VERB`, `NO_ANCHOR`, `AMBIGUOUS_ANCHOR`, `SPAN_TOO_BIG`) so Coordinator can immediately inspect and provide the exact symbol.

## Benchmark & Operational Rules
- **Timeout Flooring**: Never set benchmark or worker timeout under 480s (8 minutes) for LLM coding jobs. Short artificial timeouts cause false-positive failures.
- **Worker Hierarchy**: Qoder (DeepSeek-Flash) serves as primary free worker for bounded O(1) patches until promo expiry, automatically backed by Sol Worker for multi-turn file inspection.
