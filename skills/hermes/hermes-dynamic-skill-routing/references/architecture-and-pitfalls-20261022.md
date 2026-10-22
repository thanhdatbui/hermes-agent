# Dynamic Skill Routing O(1) Architecture & Remediation Pitfalls (2026-10-22)

## Context & Genesis

In October 2026, Hermes had 191 skills statically loaded into system context on every turn. This caused:
- Token bloat (~100k tokens before task begins)
- Severe context compression (`[SKILL_PRUNED]` markers) where critical procedures were lost
- Latency and cost explosion

## The 6-Part Architectural Blueprint

Claude Sonnet 5.5 Planner designed a zero-vector, pure-Python O(1) dynamic routing architecture:

1. **Indexer (`build_skill_index.py`)**: scans all `SKILL.md` frontmatters and compiles `skills_index.json` (< 0.5s)
2. **Matcher (`skill_lookup.py`)**: keyword bucket scoring + always injects 5 Core Pinned Skills
3. **Loader (`load_selected_skills.py`)**: loads only matched skills with path traversal guard (`is_relative_to(skills_root)`)
4. **Injector (`skill_injector.py`)**: thin adapter layer orchestrating lookup, sanitization, and budget clamp
5. **Gateway Wiring (`dispatch_worker.py`)**: auto-prepends skill context block to every worker prompt
6. **Preview CLI (`preview_skill_injection.py`)**: zero-side-effect verification CLI

## Sol Reviewer Scoring & Key Findings Remediated

Across the Closeout Gate review loops (scores: 72 -> 74 -> 77 -> 85):

### Finding 1: Path Traversal in Skill Loader
- **Issue**: `rel_path` could escape `skills_dir` via `../../`
- **Fix**: Use `(skills_root / rel_path).resolve()` and verify `skill_file.is_relative_to(skills_root)`

### Finding 2: HTML Comment Escape
- **Issue**: Malicious/accidental `-->` in skill files breaks delimiter blocks
- **Fix**: `safe_path = rel_path.replace("-->", "--&gt;")`

### Finding 3: Two-Level Freshness Detection
- **Issue**: Only checking category mtimes misses edits inside `category/skill_name/SKILL.md`
- **Fix**: 2-level iterdir scan comparing mtime of each `SKILL.md` directly against index mtime

### Finding 4: References Archive Bloat in Pinned Skills
- **Issue**: `session-close-protocol` and `evidence-first-delivery` have 100KB+ `## References` sections
- **Fix**: `clean_skill_content()` strips `## References` and caps each skill at 3,000 chars

### Finding 5: Safe-Boundary Truncation
- **Issue**: Hard-clamping at character count cuts mid-sentence or mid-HTML-comment
- **Fix**: Search backwards for the last `<!-- END SKILL:` marker before the budget ceiling

### Finding 6: Silent-Success Telemetry Anti-Pattern
- **Issue**: Hardcoded `rc=0` in audit call even when injection failed
- **Fix**: `_rc_inj = 0 if inj.status not in ("FAIL_CLOSED_STALE_INDEX", "FAIL_CLOSED_ERROR") else 1`

### Finding 7: Worker Hardcoded Budget Desync (Critical Bug)
- **Issue**: A worker patching `dispatch_worker.py` hardcoded `max_context_chars=2500` instead of `15000`
- **Consequence**: Decoupled budget caused matched skills to never be included while pinned skills took the entire allowance
- **Fix**: Always pass `max_context_chars=15000, max_pinned_budget=10000` explicitly

### Finding 8: Name vs Path Mismatch in Injected Skills Tracking
- **Issue**: Checking `if sid in full_context` where `sid` is the bare skill name can fail or false-positive if the name differs from directory structure
- **Fix**: Map `(name, path)` tuples and check `f": {path} -->" in full_context` to reliably detect which skills survived truncation

### Finding 9: OmniRoute vs Antigravity Shared Gemini Quota Pool
- **Insight**: `gemini-3.1-pro` and `gemini-3.8-flash` share the exact same quota pool in Antigravity / OmniRoute
- **Context**: `omni-worker` runs on this pool; checking only `gemini-3.1-flash-lite` in quota status creates a false indication of exhaustion or availability
