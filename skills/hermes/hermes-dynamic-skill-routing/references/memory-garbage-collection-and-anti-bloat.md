# Hermes Agent Memory Garbage Collection & Anti-Bloat Architecture

## 1. Problem Statement: The Proactive Memory Paradox

Hermes Agent is designed to "save proactively" whenever it learns environment facts or operational rules. However, in an evolving production farm:
1. **Unchecked Accumulation:** Operational scripts are continually mechanized (e.g. follow streak management, worker dispatch gateways, shift pools, reboot watchdogs).
2. **Context Bloat:** If memory entries are never purged once their underlying logic is committed to code, `MEMORY.md` rapidly approaches its hard cap (2,200 chars / 98%+), degrading the prompt with obsolete operational instructions.
3. **The Manual Dilemma:** Forbidding proactive saves forces the user to manually command `memory(...)`, which cripples the agent's core capability to learn continuously and adapt.

## 2. The Solution: Proactive Learning + Automated Garbage Collection

Instead of banning automatic memory saves, allow Hermes to learn and record proactively, but enforce **Automated Periodic Garbage Collection**:

```
[Conversations / Daily Ops]
           │
           ▼
[Hermes Proactive Memory Save] ──> Learns user preferences, corrections, new quirks
           │
           ▼ (Every 6h Cron: auto_prune_memory.py)
[Garbage Collection Engine]
  1. Parse entries by '§' delimiter in MEMORY.md & USER.md.
  2. Deduplicate redundant/near-identical entries.
  3. Filter out mechanized rules (already hardcoded in Python/guards).
  4. Preserve Protected Persona entries (Vibe O(1), Advisor On-Demand, Auto-heal).
  5. Enforce < 70% character capacity clamp.
  6. Atomic write to $LOCALAPPDATA and sync to Git deploy repo.
  7. Silent Watchdog: 0 stdout / 0 tokens when clean; alerts only on pruning.
```

## 3. Implementation Details

- **Script:** `D:/Taadaa/tools/auto_prune_memory.py`
  - Synced to `%LOCALAPPDATA%/hermes/scripts/auto_prune_memory.py`
- **Cron Job:** `hermes-memory-garbage-collector` (Job ID: `ee258b5bb5e5`)
  - Schedule: `0 */6 * * *` (00:00, 06:00, 12:00, 18:00)
  - Mode: `no_agent=True` (Zero LLM tokens)
  - Delivery: `origin` (Silent when clean, reports only when pruned)

## 4. Rule Classification Table

| Category | Storage Target | Example | Handling by Garbage Collector |
| :--- | :--- | :--- | :--- |
| **Mechanized Code** | Python scripts / Guards | Follow streak cd, Tier 1 Sol exit 126, Shift pool, Game guard | **Auto-pruned** from MEMORY.md |
| **Operational Procedures** | Dynamic Skills (`SKILL.md`) | ADB setup, uiautomator recovery, tender crawler | Kept in skill directory; loaded O(1) on-demand |
| **User Persona / Vibe** | `USER.md` | Vibe O(1), Advisor on-demand, Auto-heal ngầm, Hand-off | **Protected** (never pruned) |
| **Recent / Transient Quirks** | `MEMORY.md` | Newly observed device behavior not yet mechanized | Preserved until mechanized in code |
