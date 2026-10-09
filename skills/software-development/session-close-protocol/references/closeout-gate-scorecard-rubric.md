# Closeout Gate Scorecard & OmniRoute Architecture (2026-09-18)

## Overview
`D:/Taadaa/tools/closeout_gate.py` serves as the centralized gate runner for pre-merge review and test execution. In September 2026, the Gate 1 review pipeline was upgraded to use a structured 5-criteria scorecard with dynamic OmniRoute endpoint resolution.

## 1. OmniRoute URL Precedence & Fallback Probes
OmniRoute runs on port 20129 (`http://localhost:20129/v1/chat/completions`). When running across machines or containers, hardcoding localhost can cause silent review failures.

### Precedence Hierarchy:
1. Explicit CLI flag `--base-url <url>` (or argument `custom_url`).
2. Environment variable `OMNI_ROUTE_URL`.
3. Environment variable `OMNI_URL`.
4. Live probing against candidates (`localhost:20129`, `127.0.0.1:20129`, `192.168.110.123:20129`) using a fast probe (`/v1/models` or HTTP HEAD/GET).
5. Safe fallback to default farm router IP: `http://192.168.110.123:20129/v1/chat/completions`.

```python
def resolve_omni_url(custom_url: str | None = None) -> str:
    if custom_url:
        return custom_url
    if os.environ.get("OMNI_ROUTE_URL"):
        return os.environ["OMNI_ROUTE_URL"]
    if os.environ.get("OMNI_URL"):
        return os.environ["OMNI_URL"]
    # Dynamic probe candidates ...
```

## 2. 5-Criteria Sol Auditor Rubric & Scorecard Format
The system prompt requests a JSON scorecard structured as:
- Logic & Correctness (max 30)
- Test Evidence & Coverage (max 25)
- Telemetry & Observability (max 15)
- Farm Safety & Regression (max 15)
- Code Quality & Architecture (max 15)
**Total: 100 points**.

### Pass Threshold:
- Score $\ge 85$: `APPROVED`
- Score $< 85$: `REJECTED`
- Any critical blocker flagged: `REJECTED` regardless of score.

### JSON Output Contract:
```json
{
  "overall_score": 88,
  "verdict": "APPROVED",
  "criteria": {
    "logic_correctness": {"score": 28, "max": 30, "comments": "Accurate diff handling"},
    "test_evidence": {"score": 22, "max": 25, "comments": "Focused pytest verified"},
    "telemetry_observability": {"score": 13, "max": 15, "comments": "Structured logging present"},
    "farm_safety_regression": {"score": 13, "max": 15, "comments": "Lock breaker protected"},
    "code_architecture": {"score": 12, "max": 15, "comments": "Clean separation"}
  },
  "summary": "Review summary and findings"
}
```

## 3. Parsing & Graceful Fallback
`_parse_scorecard_and_verdict(content: str, pass_threshold: int = 85) -> tuple[str, dict | None]`:
1. First attempts to extract a JSON block enclosed in markdown ` ```json ... ``` ` or raw JSON `{...}` containing `"overall_score"`.
2. Validates `overall_score` vs `pass_threshold`.
3. If JSON parsing fails or schema does not match, falls back to legacy regex searching for `VERDICT: APPROVED` / `VERDICT: REJECTED` or raw keywords `APPROVED`/`REJECTED`.

## 4. Test Suite Requirements (`tests/test_closeout_gate_scorecard.py`)
Ensure full pytest coverage for:
- JSON scorecard passing score ($\ge 85$) -> `APPROVED` + parsed scorecard dict.
- JSON scorecard failing score ($< 85$) -> `REJECTED` + parsed scorecard dict.
- Fallback text with `VERDICT: APPROVED` (no JSON) -> `APPROVED` + `None`.
- Fallback text with `VERDICT: REJECTED` (no JSON) -> `REJECTED` + `None`.
- `resolve_omni_url` environment variable priority (`OMNI_ROUTE_URL` > `OMNI_URL` > probe/default).

### Test Suite Execution & Offline Isolation Pitfalls:
- **Unit Test Offline Requirement:** Tests in `test_closeout_gate_scorecard.py` must NEVER rely on a live OmniRoute server (`:20129`) being online. All network requests and probes must be mocked or parameterized with fixture responses.
- **Verification Command:**
  ```bash
  pytest D:/Taadaa/tools/tests/test_closeout_gate_scorecard.py -v
  ```
- **Markdown Scorecard Formatter:**
  Format rendered output into standard Telegram / Markdown table for session close reporting:
  ```markdown
  | Tiêu chí | Điểm | Max | Nhận xét |
  | :--- | :---: | :---: | :--- |
  | Logic Correctness | 28 | 30 | ... |
  ...
  ```

