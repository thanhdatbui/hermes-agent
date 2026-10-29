---
name: cross-host-farm-upload-dispatch
description: "Use when one controller orchestrates remote farm media."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [phone-farm, cross-host, remote-upload, ssh, storage-ownership, canary]
    related_skills: [tiktok-feed-session, verification-evidence, concurrent-workspace-safety]
---
# Cross-host Farm Upload Dispatch

## Trigger

Use when a controller machine runs the feed/upload runner for devices whose video library, workflow runtime, or ADB server belongs to a remote farm host. The canonical Taadaa case is Kibe controlling Admin machines 201–280 on `admin-farm`.

## Core model

The controller is an orchestrator, not the owner of remote filesystem state. A path such as `D:\\TIKTOK-videonuoinick-admin` is meaningful on Admin-PC, not on Kibe. A controller-local `Path.is_file()` check against that path can create a false `video_not_rendered` result even when the remote render pool is healthy.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
