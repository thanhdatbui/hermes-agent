---
name: hermes-profile-toolsets
description: "Create & verify Hermes profiles with toolset lockdown — agent.disabled_toolsets read-only coordinator (2-profile anti-self-write setup), runtime tool verification."
version: 1.0.1
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, profiles, toolsets, disabled_toolsets, lockdown, read-only, coordinator, delegation]
    related_skills: [hermes-agent, hermes-multi-deploy, hermes-orchestration-dispatcher]
---
# Hermes Profile Creation & Toolset Lockdown

Create isolated Hermes profiles (`~/.hermes/profiles/<name>/` — or `%LOCALAPPDATA%\hermes\profiles\<name>\` on Windows) and lock them down by disabling write/exec toolsets via `agent.disabled_toolsets`. Primary use case: the 2-profile anti-self-write design — a **read-only coordinator** session that cannot write files/run code, forcing it to delegate (`delegate_task`) to a **worker** running in the default profile.

**Rule of thumb for the lockdown list** — disable every toolset that can write/execute; keep every toolset that is read-only plus `delegation` (delegate_task is the whole point of a coordinator):

```yaml
agent:
  disabled_toolsets:
    - file            # write_file + patch (also removes read_file/search_files — accepted trade-off)
    - terminal        # terminal + process
    - code_execution  # execute_code
    - computer_use    # desktop GUI control
    - cronjob         # scheduled jobs
    - project         # workspace switching (project_create/switch)
    - memory          # memory writes
    - image_gen       # image_generate — auto-enabled by subset-inference, NOT default-off!
    - kanban          # coordinator ONLY. Worker profiles (dispatcher-spawned, HERMES_KANBAN_TASK) must NOT disable kanban — the runtime auto-append is undone by the disabled-subtraction that runs last (see references/kanban-roles-and-profile-wiring.md)
```

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
