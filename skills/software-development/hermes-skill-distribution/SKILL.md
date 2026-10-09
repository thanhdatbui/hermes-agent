---
name: hermes-skill-distribution
description: "Synchronize Hermes skills safely across machines."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, skills, sync, git, profiles, multi-machine]
    category: software-development
---

# Hermes Skill Distribution Skill

Use this skill when a Hermes skill is maintained in a repository but loaded from a separate profile-local skills directory. It covers safe propagation across machines and profiles; it does not replace the repository's own change review or silently overwrite customized skills.

## When to Use

- After pulling a repository update that changes bundled skills.
- When one machine has a newer skill than another.
- When `hermes update` or ordinary skill sync reports that a local copy was kept.
- When establishing a repository-as-source-of-truth workflow for multiple Hermes machines.

## Prerequisites

- The Hermes repository and target branch/remote are known.
- The target profile's `$HERMES_HOME` is known.
- Local edits to the profile skill have been identified before replacement.
- Use `terminal` for Git and CLI commands, `skill_view` for runtime-content inspection, and `skill_manage` only when creating or maintaining the reusable distribution skill.

## How to Run

Use the repository as the shared Git boundary, but support changes made in either machine's local Hermes skill directory:

1. Before starting work, fetch/pull the target branch and inspect the working tree. Do not reset or discard unrelated local changes.
2. After creating or editing skills locally, export the local skill tree into the repository with the project's `deploy/sync-skills-to-repo.ps1` helper (or its platform equivalent). The export must exclude runtime metadata, caches, locks, curator state, hub data, and secrets.
3. Review `git status` and `git diff`, resolve any deliberate local/repository overlap, and run `git diff --check`.
4. Commit the reviewed skill changes. Before pushing, fetch/pull again, merge or rebase remote changes, resolve conflicts, rerun `git diff --check`, then push.
5. On the other machine, pull the commit and sync repository skills into its local Hermes home with the forward sync helper. Do not use `hermes skills reset` as the normal cross-machine workflow.
6. Start a new Hermes session or use `/reset` after the filesystem sync so the new content enters a fresh cached context.
7. Verify the active content with `skill_view`; compare hashes only when strict byte-level proof is required.

## Quick Reference

```text
pull → work locally → export local skills to repo → inspect diff
→ commit → pull/merge again → diff --check → push
→ pull on other machine → repo-to-local sync → /reset
```

Important distinction:

```text
git pull/push synchronizes the shared repository
local-to-repo export publishes skills created on a machine
repo-to-local sync installs the repository copy into Hermes runtime
/reset reloads the session context
```

Never auto-commit or auto-push the export: keeping the diff visible is what makes concurrent edits from two machines mergeable.

## Procedure

### 1. Use Git as the shared boundary

The repository's `skills/` tree is the shared source between machines, but local skill edits must be explicitly exported into it before they can travel. On Windows, use `deploy/sync-skills-to-repo.ps1`; on other platforms use an equivalent additive copy that excludes runtime metadata. Do not push credentials, profile state, caches, or curator artifacts.

### 2. Inspect before committing

After export, check `git status`, review the complete skill diff, and run `git diff --check`. Preserve repository-only skills. If both machines changed the same skill, pull/merge and resolve the Git conflict deliberately; never let a blind push or mirror delete the other machine's version.

The user's required pre-push order is strict: export local skills, inspect the diff, then fetch/pull the remote and resolve conflicts before committing or pushing. If the remote changed after a local commit, pull/rebase or merge again, rerun `git diff --check`, and only then push. Never use `hermes skills reset` to distribute changes between machines; the repository export/import helpers plus Git are the source of truth. The Windows helper is manifest-aware: unchanged local copies receive upstream skill edits, while customized local skills are preserved and reported. Its export is additive/update-only and rejects stale checkouts before copying.

### 3. Sync the other machine

After the reviewed commit is pushed, the other machine pulls the repository and runs the forward repo-to-local sync helper. Ordinary runtime sync is not a reverse export, and `hermes skills reset` is not required for the normal two-machine workflow. Use reset only for an explicit one-skill replacement decision, not as the default distribution mechanism.

### 4. Verify the active copy

Use `skill_view` for the skill name and check the version, newly added sections, and linked reference files. For strict byte-level verification, compare hashes of the repository `SKILL.md` and profile-local `SKILL.md` using `terminal`. Verify references as well as the main file.

### 5. Respect session caching

A running conversation may retain the previous skill content. Use `/reset` or launch a new session after synchronization. Do not claim that a running session has adopted a skill update merely because the file on disk changed.

### 6. Repeat per profile and machine

Profiles are isolated. A successful update in the default profile does not update named profiles. Run the same verification for every profile that should receive the skill, using that profile's `$HERMES_HOME`.

## Pitfalls

- Do not report distribution complete after `git pull` without checking the active profile copy.
- Do not assume repo-to-local sync is reverse synchronization; local edits need an explicit export step.
- Do not use `/MIR` or a destructive mirror for local-to-repo export; repository-only skills must survive.
- Do not auto-commit or auto-push exported skills; inspect the diff so two-machine conflicts remain visible.
- Do not push before a final fetch/pull, conflict check, and `git diff --check`.
- Do not copy `.env`, auth files, session databases, bundled manifests, usage/curator state, caches, or lock files into the shared skill tree.
- Do not forget `/reset` or a fresh session; prompt caching can preserve old skill instructions.
- Do not claim a hash match without actually comparing both files.
- **Windows MSYS Bash `git -C` path pitfall**: Running `git -C "/d/Taadaa/..."` fails with `fatal: cannot change to ...: No such file or directory` on Windows git.exe. Always use `(cd "$dir" && git ...)` or Windows path syntax `git -C "D:/Taadaa/..."`.
- **Multi-remote Fork vs Upstream pitfall**: In repos with both `origin` (upstream) and `fork` (farm remote, e.g. `D:/Taadaa/Hermes`), never run bare `git pull` (refuses to merge unrelated histories). Always explicitly target `git pull fork main`.
- **Hardcoded Username Path in Shell Hooks**: Mọi file hook Python/Shell dùng chung giữa các máy (Kibe ↔ Admin) TUYỆT ĐỐI KHÔNG hardcode username (ví dụ: `C:\Users\Kibe\...`). Bắt buộc phải dùng `Path.home()` hoặc `Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))` để tương thích khi chạy trên máy Admin (`C:\Users\Admin`).
- **Shell Hooks Consent Allowlist (`shell-hooks-allowlist.json`)**: Khi khai báo hook mới trong `config.yaml`, Hermes kiểm tra phê duyệt tại `shell-hooks-allowlist.json` (trong `%LOCALAPPDATA%\hermes\` hoặc `~/.hermes\`). Khi đồng bộ sang máy khác, BẮT BUỘC phải đồng bộ cả file `shell-hooks-allowlist.json` vào cả 2 vị trí runtime để máy đích không bị chặn xác thực hook khi chạy non-interactive/gateway.
- **Dual-Target Hooks Deployment trên Machine Đích**: `config.yaml` thường trỏ đường dẫn hook tới `python D:/Taadaa/tools/hooks/<hook>.py`. Do đó script đồng bộ trên máy đích (`apply_sync_admin.py`) phải sao chép hook vào CẢ HAI nơi: `%LOCALAPPDATA%\hermes\hooks\` VÀ `D:\Taadaa\tools\hooks\`.
- **CRITICAL ANTI-PATTERN — CẤM SCRIPT COPY TỰ ĐỘNG 1 CHIỀU LÊN ONEDRIVE CHUNG:** Tuyệt đối CẤM viết script Python ngầm (`cron`, watchdog) dùng `shutil.copy` hay `shutil.copy2` tự động đẩy mã nguồn từ máy local (`D:/Taadaa/tools`) đè lên thư mục chia sẻ OneDrive (`Taadaa_Sync_Shared`). Hành vi này sẽ GHI ĐÈ NÁT TOÀN BỘ code mới mà máy Admin sửa trên OneDrive bằng code cũ của Kibe. Thư mục code dùng chung phải dùng NTFS Junction trực tiếp (`mklink /J`) hoặc quản lý qua Git repo chung.
- **CRITICAL PITFALL — SỬA CONFIG/HOOK CỤC BỘ BỎ QUÊN 2 KÊNH PHÂN PHỐI SANG ADMIN:** Khi tắt/sửa hook Hermes hoặc cập nhật `config.yaml` trên Kibe (`$LOCALAPPDATA\hermes`), BẮT BUỘC phải cập nhật đồng thời cả 2 kênh phân phối dùng chung:
  1. Git Deploy template: `D:\Taadaa\Hermes\deploy\hermes-home\` (cho `sync-from-kibe.ps1` kéo qua `fork main`).
  2. OneDrive Shared Sync: `D:\OneDrive\Taadaa_Sync_Shared\hermes-sync\` (cho `apply_sync_admin.py` đồng bộ trực tiếp).
  Nếu chỉ fix cục bộ trên runtime Kibe, máy Admin khi chạy sync sẽ bị ghi đè lại config/hook cũ (ví dụ: Deadman switch `guard_progress_supervisor.py` không có matcher chặn đứng toàn bộ tool call của Coordinator khi đang inspect O(1)).
- **INVARIANT HOOK SAFETY — CẤM PRE-TOOL HOOK KHÔNG MATCHER CHẶN ĐỨNG COORDINATOR:** Mọi hook an toàn / supervisor đặt tại `pre_tool_call` BẮT BUỘC phải có `matcher` cụ thể hoặc cơ chế bypass cho Coordinator. Tuyệt đối CẤM cài đặt deadman switch đếm tool call mà không tính tới các phiên Coordinator chỉ đọc log / inspect không sửa file, tránh làm tê liệt toàn bộ hệ thống (`delegate_task`, `terminal`, `clarify`).

## Verification

A synchronization is complete only when:

- The intended repository commit is present on the target machine.
- Local skill edits were exported into the repository and the resulting Git diff was reviewed.
- The final pre-push pull/merge completed without unresolved conflicts.
- `git diff --check` passes before the push.
- Repo-to-local sync copied the intended skills on the receiving machine.
- `skill_view` shows the expected version and new logic from the active profile.
- References required by the skill exist in the active profile.
- A new session or `/reset` has been performed before relying on the change.
- Unrelated local changes and profile secrets remain untouched.

## Support Files

- `references/cross-machine-skill-sync.md` — concise evidence checklist and Windows/Linux/macOS command patterns.
- `references/cross-machine-hook-config-distribution-and-deadman-prevention-20260919.md` — Quy chuẩn đồng bộ 4 vị trí (Quad-Location Parity) cho Hook/Config giữa Kibe và Admin, phân tích sự cố Deadman Lockout và quy tắc thiết kế hook an toàn chống tự sát session.
- `references/two-machine-tool-sync-architecture-git-vs-onedrive-20260917.md` — Kiến trúc đồng bộ code hai chiều Kibe ↔ Admin: Phân tích bẫy mất mã nguồn âm thầm khi dùng script copy 1 chiều từ máy con lên OneDrive chung; bẫy file lock .pyc của OneDrive và giải pháp chuyển đổi toàn diện sang Git repository độc lập (GitHub Private).
- `references/onedrive-tools-sync-safety-and-anti-overwrite-20260917.md` — Quy chuẩn An toàn Đồng bộ Hai Chiều & Cấm Copy Tự Động Ghi Đè (OneDrive vs Local Tools): Phân tích bẫy mất mã nguồn âm thầm khi dùng script copy 1 chiều từ máy con lên OneDrive chung; nguyên tắc SSOT OneDrive Junction.
