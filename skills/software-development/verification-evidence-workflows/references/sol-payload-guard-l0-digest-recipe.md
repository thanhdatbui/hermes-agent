# Sol Payload Guard & L0 Digest Verification Pattern

When closeout gates evaluate candidates through Reviewer models (such as Sol High via OmniRoute `:20129`), the payload is strictly constrained by `sol_payload_guard.py` (`SOL_TARGET_BYTES = 32768`).

## 1. Budget Breakdown (`split_budget`)
- **Diff Budget (`diff_b`):** 65% ≈ 21,299 bytes.
- **Log Budget (`log_b`):** 25% ≈ 8,192 bytes.
- **Wrapper/System Prompt Reserve:** 10% ≈ 3,277 bytes.

## 2. Truncation Manifest Risk (`[TRUNCATION_MANIFEST]`)
If the candidate diff exceeds `diff_b` or if individual files exceed their weighted share, `_render_file` selectively truncates hunks:
- Emits `(partial)` markers in the manifest.
- Causes the Reviewer to invoke the invariant: *"Phần bị lược KHÔNG được coi là đã review"* (Truncated parts cannot be assumed reviewed).
- Result: Severe deductions in `logic_correctness` and `farm_safety_regression`, permanently capping scores at ~76-78/100.

## 3. Pre-Flight Verification Probe
Before running `closeout_gate.py`, run this probe in the repository to guarantee `level=L0`:
```python
import sys
from pathlib import Path
sys.path.insert(0, 'D:/Taadaa/tools')
from closeout_gate import extract_diff
from sol_payload_guard import split_budget, digest_diff, SOL_TARGET_BYTES

repo = Path('.')
targets = ['path/to/code.py', 'path/to/test.py']
diff_res = extract_diff(repo, base_ref='HEAD', targets=targets)
diff_b, _, _ = split_budget(SOL_TARGET_BYTES)
d = digest_diff(diff_res.diff_text, budget=diff_b)

print(f"Diff Raw Bytes: {d.raw_bytes} / Budget: {diff_b}")
print(f"Digest Level: {d.level}, Omitted Files: {d.omitted}")
assert d.level == "L0" and len(d.omitted) == 0, "Candidate exceeds payload budget and will be truncated!"
```

## 4. Key Truncation Avoidance Rules
1. **Compact Test Files:** Minimize redundant test helpers and nested patch contexts. Keep unit test files under 8.5 KB.
2. **Cohesive Code Hunks:** Cluster module modifications into single continuous blocks rather than 5-6 scattered hunks to save diff headers.
3. **Clean Module Header:** Follow PEP 257 order: Shebang line 1, docstring lines 2-17, then `from __future__ import annotations`.
