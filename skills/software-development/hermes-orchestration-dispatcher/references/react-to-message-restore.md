# Restore react_to_message (feature Codex xóa khỏi working tree) — 2026-08-05

## Bối cảnh

Sau update 0.18.2 → 0.20.0, Codex sửa trực tiếp trong working tree và **gỡ toàn bộ feature message reactions** (không chỉ tool). User yêu cầu restore `react_to_message`. Session bị gián đoạn (gateway 524) **khi đang port sang cấu trúc 0.20.0 — CHƯA HOÀN THÀNH**. File này là toàn bộ investigation + plan để session sau làm tiếp.

## Feature có 3 lớp backend (Codex xóa HẾT, không phải chỉ tool)

| Lớp | File gốc (commit 7d92056c4) | Trạng thái 0.20.0 sau Codex |
|---|---|---|
| Storage (DB layer) | `hermes_state.py`: `REACTIONS_METADATA_KEY`, `set_message_reaction`, `get_message_reactions`, `take_unseen_reactions`, `latest_message_row_id`, `latest_user_message_row_id`, `get_message_role` | **Đã xóa khỏi `hermes_state.py`** (grep rỗng) |
| RPC | `tui_gateway/methods_session.py`: `@method("message.react")` | **File `methods_session.py` ĐÃ BỊ XÓA** — 0.20.0 gộp toàn bộ `@method` vào `tui_gateway/server.py` (118 methods, `def method(name)` ở dòng 1219) |
| Tool + toolset | `tools/react_to_message_tool.py` (check_fn HERMES_DESKTOP) + khai trong `toolsets.py` | **File tool đã xóa**; toolset không còn |
| Model context | `_pending_reaction_notes()` + chèn vào `run_message` (server.py `_run_prompt_submit`, cạnh SPEECH_INTERRUPTED_NOTE); `agent/conversation_loop.py` (6 dòng) | **Đã xóa** — grep `_pending_reaction_notes` rỗng; diff server.py cho thấy block bị gỡ |

Commit gốc: `7d92056c4` "feat(gateway): iMessage-style message reactions — storage, RPC, agent tool, model context" (9 files: `.plans/message-reactions.md`, `agent/conversation_loop.py`, `hermes_state.py` +221, `tests/test_message_reactions.py`, `tools/react_to_message_tool.py`, `toolsets.py`, `tui_gateway/methods_prompt.py`, `tui_gateway/methods_session.py`, `tui_gateway/server.py`).

**Frontend KHÔNG bị Codex xóa** (vẫn còn): `apps/desktop/src/store/reactions-enabled.ts` (opt-in, KEY `hermes.desktop.reactions.v1`, gửi `config.set display.message_reactions` xuống gateway), `gateway-event.ts` xử lý `message.reaction` event, `message-parts.tsx` (tool block `react_to_message` → render null trừ isError), `text-utils.ts` (emoji completions gated bởi `$reactionsEnabled`). → Frontend là dead code chờ backend. Bật UI thôi KHÔNG đủ — cần restore backend.

## Nguồn code để restore (quan trọng)

1. **Commit gốc**: `git show 7d92056c4:<path>` — có đủ DB methods, RPC body, tool, test.
2. **`runtime-sync-package-backups/<ts>/files/hermes_state.py`** (thư mục untracked do runtime-sync tạo) — **bản hermes_state.py TRƯỚC khi Codex xóa**, chứa luôn `_scrub_surrogates` (dòng 141), `_encode_display_metadata` (6150), `_decode_display_metadata` (6212), `set_message_reaction` (6493). Backup 20260805T135645096Z là bản đầy đủ.
3. **`tui_gateway/server.py.codex-backup-20260805-request-overrides`** — backup Codex tự để lại trước khi sửa (không liên quan reaction, nhưng là pattern: Codex để `*.codex-backup-*` cạnh file nó sửa).

## Khó khăn port sang 0.20.0 (KHÔNG copy nguyên commit)

- `methods_session.py` không còn tồn tại → RPC `message.react` phải **thêm vào `tui_gateway/server.py`** với đúng helper 0.20.0.
- Helper 0.20.0 còn: `_sess_nowait` (1 def), `_session_db` (1), `_db_unavailable_error` (1), `_ok`/`_err` (2), `_execute_write` (hermes_state.py:1249), `_decode_content` (hermes_state.py:3773).
- Helper 0.20.0 **THIẾU** trong `hermes_state.py`: `_decode_display_metadata`, `_encode_display_metadata`, `_scrub_surrogates`. Lấy từ backup (runtime-sync-package-backups) hoặc commit gốc — kiểm tra `hermes_state_search.py` dùng `self._decode_display_metadata` (dòng 1005-1006) nên phải tìm đúng định nghĩa (có thể ở common/search, grep toàn repo).
- Schema messages 0.20.0 **VẪN có cột `display_metadata TEXT`** (`hermes_state_common.py:276`) → DB layer port được không cần migration.
- `message.react` RPC body gốc (methods_session.py): `row_id` hoặc `newest_role` (user|assistant) + `emoji` (null = clear) + `author` (user|agent); dùng `db.latest_message_row_id(session_key, role=newest_role)` khi không có row_id; `db.set_message_reaction(...)`; trả `_ok(rid, {"row_id": int(row_id), "reactions": reactions})`; lỗi `_err(rid, 4023/4024/4025/4040/5007)`.
- Tool gốc `tools/react_to_message_tool.py` (154 dòng, check_fn HERMES_DESKTOP): lấy nguyên từ commit; cần đọc body để biết nó dùng RPC nào (qua gateway emit) và `_history_to_messages` có forward `row_id` không (commit gốc thêm `row_id` vào `_history_to_messages` trong server.py — kiểm tra 0.20.0 còn không).
- Model context: thêm lại `_pending_reaction_notes(session)` + chèn vào `run_message` trong `_run_prompt_submit` (0.20.0 đã đổi chỗ — tìm chỗ `SPEECH_INTERRUPTED_NOTE` để đặt cạnh).

## Test

Commit gốc có `tests/test_message_reactions.py` (169 dòng) — lấy nguyên, chạy với `PYTHONPATH=.` + `-p no:cacheprovider` (môi trường consumer pytest theo memory).

## Checklist hoàn thành

- [ ] `hermes_state.py`: thêm `REACTIONS_METADATA_KEY` + 6 methods (từ commit gốc, dùng `_execute_write` 0.20.0; thêm `_decode/_encode_display_metadata` + `_scrub_surrogates` nếu thiếu)
- [ ] `tui_gateway/server.py`: thêm `@method("message.react")` (port body gốc, helper 0.20.0)
- [ ] `_history_to_messages` forward `row_id` (nếu 0.20.0 chưa có)
- [ ] `tools/react_to_message_tool.py`: restore từ commit gốc + khai lại vào `toolsets.py`
- [ ] `_pending_reaction_notes` + chèn run_message trong `_run_prompt_submit`
- [ ] `tests/test_message_reactions.py` chạy xanh
- [ ] Restart app để nạp; bật UI toggle (Settings → Appearance → reactions)
