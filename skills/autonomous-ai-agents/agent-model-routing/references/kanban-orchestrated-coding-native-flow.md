# Kanban orchestrated-coding native flow (source-verified 2026-08-15)

Cơ chế per-role model routing của Hermes Kanban — đã verify từ `D:\Taadaa\Hermes`
(`hermes_cli/kanban_db.py`, `hermes_cli/kanban_templates.py`,
`skills/software-development/kanban-orchestrated-coding/SKILL.md`, tests
`tests/hermes_cli/test_kanban_orchestrated_coding.py`).

## Vì sao không cần bịa orchestrator thứ hai

Bundled skill `kanban-orchestrated-coding` đã định nghĩa sẵn workflow graph:
root → planner → plan-auditor → executor (`plan_audit_required=true`) →
code-auditor/reviewer → summarizer. Step keys dùng `current_step_key`:
`planner`, `auditor`, `worker`, `reviewer`. Không có config template mới cần
thêm — chỉ cần khai báo roles trong config để dispatcher route đúng model.

## Cấu hình (config.yaml, root hoặc profile)

```yaml
kanban:
  orchestration:
    roles:
      planner:      # Pro lên plan (đọc repo + viết plan; KHÔNG code)
        candidates:
          - profile: taadaa-planner
            model: deepseek-v4-pro
        toolsets: [file, terminal, code_execution]
      auditor:      # Pro audit plan (read-only; viết verdict)
        candidates:
          - profile: taadaa-auditor
            model: deepseek-v4-pro
        toolsets: [file, terminal]
      worker:       # Flash implement theo plan đã APPROVED
        candidates:
          - profile: taadaa-fix-automation
            model: deepseek-v4-flash
        toolsets: [file, terminal, code_execution]
      reviewer:     # Flash review post-change
        candidates:
          - profile: taadaa-fix-automation
            model: deepseek-v4-flash
        toolsets: [file, terminal]
```

## Cơ chế resolve (source)

- `resolve_workflow_step_policy(task)` (kanban_db.py:9347): đọc
  `task.current_step_key`; nếu `kanban.orchestration.roles.<key>` tồn tại →
  chọn candidate đầu tiên (`candidate_index=0`); nếu `task.assignee` khớp một
  profile trong candidates thì chọn đúng index đó. Trả
  `WorkflowStepPolicy(step_key, profile, model, toolsets)`.
- Dispatcher (`_poll_ready_tasks` ~kanban_db.py:8800): task ready có step_key →
  resolve policy → gán assignee/model (`_apply_workflow_step_policy` ghi
  event `workflow_step_routed`) → spawn `hermes -p <profile>`; profile config
  pin model thật.
- Role key `planner`/`worker` chưa khai báo trong roles → policy None →
  không hijack broad role (không auto-routing sai).
- Toolsets role được pin qua spawn (`_default_spawn` + `model_tools`); worker
  trong `HERMES_KANBAN_TASK` context được auto-append `kanban_*` lifecycle
  tools (complete/block/heartbeat/create/...). **PITFALL:** nếu profile
  `agent.disabled_toolsets` chứa `kanban`, subtraction sau auto-append sẽ XÓA
  kanban tools → worker không có `kanban_complete`/`kanban_block`. Phải bỏ
  `kanban` khỏi disabled_toolsets của worker profiles (hit thật 2026-08-15,
  fix 1 dòng; verify bằng `get_tool_definitions` với `HERMES_KANBAN_TASK=1`).

## Vận hành

1. Tạo root task (goal, constraints, budget, acceptance) + planner task
   `current_step_key="planner"`, `workflow_template_id="kanban-orchestrated-coding"`.
2. Plan xong → auditor task (Pro) đọc plan + executor task
   (`plan_audit_required=true`, `plan_audit_max_rounds=2`) → verdict qua
   `kanban_apply_plan_audit_actuation(executor_task_id=...)` (hoặc primitive
   `kanban_record_plan_audit_verdict`); REJECT → revision planner/auditor
   round-scoped idempotency key.
3. APPROVED → worker task (Flash) code theo plan.
4. Reviewer (Flash) + verify độc lập rồi mới báo DONE.

## Mô hình chi phí (user chốt 2026-08-15)

- Coordinator hằng ngày = Flash; Pro chỉ planner/auditor phiên ngắn;
  Sol = case khó; Opus = audit gate. Pro ≤10–15% tổng traffic
  (blended = (1−s)+s·2.76; s=10% → 1.176× so với all-Flash).
- Trước khi sửa routing config: trình phương án + chi phí, chờ user duyệt.

## Lưu ý implement

- Profile `custom_providers` là LIST: `[{name:"9router", base_url, key_env,
  api_mode:"chat_completions", discover_models:false, model:"<m>",
  models:{"<m>":{context_length:1048576}}}]` — dùng chung NINEROUTER_API_KEY,
  không inline secret.
- Mọi write config qua python+yaml (atomic), không text-regex; snapshot
  baseline + rollback nếu read-back lệch.
- Repo Hermes dirty-tree: không đụng file repo; chỉ sửa local config/profile.
