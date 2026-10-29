# Subagent Dispatch Deadlock & Regex Scanner Overmatch Traps

## 1. Systemic Subagent Dispatch Deadlock (Subagent Edit Blocked Storm)

### The Anti-Pattern & Policy Desync
- **Root Cause:** A systemic contradiction where system prompts / SOUL guide the Coordinator:
  "Mọi việc phát triển code... BẮT BUỘC do Worker subagent thực hiện qua delegate_task"
  while runtime Gate #3 enforces a mechanical fail-closed block:
  "delegate_task BỊ CẤM CHO TASK SỬA CODE! Bắt buộc thi công qua dispatch_worker.py"
- **The Failure Cascade:**
  1. Coordinator reads SOUL and calls `delegate_task` to patch code.
  2. Gate #3 intercepts and records a `subagent_edit_blocked` failure in the dispatch audit log.
  3. Hook guidance inadvertently suggested bypass keywords (such as allow subagent code edit overrides).
  4. LLMs blindly appended the override string to `delegate_task`, spawning generic Hermes subagents that lack anchor verification, O(1) context packing, and Sol/Agy models.
  5. The generic subagents fumbled across files, accumulating secondary failures: `NEEDS_INPUT`, `NO_DIFF`, and `TIMEOUT`.
  6. The 6-hour compliance watchdog reported massive G3 failures (>40 violations).

### The Invariants & Canonical Contract
1. **Tool-to-Task Specialization Invariant:**
   - **Code Modifications:** BẮT BUỘC thi công qua `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"` (Tier 1 Sol -> Tier 2 Agy -> Tier 3 Haiku).
   - **`delegate_task` Restriction:** `delegate_task` CHỈ DÙNG cho nhiệm vụ đọc/thám nghiệm độc lập (`investigate` với budget <= 8 calls). Tuyệt đối cấm dùng cho task sửa code.
2. **Guidance Cleanliness Invariant:**
   - Never expose internal bypass flags or override keywords in user-facing guidance messages. The required action must point strictly to `dispatch_worker.py`.

---

## 2. Regex Scanner Overmatching & Circular Self-Blocking (Dangerous Root Trap)

### The Anti-Pattern
- **Naive Substring Scanner:** Scanners defined as `(?<![\w.-])find(?:\.exe)?\s+[^\n]*` match:
  - English comments in Python scripts: `# Find center phone bounds`
  - String manipulation or methods: `str.find( ... )`
  - Repair prompts mentioning the rule name itself
- **Integer Division vs Unix Root:** Boundary checks using `/{1,2}` treat Python integer division `// 2` or comment syntax `//` as the Unix root path `//`.
- **False-Positive Root Intercept:** When the command also mentions a protected directory (e.g. `D:/Taadaa/orders/images/order_raw.jpg`), the hook evaluates:
  `contains_dangerous_root(cmd) AND find_scanner.search(cmd) -> True`
  falsely classifying benign image processing or repair commands as a broad filesystem scan.

### The Invariants & Implementation
1. **Command-Position Enforcement for Shell Scanners:**
   - Shell utility scanners (`find`, `grep`, `rg`) must only match at command execution position: line start `^`, after shell chaining operators (`[;&|]`), command substitution (`$()`, backticks), or prefix utilities (`sudo`, `env`):
     ```python
     FIND_SCAN = re.compile(
         r"""
         (?:^|[;&|`$()]\s*|\b(?:sudo|env)\s+)
         find(?:\.exe)?
         \s+
         (?:-[a-zA-Z]|\.|\/|[a-zA-Z]:)
         [^\n]*
         """,
         re.I | re.X,
     )
     ```
2. **Interpreter Command Exemption:**
   - When the top-level command is an interpreter invocation (`python -c "..."` or `python script.py`), skip shell utility scanning. Filesystem walks inside Python code are governed exclusively by `PYTHON_SCAN` (`os.walk`, `rglob`, `glob.*recursive=True`).
3. **Strict Unix Root Boundary Check:**
   - Exclude double slashes `//` and arithmetic division inside Python commands from Unix root detection:
     ```python
     if re.search(r"(?<!/)(?:^|[\s'\"`(=])/(?:[\s'\"`\)]|$)(?!/)", norm):
         if re.search(r"\bpython(?:\d+)?(?:\.exe)?\s+", norm):
             return False
         return True
     ```
4. **Multi-Line Command Splitting in Security Allowlist:**
   - Security wrappers split terminal commands on `\n` to evaluate allowlists per statement. Prompts containing raw newlines within double quotes have subsequent lines evaluated as standalone commands, tripping default-deny allowlists on regex fragments.
   - **Rule:** Never pass unescaped raw newlines in terminal commands. Use single-line prompts with `\n` literals, or write the prompt to a file before dispatching.
