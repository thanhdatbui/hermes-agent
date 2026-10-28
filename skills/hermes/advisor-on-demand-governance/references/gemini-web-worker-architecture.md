# Gemini Web Worker (Argon 4) Architecture & Operational Guide

## 1. Overview & Context
- **Script Location**: `D:/Taadaa/tools/gemini_web_worker.py`
- **Unit Test Suite**: `D:/Taadaa/tools/tests/test_gemini_web_worker.py`
- **Model Endpoint**: `POST http://127.0.0.1:20129/v1/chat/completions` via combo `gemini-web-argon-pool`
- **Underlying Engine**: Google Gemini 4 (Argon) web session via OmniRoute reverse HTTP stream (`StreamGenerate`, `modelCategory = 3`).

## 2. Technical Pitfalls & Fixes in Parser Design

### Pitfall 1: Gemini Web Python Sandbox Activation
- **Behavior**: When prompted with generic coding instructions, Gemini Web often outputs internal Google sandbox blocks (e.g. ````python?code_reference ... ````) and pauses execution waiting for workspace app approval.
- **Fix**: The system prompt strictly imposes:
  `CRITICAL CONSTRAINT: You do NOT have internal python execution sandbox. Do NOT execute python code. Output EXACTLY and ONLY ONE Action Block per turn.`

### Pitfall 2: Dual Syntax Matching for Code Patches
Gemini frequently outputs two distinct patch syntaxes:
1. **Standard Farm ReAct Action**:
   ```text
   ACTION: PATCH
   PATH: relative/path/to/file.py
   <<<<<<< SEARCH
   <old code>
   =======
   <new code>
   >>>>>>>
   ```
2. **Gemini Native Diff Notation**:
   ```text
   PATCH relative/path/to/file.py
   <<<<
   <old code>
   ====
   <new code>
   >>>>
   ```
- **Fix in `parse_action()`**: Regex dynamically captures angle brackets from length 3 to 7 (`<{3,7}` and `={3,7}` and `>{3,7}`), seamlessly extracting `search_block` and `replace_block`.

### Pitfall 3: Regex Multiple Repeat Error
- **Bug**: Using `r"<+{3,7}"` inside Python `re` raises `re.error: multiple repeat at position 2`.
- **Fix**: Always use `r"<{3,7}"` without redundant `+` quantifier.

## 3. Invocation Runbook
Run directly via command line:
```bash
python D:/Taadaa/tools/gemini_web_worker.py "<prompt task>" --workdir "<path/to/repo>" --file "<target_file>" --max-turns 8
```
Or dispatch dynamically when user specifically requests Gemini Web / Argon Worker.
