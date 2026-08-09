# Audit routing v5 — model matrix đã test + CHỐT (2026-08-07 → 2026-08-08)

User chốt hướng đổi policy audit (`D:\Taadaa\AGENTS.md` "Active Audit Routing Policy v4" → v5).
**ĐÃ GHI VÀO AGENTS.md 2026-08-08** (block "### Active Audit Routing Policy v5 (Multi-Agent Routing)",
heading sentinel + backup `.bak-v5-20260808-154454` + verify byte-identical ngoài vùng policy;
sau đó vá thêm 2 điều khoản fail-closed → `.bak-v5-fix-20260808-155539`, `rebuilt==old: True`).

## Kết quả test live (9router `localhost:20128`, key `NINEROUTER_API_KEY`)

| Model | Kết quả | Ghi chú |
|---|---|---|
| `ag/claude-sonnet-4-6` | ✅ stream OK | chấp nhận `reasoning_effort:high` |
| `ag/claude-opus-4-6-thinking` | ✅ stream OK | chấp nhận `reasoning_effort:high` |
| `cx/gpt-5.6-luna` | ✅ 200 OK | codex route |
| `cx/gpt-5.6-terra` | ✅ 200 OK | |
| `cx/gpt-5.6-sol` | ✅ 200 OK | |
| `v98/gpt-5.6-luna-max` | ❌ 429 new_api_error | "Something wrong, please try again" — lỗi UPSTREAM v98, reset 5m, KHÔNG phải quota thường |
| `v98/gpt-5.6-terra-max` | ❌ 429 new_api_error | như trên |
| `gpt-5.6-luna-max` (không prefix) | ❌ model_not_found | "No active credentials for provider: openai" |

## Claude CLI (Claude Code 2.1.186, gói Pro user)

- `claude -p "..." --model claude-sonnet-5` ✅ / `claude-opus-5` ✅ — smoke test OK.
- **PITFALL: flag `--reasoning-effort` KHÔNG tồn tại** (`unknown option`).
- Cú pháp đúng: `claude -p "..." --model claude-sonnet-5 --settings '{"reasoning":{"effort":"high"}}'` ✅.
- `claude model list` là lệnh tương tác (in model đang chạy) — headless dùng `--model <name>`.
- User: CLI = **sonnet-5 high (task medium) / opus-5 medium (task khó)**; KHÔNG dùng
  sonnet-4.6 qua CLI (sonnet-4.6 CHỈ qua 9router). Quota gate giữ nguyên
  (preflight 85%/5h + 90%/tuần).

## Ladder v5 FINAL (CHỐT 2026-08-08 — đã vào AGENTS.md)

```
AUDIT (read-only):
  1. ag/claude-opus-4-6-thinking (reasoning high) — PRIMARY planner/audit (user đổi 2026-08-09; sonnet-4-6 giữ làm legacy backup khi opus-4-6-thinking 429/401)
  2. cx GPT (9router codex): luna (dễ) / terra (khó vừa) / sol reasoning high (khó thật)
  3. Claude CLI: claude-opus-5 reasoning high — CHỈ task khó thật, quota gate
     (preflight <85% 5h AND <90% weekly), nằm TRƯỚC cx/gpt-5.6-sol [phương án A]
  4. OpenCode free (catalog động từ 9router — không hardcode list)
  5. Command Code (9Router/Claude)
ESCALATION backup: ag/claude-opus-4-6-thinking (reasoning high — khi CLI quota blocked)
```

- **ĐÃ CHỐT: bỏ hẳn sonnet-5 khỏi CLI audit** — user: "bỏ luôn sonnet 5 high, chỉ dùng
  opus5 medium cho task khó; task dễ/trung bình tự chui cx GPT trước". Claude CLI chỉ còn
  1 vai: `claude-opus-5` medium cho task khó thật (lớp 3).
- **Vá fail-closed (từ audit AG thật, verdict REJECT 5 HIGH)**: (4) `Fail-closed hard stop` —
  MỌI route fail → `AUDIT_ALL_ROUTES_FAILED: <last_error>` + dừng task, KHÔNG
  deploy/merge/commit/live-act, báo user 1 dòng; (5) `Audit route switching` — chỉ coordinator
  chuyển lớp dựa signal cụ thể (HTTP 429/401, timeout >60s, empty response, non-zero exit),
  ghi `AUDIT_ROUTE_SWITCH: layerX -> layerY, reason=<signal>`; verdict usable dừng ladder ngay.
- **Bỏ hẳn Gemini 3.6 Flash khỏi route audit** (gemini vẫn giữ làm VISION aux — cấu hình
  `auxiliary.vision` riêng, không liên quan audit).
- **Bỏ mục "fresh Codex reviewer độc lập"** (bản v4 route 6) — trùng với cx GPT route,
  cùng key 9router.
- **wrapper gemini cũ đã vô hiệu** (2026-08-08): `invoke-gemini-9router-audit.ps1`,
  `invoke-gemini-api-audit.ps1`, `invoke-gemini-audit.ps1` → stub `GEMINI_AUDIT_DISABLED_POLICY_V5`
  + exit 23 (backup `.bak-v5-*`). Primary wrapper mới = `invoke-ag-audit.ps1` (exit 0/20/21/22/1).
- One-slot làm rõ: 1 evidence audit 1 lần; worker sửa xong = evidence MỚI → re-audit hợp lệ
  (material change = mở slot mới). KHÔNG cấm audit tiếp sau khi sửa.
- **Test acc Antigravity (08-08): audit sau khi sửa.

## Model 9router đang sống (catalog dump 2026-08-07 — trích phần liên quan audit)

- `combo`: gpt-5.4, deepseek-v4-flash/pro/pro-max, opencode-free, gpt-5.6-luna/sol/terra, vision-gemini
- `freemodel/*`: gpt-5.4/5.5/5.4-mini/5.3-codex + freemodel/gpt-5.6-luna/sol/terra (08-07: 401 Insufficient balance)
- `v98/*`: claude-sonnet-4-6, claude-sonnet-5, claude-opus-4-6/4-7/5, gpt-5.6-luna/terra/sol (+ -max/-ultra variants ĐANG 429), longcat-flash, ...
- `ag/*`: claude-sonnet-4-6, claude-opus-4-6-thinking, gemini-3.6-flash-high/medium/low, gemini-pro-agent
- `cx/*`: gpt-5.6-sol/terra/luna (+ `-review` suffix), gpt-5.5/5.4/5.4-mini/5.3-codex-spark
- `gemini/*`: gemini-3.6-flash (vision aux), 3.5-flash-lite, 3.1-pro-preview, gemma-4-31b-it
- `cmc/*`: deepseek-v4-pro/flash, Kimi-K2.6/2.5, GLM-5.1/5, MiniMax-M2.7/2.5, Qwen3.6, Step-3.5-Flash
- `gc/*`: gemini-3.1-pro-preview, 3-pro-preview, 2.5-pro

## 2-profile coordinator — ĐÃ THỬ, ĐÃ DẸP (2026-08-07)

- Đã dựng profile `coordinator` (clone default) + `agent.disabled_toolsets:
  [file, terminal, code_execution, computer_use, cronjob, project, memory, image_gen, kanban]`
  → verify runtime: write tools ABSENT, delegate_task/session_search/skill_view/web/browser/vision
  PRESENT, default sha256 giữ nguyên, `hermes -p coordinator chat -q` boot OK.
- **Tại sao dẹp**: delegate_task subagent inherit enabled toolsets từ parent → worker spawn từ
  session coordinator CŨNG mất write tools → worker thật phải là process/session riêng profile
  default → spec chuyển giữa 2 session bằng copy-paste → user REJECT:
  *"vkl copy paste thôi dẹp mẹ đi, mục đích để khỏi spawn agent h biến thành copy paster"*.
- Profile đã xóa bằng `echo "coordinator" | hermes profile delete coordinator` (lệnh cần
  confirm interactive — pipe tên vào).
- **Bài học class-level**: guard coordinator-write CHỈ có thể là prompt-level mềm trên model
  flash-free (~80-90% tuân thủ, model yếu hay shortcut). Ép cứng 100% qua tool-level đều phá
  luồng delegate_task in-session (2-profile → copy-paste; chặn parent = chặn luôn worker cùng
  session). KHÔNG đề xuất lại 2-profile. Nâng tuân thủ rẻ nhất = đổi model session mạnh hơn
  (v4-pro/luna), không phải đổi cấu trúc profile.
- Lệnh tạo (nếu lỡ cần): `hermes profile create coordinator --clone --description "..."` — tạo
  kèm wrapper `coordinator.bat`. `hermes config set` KHÔNG set được LIST (chỉ bool/int/float —
  source `set_config_value` dòng 8328-8339; list string → runtime iterate từng ký tự silent
  no-op) → list phải qua python `yaml.safe_load/set/safe_dump`.
