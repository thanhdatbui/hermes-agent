---
name: hermes-dynamic-skill-routing
description: "Use for Hermes dynamic skill routing O(1) context injection."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, skills, context-optimization, o1-retrieval, anti-bloat, dispatch-worker, skill-injector]
    related_skills: [hermes-agent, session-close-protocol, closeout-review-discipline]
---
# Hermes Dynamic Skill Routing O(1)

Use this skill when operating or troubleshooting the skill-context injection pipeline that prevents context bloat (`[SKILL_PRUNED]` errors) on the Taadaa Farm.

## Architecture Overview

Instead of loading all 190+ skills statically into every session:

```
[Task Prompt]
     │
     ▼
skill_injector.inject_skill_context(prompt, tier="T1")
     │   1. check_index_freshness() - verify mtime of each SKILL.md
     │   2. lookup_skills(prompt, top_k=5) - O(1) keyword bucket match
     │   3. load_skill_content() - reads matched + 5 Pinned Core Skills
     │   4. Budget clamp: total ≤ max_context_chars (default 15,000)
     │
     ▼
[Enriched Prompt = skill context block + "---" + original prompt]
     │
     ▼
dispatch_worker.py → Agy CLI (Tier 1) / Haiku fallback (Tier 2)
```

## Core Files

> Architecture Reference: [`references/mechanical-planner-and-worker-gateways-architecture.md`](references/mechanical-planner-and-worker-gateways-architecture.md) (Claude CLI Approved)
> Case Study & Anti-Patterns: [`references/static-skill-dump-anti-patterns.md`](references/static-skill-dump-anti-patterns.md) (Static 350+ Dump vs Dynamic O(1) Routing)

| File | Path | Purpose |
|------|------|---------|
| `build_skill_index.py` | `D:/Taadaa/tools/` | Scans 190+ SKILL.md files, outputs `skills_index.json` |
| `skills_index.json` | `D:/Taadaa/tools/` | Lightweight index (name, category, description, path, tokens_est) |
| `skill_lookup.py` | `D:/Taadaa/tools/` | Keyword bucket lookup, always returns 5 Pinned Core Skills |
| `load_selected_skills.py` | `D:/Taadaa/tools/` | Loads selected skills with path traversal guard |
| `skill_injector.py` | `D:/Taadaa/tools/` | Adapter: orchestrates lookup → load → budget → inject (auto_heal supported) |
| `dispatch_planner.py` | `D:/Taadaa/tools/` | Single Dispatch Gateway for planning: Sonnet -> Sol -> Coordinator |
| `dispatch_worker.py` | `D:/Taadaa/tools/` | Single Dispatch Gateway for code fixes: Sol -> Agy -> Haiku -> Coordinator |
| `record_skill_knowledge.py` | `D:/Taadaa/tools/` | Canonical 1-touch tool: resolve skill, atomic write, auto rebuild index |
| `auto_prune_memory.py` | `D:/Taadaa/tools/` | Automated 2-Stage GC for MEMORY.md and USER.md (dedup + mechanized purge) |
| `preview_skill_injection.py` | `D:/Taadaa/tools/` | CLI preview without side effects |

## Pinned Core Skills (Always Injected)

These 5 skills are ALWAYS loaded regardless of query result:
- `taadaa-farm-ops-rules`
- `farm-anti-overengineering`
- `session-close-protocol`
- `evidence-first-delivery`
- `agent-verification-loop`

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
