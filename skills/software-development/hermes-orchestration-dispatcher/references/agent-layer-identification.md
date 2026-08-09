# Xác định lớp agent của session Hermes hiện tại (audit recipe)

Cách xác định session Hermes đang chạy ở lớp agent nào (Coordinator / worker /
subagent / kanban worker / planner-auditor). **Read-only audit** — không cần chạy
gì, chỉ đọc env + code. Đã verify 2026-08-07 trên session UI chính.

## 1. Env signals (deterministic — check trước)

```bash
env | rg -i "HERMES|KANBAN|PARENT|SUBAGENT"
echo "HERMES_KANBAN_TASK=[$HERMES_KANBAN_TASK]"
grep -A8 "^delegation:" ~/AppData/Local/hermes/config.yaml
```

| Tín hiệu | Giá trị | Kết luận |
|---|---|---|
| `HERMES_KANBAN_TASK` | set (task id) | Dispatcher-spawned kanban worker (`tools/kanban_tools.py:77` — chỉ active khi env này set) |
| `HERMES_KANBAN_TASK` | `[]` / rỗng | KHÔNG phải kanban worker → session thường |
| `HERMES_UI_SESSION_ID` | set | Session UI desktop app |
| `HERMES_SESSION_ID` hoặc `parent_session_id` | set | Là subagent con của session khác |
| `HERMES_SESSION_ID` / parent | rỗng | Session chính (root) |
| `delegation:` config | chỉ `max_iterations` (KHÔNG model/provider) | Subagent nếu spawn sẽ inherit model cha — không pin được model khác qua delegate_task |

Kết luận chuẩn cho session UI chính: **KHÔNG phải subagent, KHÔNG phải kanban
worker → main session = Coordinator** theo AGENTS.md v8 (`CODEX-DIRECT-WORKER-POLICY`).

## 2. Bản đồ code — các lớp agent trong Hermes

| Lớp | Nơi định nghĩa | Vai trò |
|---|---|---|
| 0. Gateway/Session | `gateway/session.py` (SessionEntry/SessionContext/SessionStore); `gateway/run.py` tạo `AIAgent` per turn (~dòng 13570) | Quản lý session, không phải agent |
| 1. AIAgent | `run_agent.py:396` — forwarder → `agent/agent_init.py:277` (`init_agent`) | Agent class chính |
| 2. Conversation loop | `agent/conversation_loop.py:537` (`run_conversation`) | Vòng lặp tool-calling |
| 3. Subagent | `tools/delegate_tool.py` — role `leaf`/`orchestrator`, `max_spawn_depth=1` (flat mặc định); `_MODEL_HIDDEN_TASK_FIELDS` chỉ che transport, không phải model | Worker được dispatch (đây là lớp session gọi khi cần write) |
| 4. Kanban worker/orchestrator | `tools/kanban_tools.py` — session `hermes chat` thường thấy ZERO kanban tools; worker chỉ khi `HERMES_KANBAN_TASK` set | Worker/orchestrator qua Kanban |

## 3. Phân loại theo policy (template kết quả)

- Session UI chính, model `oc/deepseek-v4-flash-free` (provider custom) → role **flash/high worker**, nhưng với tư cách session chính = **Coordinator read-only**.
- Terra/Sol (qua 9router HTTP hoặc Codex CLI) = planner/auditor **read-only** — là lớp session GỌI RA khi cần audit, không phải lớp session đang chạy.
- Write path bắt buộc: dispatch đúng 1 fresh worker subagent (inherit flash) → session verify độc lập (diff+test+CRLF), KHÔNG tin self-report.
- Spawn fail confirmed → `SUBAGENT_RUNTIME_UNAVAILABLE` → session-as-worker (fallback duy nhất).

## 4. Pitfall tooling khi audit

- `search_files` với path Windows (`D:\...` hoặc `D:/...`) có thể fail `rg: IO error ... cannot find the path specified` dù thư mục tồn tại (terminal `cd /d/...` vẫn vào được). **Workaround**: dùng terminal `cd /d/Taadaa/Hermes && rg -n "pattern" path/` thay cho search_files; đừng retry search_files >2 lần cùng path (loop).
- Audit layer KHÔNG cần chạy app — env + code locations là đủ; mọi lệnh đều read-only.
