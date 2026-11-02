---
name: cloud-storage-sync-troubleshooting
description: Troubleshoot and resolve sync errors, stuck files, authentication hangs, and notification issues for cloud storage clients (Google Drive, OneDrive, Dropbox, iCloud) on Windows.
category: devops
---
# Cloud Storage Sync Troubleshooting

## Overview
Systematic approach to diagnose and fix sync client issues on Windows: stuck "Lost and Found" notifications, orphaned files, database corruption, sign-in hangs, and sync loops.

## Trigger Conditions
- Persistent "Lost and Found" / "Bị thất lạc và đã tìm thấy" popup
- Files stuck in sync queue (0 bytes, never complete)
- Sync client high CPU / memory without progress
- Notification drawer shows unresolved sync errors
- iCloud desktop app stuck indefinitely on "Signing In..." with 0% CPU and CLOSE_WAIT sockets

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
