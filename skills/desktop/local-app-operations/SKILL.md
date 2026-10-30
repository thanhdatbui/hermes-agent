---
name: local-app-operations
description: "Safely update and operate locally hosted web applications through their installed/runtime surface, keeping application management separate from source-repository maintenance."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [local-app, web-dashboard, app-update, browser-ui, proxy-import, credential-safety]
    category: desktop
---
# Local application operations

Use this skill when the user asks to update, configure, log into, or import data into a locally running application with a browser dashboard (for example, a gateway, proxy manager, or self-hosted admin UI).

## Core rule: app surface first, repository second

1. Interpret “update the app” as updating the installed/running application instance, not automatically updating its source repository.
2. Discover the runtime surface first: URL/port, process owner, installed package/shortcut, in-app version, and available updater or admin controls.
3. Do not enter a source repository, run `git fetch`, `rebase`, `reset --hard`, `stash`, or overwrite local code unless the user explicitly asks to update the source checkout or the application is demonstrably installed from that checkout and no safer app updater exists.
4. Never involve an unrelated repository merely because it is present on the machine. State the exact target path and port before acting.
5. Do not stop a process as a default prerequisite. Update through the app's own updater or package mechanism first. Restart only when required by the update and only after checking the process/port and scope.
6. If a source-based update is truly required, preserve local work visibly (named backup/stash/branch), report the exact conflict risk, and verify the application only after the update/build succeeds. Never silently discard local work.
7. **SQLite Data Hub & Dashboard Integration:** When migrating legacy Excel workbooks to a centralized SQLite database (`farm_master.db`) and surfacing it via an internal Web Dashboard (such as `kibe:1905`), preserve multi-process safety, use normalized header aliasing with NFD accent stripping, expose clean DAL interfaces (`farm_db.py`), and restart the dashboard cleanly via dedicated orchestrators (`restart_tiktok_dashboard.py`). Reference: `references/sqlite-farm-master-ledger-and-web-dashboard.md`.
8. **Meta / Muse AI & Antidetect Isolation Governance:** When testing or registering accounts on antidetect browsers (GPM, Playwright), strictly enforce clean-state isolation (new profile + fresh proxy per attempt, strictly adhere to requested country/Canada), never push manual steps to the user ("tự làm nốt đi"), never connect personal accounts to foreign proxies, and handle registration blockers autonomously. Reference: `references/meta-muse-antidetect-registration-governance.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
