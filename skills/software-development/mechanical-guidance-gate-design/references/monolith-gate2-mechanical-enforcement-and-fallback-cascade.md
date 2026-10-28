# Monolith Gate 2 Mechanical Enforcement & Multi-Tier Fallback Safety

## 1. Problem & Architecture Overview
In autonomous agentic coding, Coordinator prompt rules (e.g. "Do not pass open goals on monoliths >1,500 lines") are soft constraints. Coordinators frequently violate soft rules under time pressure, passing vague prompts to one-shot workers (like Qoder DeepSeek-Flash).
This triggers:
1. `NO_DIFF` from the Tier 1 Worker due to context overload.
2. Unnecessary cascades through fallback tiers (Sol -> Agy -> Haiku), burning API quota and stalling the farm queue.
3. Both workers and fallback tiers failing on the same ungrounded prompt.

## 2. Mechanical Gate 2 Enforcement Rules

### Rule 1: Mechanical Gate Placement (Single Checkpoint)
Place the Gate check in `dispatch_worker.py` immediately at the start of `main()`, before spawning any worker tier.
Never rely solely on prompt instructions.

### Rule 2: Grounding & Monolith Detection (O(1) Pre-flight)
- Threshold: Any target file > 1,500 lines (`sum(1 for _ in f) > 1500`).
- Detection scope: Target file passed via `--file` OR parsed from prompt via path regex `r"[\w:./\\-]+\.(?:py|js|ts|tsx|ps1)\b"`.
- Banned verbs on monoliths: Regex `r"refactor|rewrite|audit|clean ?up|toàn bộ|whole file|tối ưu|review file"`.

### Rule 3: Anchor Symbol Validation (Span Constraint)
For any monolith target:
- Must define an anchor symbol (function or class name).
- Must have exactly 1 occurrence in the target file (`len(hits) == 1`).
- Target function/symbol span must be <= 150 lines.

### Rule 4: Terminal Exit Code 3 (No Fallback Cascade)
- If Gate 2 is violated: Exit with code `3` (`GATE_VIOLATION`), NOT `1` (`TASK_FAIL`).
- **Hard Rule**: Exit code 3 MUST NOT trigger fallback to Tier 2 (Sol) or Tier 3 (Agy/Haiku). If the prompt is structurally broken, falling back is pure waste.
- Output actionable JSON hint so Coordinator can extract the exact function and re-dispatch with focused anchor.

### Rule 5: Benchmark & Worker Floor Timeouts
- Benchmark or worker invocations MUST enforce floor timeout >= 480s (same as standard production workers).
- Never truncate timeouts during testing or benchmarks to avoid false-positive timeout failures.
