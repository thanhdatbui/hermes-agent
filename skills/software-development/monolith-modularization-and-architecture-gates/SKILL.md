---
name: monolith-modularization-and-architecture-gates
description: "Use when modularizing monolith scripts with CI gates."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [refactoring, monolith, architecture-gate, thin-slice, code-cleanliness, ci-enforcement]
    related_skills: [farm-anti-overengineering, test-driven-development, code-audit, closeout-review-discipline]
---
# Monolith Modularization and Architecture Gates Discipline

Use this skill when refactoring monolithic production scripts (> 1.500 lines) into modular subpackages without disrupting active workloads, breaking backward compatibility, or letting subsequent AI agents undo the modularization.

Reference files:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

## 1. Core Principles & The Monolith Problem

### The Problem
When scripts evolve over months, they accumulate multiple orthogonal domains into a single file (e.g., network proxy rotation, SQLite concurrency, video perceptual hashing, YOLO cropping, language gates, platform scrapers).
- **Context Bloat:** Coding agents (Claude/Gemini) must ingest 20.000–30.000 tokens per request just to read the script, rapidly exhausting token quotas.
- **Accidental Coupling:** Editing one component (e.g. proxy) risks breaking another (e.g. database transactions or audio transcription).
- **Agent Regression Trap:** Without mechanical locks, future AI turns naturally append new code back into the monolith out of least resistance.

### The Invariants
1. **Zero Downtime / Zero In-Flight Disruption:** Running background processes (e.g. 20-thread downloaders or render chains on worker nodes) must never encounter missing imports, broken CLI parameters, or locking contention.
2. **Absolute Backward Compatibility:** Re-export all public domain functions from the original orchestrator so callers importing from the legacy module path never break.
3. **Mechanical Architecture Gates:** Never rely on agent prompt discipline alone. Lock module boundaries via automated unit tests that enforce line count ceilings and forbid inline redefinitions.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
