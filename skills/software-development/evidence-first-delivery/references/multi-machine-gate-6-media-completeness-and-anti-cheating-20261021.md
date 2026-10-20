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
Every visual evidence artifact MUST strictly reside in the device runner's canonical directory path containing that machine's exact hardware serial:
```text
D:/CodexRuntime/tiktok-video/runs/run_<DEVICE_SERIAL>_<TIMESTAMP>/avatar-uploaded-confirmed.png
```
- Local and remote runners generate directories incorporating the ADB hardware serial (e.g., `ce0318237dec1ce60c` for Machine 20, `ce01171168a90d0105` for Machine 220).
- The verifier validates that the image path matches the machine's hardware serial bound in `devices.yaml` / `admin.yaml`. Arbitrary external paths or mock paths are hard-rejected.

### B. Dual Hash Integrity (SHA-256 + Perceptual Hash)
- **Byte Hash (SHA-256):** Rejects direct file copying or multiple references to the identical file:
  $$\text{count}(\text{unique}(\text{SHA256}(img_1, \dots, img_N))) == N$$
- **Perceptual Hash / Dimension & Pixel Variance:** Rejects attempts to bypass byte hashing via minor re-encoding, cropping, or metadata stripping of a single capture.

### C. Mathematical Set-Difference Audit
The reported machine identifiers are validated against the initial immutable batch manifest:
```python
assert set(reported_machine_ids) == set(manifest.machine_ids)
assert len(reported_machine_ids) == len(manifest.machine_ids)
```
Each machine ID in the manifest must appear exactly once. Zero duplicates, zero omissions.

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
   - A deterministic script (`compose_batch_report.py`) reads the manifest and execution receipts, rendering a rigid structural template:
   ```text
   [BATCH REPORT] Total: N | Succeeded: X | Failed: Y
   • Machine 20 (Nick: ...): [VERIFIED_SUCCESS] MEDIA:D:/.../avatar-uploaded-confirmed.png
   • Machine 220 (Nick: ...): [VERIFIED_SUCCESS] MEDIA:D:/.../avatar-confirmed-m220.png
   • Machine 17 (Nick: ...): [FINAL_BLOCKED: TIMEOUT] MEDIA:D:/.../timeout-error-screen.png
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

## 3. Operational Checklist for Multi-Machine Tasks

Before sending any multi-machine summary to the Operator:
- [ ] Count of distinct `MEDIA:` tags equals exactly $N$ target machines.
- [ ] Each `MEDIA:` path is anchored to the runner directory matching that machine's hardware serial.
- [ ] No duplicate SHA-256 hashes across the attached images.
- [ ] Every image has been visually verified via `browser_vision` or WinRT OCR prior to dispatch.
- [ ] Any degraded/failed machine includes its physical error screenshot, never omitted or papered over.
