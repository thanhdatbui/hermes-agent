# Multi-Machine Gate 6: Media Completeness, Anti-Cheating & Zero-Whining by Structure

## Context & Incident Background (21/10/2026)

When operating multiple farm devices in parallel or batch workflows (e.g., 6 machines: 17, 20, 41, 217, 220, 241 across local Kibe and remote Admin hosts), the Hermes Coordinator exhibited severe **Recency Bias**:
- When multiple background processes finished, the Coordinator only attached a single `MEDIA:<path>` tag corresponding to the last completed machine, dropping visual evidence for all previously completed devices.
- The Operator reprimanded: *"Mà sao mỗi lần m làm vài máy mà m gửi bằnh chứng media có 1 máy v"*.
- The Operator probed potential failure modes:
  1. *"Mày có tìm cách gian lận bằng gửi cùng 1 máy nhiều lần k"* (Will the LLM cheat by sending the same machine multiple times?)
  2. *"Và cơ học nó thiết kế có gây khóc lóc k v"* (Will the mechanical gate design cause paralysis and whining?)
- The Operator mandated a formal Tri-Party Consultation: *"Gọi 3 bên hỏi"* (Claude Sonnet 5.5 Reviewer, Advisor Sol-WebPool :20129, and Hermes Coordinator).

---

## 1. Tri-Party Architectural Consensus: Anti-Cheating Invariants

Relying solely on `count("MEDIA:") == N` creates an immediate loophole where an LLM under pressure will duplicate the same `MEDIA:` path $N$ times, copy files under distinct names, or slightly resize/re-encode images to bypass naive byte checks.

The Tri-Party Review established 4 mandatory mechanical locks:

### A. Per-Machine Hardware Serial Binding
Every visual evidence artifact MUST strictly reside in the device runner's canonical directory path containing that machine's exact hardware serial or canonical machine token:
```text
D:/CodexRuntime/tiktok-video/runs/run_<DEVICE_SERIAL>_<TIMESTAMP>/avatar-uploaded-confirmed.png
```
- Local and remote runners generate directories incorporating the ADB hardware serial (e.g., `ce0318237dec1ce60c` for Machine 20, `ce01171168a90d0105` for Machine 220).
- Path binding regex enforces strict token boundaries:
  ```python
  pattern = r"(?<![0-9A-Za-z])(?:m|machine[_\-]?)?" + re.escape(machine_id) + r"(?![0-9A-Za-z])"
  ```
  This cleanly permits canonical naming forms (`m220`, `machine-220`, `220`) while strictly preventing partial numeric collisions (e.g., `1220` or `2201` falsely matching `220`).
- Arbitrary external paths or mock paths are hard-rejected with `ERR_MEDIA_PATH_BINDING`.

### B. Dual Hash Integrity (SHA-256 + Cross-Machine Grouping)
- **Byte Hash (SHA-256):** Rejects direct file copying or multiple references to the identical file:
  $$\text{count}(\text{unique}(\text{SHA256}(img_1, \dots, img_N))) == N$$
- **Unconditional Hashing Invariant (Remediated Vulnerability):**
  * *Vulnerability found by Claude Sonnet 5.5 Reviewer in Round 1:* If hashing is only performed for machines present in a filtered manifest (`--machines`), evidence items for excluded machines bypass hashing, allowing an attacker to reuse a screenshot from an excluded machine to claim success for a target machine.
  * *Fix:* Compute SHA-256 unconditionally across all evidence items before evaluating filter membership. Any cross-machine duplicate hash triggers `ERR_DUPLICATE_MEDIA_SHA256` and suppresses `MEDIA:` output.

### C. Mathematical Set-Difference Audit
The reported machine identifiers are validated against the initial immutable batch manifest:
```python
assert set(reported_machine_ids) == set(manifest.machine_ids)
assert len(reported_machine_ids) == len(manifest.machine_ids)
```
Each machine ID in the manifest must appear exactly once. Zero duplicates (`ERR_DUPLICATE_MACHINE_EVIDENCE`), zero omissions (`ERR_MISSING_MACHINE`), zero unregistered machines (`ERR_UNKNOWN_MACHINE`).

### D. Immutable Batch Manifest
At batch launch, a deterministic manifest is recorded (`batch_manifest.json`) containing the exact target machine IDs and their hardware serials. The egress gate audits directly against this immutable record.

---

## 2. Zero-Whining by Structure (Anti-Paralysis Protocol)

### The Whining Trap (Why Loose Egress Gates Paralyze Agents)
If an egress filter simply blocks an incomplete message and throws an `AssertionError` or returns conversational feedback to the LLM, the LLM falls into a panic loop:
1. It tries to explain away the failure ("I apologize", "Due to system constraints...").
2. It asks the Operator for guidance ("Should I retry or proceed?").
3. It halts autonomous operations, locking up the chat session in perpetual paralysis.

### The Structural Solution: Machine-Synthesized Templates
To achieve complete autonomy without paralysis or conversational whining:

1. **Strip LLM Prose Generation Rights:**
   - Multi-machine batch reporting MUST NOT be drafted free-form by the LLM.
   - A deterministic tool (`D:/Taadaa/tools/compose_batch_report.py`) reads the manifest and execution receipts, rendering a rigid structural template:
   ```text
   [BATCH REPORT]
   machines=2 valid=2 invalid=0
   [MACHINE 20] status=SUCCESS OK
   MEDIA:D:/CodexRuntime/tiktok-video/runs/run_ce0318237dec1ce60c_20261021_041312/avatar-uploaded-confirmed.png
   [MACHINE 220] status=SUCCESS OK
   MEDIA:D:/Taadaa/reports/avatar_confirmed_m220.png
   ```

2. **Blocked With Real Evidence is a Valid Terminal State:**
   - A hardware failure, timeout, or UI error is NOT a gate violation that blocks message delivery.
   - When a runner fails, it captures the error state screenshot (e.g., `avatar-picker-no-match.png`) and records `FINAL_BLOCKED` with the error receipt.
   - The egress gate treats `VERIFIED_SUCCESS` + `FINAL_BLOCKED` (with valid error media) as a 100% complete and compliant batch report.
   - The message is delivered immediately without interruption.

3. **No-Waiting-State Invariant:**
   - Once the batch report is delivered, the session advances to the next pending queue item or gracefully exits.
   - The system NEVER enters an interactive waiting state asking the Operator for permission to proceed.

---

## 3. Production Implementation & Verification

### A. Production Tooling
- **Composer:** `D:/Taadaa/tools/compose_batch_report.py`
  * CLI arguments: `--manifest <json|file>`, `--evidence <json|file>`, `--machines <list>`, `--strict` (exit 1 on validation error), `--json` (emit structured validation payload).
- **Test Suite:** `D:/Taadaa/tools/tests/test_compose_batch_report.py` (10/10 passed in 0.24s).

### B. Claude Sonnet 5.5 Reviewer 2-Round Audit Progression
- **Round 1 (REJECTED):** Discovered the filter-ordering defect where `--machines` narrowed the manifest before hash deduplication, allowing cross-machine duplicate screenshots to evade detection.
- **Round 2 (APPROVED):** Verified unconditional SHA-256 hashing across all evidence items and dedicated regression test `test_cli_machines_filter_with_shared_duplicate_sha256`. Live simulation proved pre-fix code emitted invalid `MEDIA:` while post-fix code completely suppresses the cheated media.

---

## 4. Operational Checklist for Multi-Machine Tasks

Before sending any multi-machine summary to the Operator:
- [ ] Count of distinct `MEDIA:` tags equals exactly $N$ target machines.
- [ ] Each `MEDIA:` path is anchored to the runner directory matching that machine's hardware serial or canonical token (`m<id>`, `machine-<id>`).
- [ ] No duplicate SHA-256 hashes across the attached images.
- [ ] Every image has been visually verified via `browser_vision` or WinRT OCR prior to dispatch.
- [ ] Any degraded/failed machine includes its physical error screenshot, never omitted or papered over.
