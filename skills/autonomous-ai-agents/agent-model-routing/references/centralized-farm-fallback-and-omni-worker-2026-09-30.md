# Centralized Farm Fallback to Omni-Worker & 160-Device Architecture (2026-09-30)

## Context & User Correction

In multi-agent farm operations, the user provided a fundamental operational correction:
> *"160 máy chạy script python, còn sửa chỉ sửa ở 1 máy. Chỉnh cho tao fallback hết sang model omni worker."*

This establishes two primary architecture invariants:
1. **Physical Boundary (Farm vs LLM):** The 160 Android devices execute local Python/ADB/ATX automation scripts independently. They do not run LLMs or AI subagents.
2. **Centralized Code Management:** All code development, bug fixing, test running, and git operations take place strictly on **ONE host machine** (Coordinator/Workstation at `D:\Taadaa\...`).
3. **Centralized Worker Fallback:** When a worker subagent (`delegate_task`) or provider call encounters failure (quota exhaustion, 429 rate limit, 5xx server error, network timeout), recovery MUST NOT be handled by having the Coordinator blindly take over implementation in the main session. Instead, Hermes runtime MUST centrally fail over to `omni-worker`.

---

## Why Coordinator Must Never Take Over Worker Implementation

As confirmed by Claude Code CLI (v2.1) architectural analysis:
- **Pollution of Coordination Context:** Sửa code, đọc XML dumps, và chạy test nạp vào session chính hàng chục KB context rác, làm phình to context nhanh chóng và gây nghẽn gateway event loop (bài học sự cố 25/09).
- **Cascading Collapse:** Nếu worker bị 429 mà Coordinator nhảy vào ôm việc, Coordinator cũng sẽ dính 429/timeout. Khi não điều phối bị đơ, 160 máy đang chạy nền sẽ mất người giám sát, dẫn đến toàn bộ farm bị đóng băng.
- **Phân định rõ rệt:**
  * Lỗi hạ tầng (Quota, 429, API down) $\to$ Xử lý bằng **Provider Failover (đổi sang `omni-worker`)**, không giải quyết bằng sửa code.
  * Lỗi logic/bug thật $\to$ Worker sửa theo contract O(1). Coordinator chỉ thực hiện Emergency Surgery L2 khi thỏa mãn ngân sách O(1) khắt khe (1 file, <= 15 dòng diff, test < 30s).

---

## Centralized Fallback Chain Configuration in Hermes

In `~/.hermes/config.yaml`, the root `fallback_providers` list controls the failover sequence for both the parent session and child subagents (which inherit `_fallback_chain` in `tools/delegate_tool.py`):

```yaml
fallback_providers:
- model: omni-worker
  provider: custom:omni
- model: muse-spark-1.3
  provider: custom:opencode
- model: cx/gpt-5.6-luna-high
  provider: custom:omni
```

### Verification & Tool Commands
- Check current chain: `hermes fallback list`
- Inspect config: `hermes config show`
- Runtime behavior: When the primary model (`omni-worker` or pinned `delegation.model`) hits an upstream 429/500/timeout, the Hermes runtime immediately attempts the next provider in the chain without terminating the child subagent or aborting the task.
