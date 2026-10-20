# Gate 6 Mechanical Enforcement: Zero-Whining by Structure & Shift-Left Architecture (2026-10-20)

## 1. Context & Incident Summary

Operator caught Coordinator committing two severe violations:
1. **Gate 6 Violation:** Operating on GPM / ChatGPT web interface without providing physical `MEDIA:<path>` evidence, outputting plain text instead.
2. **Hallucination / Premature Closure:** Misleading Operator by quoting stale router model aliases (`GPT-5.6`) and jumping to conclusions from a demo web header (`GPT-6 with Intelligent UI`) without verifying the actual model selector dropdown.
3. **Conversational Drift & Whining:** When Operator questioned the violation, Coordinator gave rambling theoretical excuses instead of directly answering why the existing gate failed to block it.

Coordinator engaged **Claude Sonnet 5.5 Planner** (`--role planner`, max 10 turns) across 3 adversarial design rounds and **Claude Sonnet 5.5 Reviewer** (`--role reviewer`, max 8 turns) across 4 rigorous code review rounds, achieving **`VERDICT: APPROVED`** on `guard_media_vision_gate.py` with 85/85 tests passed.

---

## 2. The 4 Traps of Naive Anti-Whining Gate Design

During consultations, Coordinator and Claude Sonnet 5.5 identified 4 fatal traps that cause paralysis, latency freezes, or whining in gate architectures:

### Trap 1: Whining in Degraded Prose
- **Vulnerability:** When a gate hits retry limits and falls back to a "DEGRADED" state, allowing the LLM to write free-form prose results in conversational whining ("Dạ em đã cố gắng nhưng bất lực...", "Em xin lỗi anh giúp em với...").
- **Solution (Zero-Whining by Structure):** Strip the LLM of prose generation capabilities on the degraded branch entirely. The runtime automatically formats the output using a strict, machine-generated template:
  `Trạng thái: DEGRADED | Mã: <code> | Thiết bị: <id> | Bằng chứng cuối: <receipt_id> | Việc tiếp theo: <action>`
  Zero prose means 0% possibility of conversational whining.

### Trap 2: Context-Blind Egress Capture (The Autopilot Trap)
- **Vulnerability:** Designing an Egress filter that tries to "autonomously capture" missing screenshots out-of-band fails because the egress filter does not know which CDP port, GPM profile ID, or ADB serial the agent was interacting with.
- **Solution (Shift-Left Tool Wrapper):** Shift capture and OCR left into the UI tool wrapper itself (`computer_use`, `gpm`, `adb`, `playwright`). The wrapper captures the screenshot, runs WinRT OCR, and attaches a signed `Evidence Receipt` with metadata (`device_id`, `cdp_port`, `action_ts`, `ocr_status == 'OK'`) with an execution budget <= 15s (max 1 retry). Egress is purely a millisecond-fast scope-guard.

### Trap 3: Regex False Positives on Normal Chat
- **Vulnerability:** Using broad regex patterns (like "hiển thị", "lỗi", "màn hình") at egress blocks normal user discussions about code, architecture, or general questions.
- **Solution (Strict UI-Turn Scope Guard):** The Gate 6 Egress Filter is ONLY armed if the turn actually invoked a UI tool (`is_ui_turn(tool_calls)`). Normal conversation, code review, and non-UI terminal commands bypass the gate 100%. If tool calls cannot be parsed or are empty during an action claim, the gate **fails closed**.

### Trap 4: Egress Retry Latency Freezes (The 3–5 Minute Hang)
- **Vulnerability:** Allowing the Egress filter to reject output, re-prompt the LLM, wait 45s, reject again, and loop 3 times hangs the session for 3–5 minutes while the user waits in frustration.
- **Solution:** Egress retry count = 0. All evidence generation happens synchronously in the tool wrapper. Total additional latency ceiling <= 20s. If evidence is missing, immediately emit the machine-rendered degraded template.

---

## 3. Sanitizer Loop Against Tag Reassembly Attacks

When sanitizing user-controlled fields (`device_id`, `next_action`) inserted into degraded templates:
- A single pass of `re.sub(r'(?i)media:', '', text)` is vulnerable to reassembly attacks:
  - `MEDMEDIA:IA:` -> inner `MEDIA:` stripped -> leaves `MEDIA:`.
  - `MEDI\nA:` -> character stripping leaves `MEDIA:`.
- **Mechanical Fix:**
  1. Strip disallowed characters first: `text = re.sub(r'[^A-Za-z0-9_.: -]', '', str(s) or '')`.
  2. Run a loop until convergence:
     ```python
     while True:
         new_text = re.sub(r'(?i)media:', '', text)
         if new_text == text:
             break
         text = new_text
     return text.strip()[:64]
     ```

---

## 4. Multi-Task Prompt Overload Trap for Haiku Worker

When Operator asked: *"Mà sao không gọi Haiku mà phải gọi Agy CLI?"*:
- **Root Cause:** Coordinator dispatched a prompt with 5 complex, distinct refactoring tasks across a 500-line monolith file to Haiku in a single dispatch.
- **Haiku Failure Mode:** Haiku 5.5 is an atomic O(1) worker optimized for 10–15s single-point patches. Overloading Haiku with 5 structural changes causes it to fail diff verification (`TASK_FAIL / unrelated_files_changed`), tripping the 2-attempt circuit breaker in `dispatch_worker.py` and escalating to Agy CLI (which then timed out after 1200s).
- **Rule:** Never batch multiple separate refactorings into one prompt for Haiku. Decompose review findings into atomic 1-target, 1-function dispatches.
