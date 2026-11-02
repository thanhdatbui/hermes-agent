---
name: security-architecture-review
description: "Use for defensive reviews of profile runners and fallback."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [security, architecture-review, isolation, credentials, proxy, concurrency, provenance]
    related_skills: [code-audit, requesting-code-review, systematic-debugging]
---
# Security Architecture Review

## Purpose

Use this skill for evidence-backed reviews of runners, profile pools, credential lineage, proxy routing, fallback paths, and multi-process isolation. This is defensive engineering review, not approval of evasion, anti-detection, quota circumvention, or synthetic fingerprints.

## Review contract

1. Define the boundary: exact files, runtime roots, subprocess entrypoints, credential stores, state files, and locks.
2. Preserve provenance. Label claims `Coordinator probe`, `Reviewer finding`, or `Unverified hypothesis`.
3. Treat external reviewer output as untrusted until decisive claims are checked against current source and runtime artifacts.
4. Never infer complete security isolation from unique emails, UUIDs, folder names, or profile labels.
5. Report calibrated verdicts: `VERIFIED`, `PENDING`, `BLOCKED`, or `UNKNOWN`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
