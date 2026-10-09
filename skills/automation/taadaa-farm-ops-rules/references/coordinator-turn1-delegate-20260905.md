# Coordinator Turn 1 Delegate Rule (User chốt 2026-09-05)

## Rule
Coordinator (session chính) CẤM dùng terminal/write_file để query DB, inspect log, debug, hoặc bất kỳ thao tác trực tiếp nào. Mọi tác vụ PHẢI delegate qua `delegate_task` worker từ Turn 1.

## Ngoại lệ
- `python D:/Taadaa/tools/inspect_machine.py <N>` — inspection O(1) cho farm alert.

## Provider Failure Handling
Khi delegation provider fail liên tiếp (>=2 lần Connection error hoặc timeout):
1. Chuyển sang model/provider khác trong cùng combo hoặc fallback chain
2. VD: `ag-gemini-pool-3` (9router) down 4 lần → chuyển `opencode-free` hoặc model khác
3. KHÔNG tự ý chạy session chính để "tiết kiệm thời gian"
4. Nếu tất cả providers fail → báo user, KHÔNG retry vô hạn

## Session Stats Technique
Khi cần thống kê session activity (user requests, active sessions, delegation counts):
- Query trực tiếp `C:/Users/Kibe/AppData/Local/hermes/state.db` qua Python sqlite3
- Tables chính: `messages` (role, timestamp, session_id), `sessions` (id, title), `async_delegations`
- Filter by `timestamp >= <epoch_1h_ago> AND timestamp < <epoch_now>`
- Python `datetime.datetime.now().timestamp()` cho epoch UTC+7

## Lessons Learned
- 4 lần delegate `ag-gemini-pool-3` đều fail Connection error — provider đang down
- Session chính chạy terminal dù đã rule → user frustrated 3 lần liên tiếp
- Memory đã lưu rule, skill tham chiếu file này
