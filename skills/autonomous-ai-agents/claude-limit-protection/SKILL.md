---
name: claude-limit-protection
description: "Enforce Claude CLI usage limits: block at 85% of 5h session limit and 90% of weekly quota. Mirrors Codex limit protection rules."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Claude, CLI, Limit-Protection, Quota, Safety]
    related_skills: [claude-code, codex, agent-model-routing]
---

# Claude CLI Limit Protection Rule

References:
- `references/claude-cli-windows-execution-and-tool-pitfalls.md` — Khắc phục lỗi treo pipe MSYS, bẫy 'Error: Reached max turns' (bắt buộc `--tools ""` cho one-shot review), foreground timeout 60s và dọn dẹp tiến trình mồ côi (03/10/2026).
- `references/claude-opus-5-5-upgrade-and-native-cli-update.md` — Nâng cấp Claude Code CLI lên native v2.1.281+ qua `claude install latest` và cấu hình Claude Opus 5.5 (`claude-opus-5-5`, 1M context, mandatory reasoning) làm model mặc định (24/09/2026).
- `references/hard-guard-pre-tool-call-enforcement.md` — Sự cố vi phạm chạm trần 100% Claude Pro, thất bại của luật mềm và kiến trúc Hard Guard PreToolUse chặn đứng vật lý tại `farm-coordinator-guard` (06/09/2026).
- `references/session-limit-reset-window-handling.md` — Dấu hiệu nhận biết lỗi 5h session limit ('You've hit your session limit · resets 2:40pm'), cập nhật cache claude_lockout.json và quy trình auto-fallback sang OmniRoute combo review (08/09/2026).

## Overview
Prevent Claude Code CLI usage when approaching Anthropic API limits to avoid session disruption and quota exhaustion. Mirrors existing Codex limit rules.

## Limit Thresholds

| Limit Type | Threshold | Action |
|------------|-----------|--------|
| **5-hour session window** | 85% (4h 15m) | **BLOCK** new Claude CLI tasks |
| **Weekly quota** | 90% | **BLOCK** new Claude CLI tasks |
| **Warning zone** | 70% 5h / 80% weekly | Log warning, allow with caution |

## Enforcement Rules (Two-Tier Architecture: Hard Guard + Self-Tracking)

### 🛑 CRITICAL LESSON: Soft Rule Failure & Hard Guard Requirement
- **Hard Truth:** Claude Pro accounts on Claude Code CLI **KHÔNG** trả về `% quota` qua `claude auth status --text` (lệnh này chỉ in Login method/Org/Email).
- Nếu chỉ dùng "luật mềm" (nhắc agent trong prompt/memory), khi gặp task khó agent sẽ dễ sơ suất gọi `claude -p --model opus --effort max` nhồi prompt lớn, đốt sạch quota và chạm trần 100% dẫn đến lockout hàng giờ.
- **BẮT BUỘC:** Mọi quy tắc quota BẮT BUỘC phải được cưỡng chế bằng **Hard Guard bằng code** tại `pre_tool_call` hook (`farm-coordinator-guard`), chặn đứng vật lý (`action: "block"`) trước khi lệnh terminal được thực thi!

### 1. Hard Guard Intercept (Plugin `farm-coordinator-guard`)
Trước khi cho phép bất kỳ lệnh terminal nào chứa `\bclaude\b`:
1. **Kiểm tra Lockout Cache (`claude_lockout.json`):**
   - Nếu `locked_until > now`: Chặn đứng vật lý ngay lập tức, trả thông báo lỗi chỉ rõ thời gian mở khóa (ví dụ: `resets 16:40 (Asia/Bangkok)`), ép fallback sang OmniRoute `:20129`.
2. **Kiểm tra Self-Tracking Quota (`claude_usage.json`):**
   - Đếm số lượt gọi trong cửa sổ 5h (`window_5h = now - 5 * 3600`).
   - Tính trọng số: lệnh thường = 1; `--model opus` / `claude-opus-5-5` = 2x; `--effort max` = 2x (tổng weight = 4 cho Opus Max). (Lưu ý: Mặc định CLI đã chuyển sang Claude Opus 5.5 `claude-opus-5-5` từ 24/09/2026 với native build v2.1.281+ qua `claude install latest`).
   - Ngưỡng 85%: Nếu `(total_weight + weight) >= 38` (trên tổng trần 45 calls chuẩn Pro): **Chặn đứng vật lý (`action: "block"`)**, không cho lệnh chạy.
3. **Fallback Bắt Buộc:**
   - Fallback sang OmniRoute Review `:20129`: model `review` (chuỗi Opus -> Sonnet -> GPT OSS -> Nemotron -> AG) hoặc `auto/claude-opus`.

### 2. Lockout Detection & Auto-Cache (Post-Tool Detection)
Khi lệnh `claude` trả về lỗi rate limit (ví dụ: `You've hit your session limit · resets 4:40pm (Asia/Bangkok)`):
- Tự động ghi nhận `locked_until` vào `claude_lockout.json`.
- Mọi lượt gọi tiếp theo sẽ bị Hard Guard chặn đứng ngay tại cửa ngõ (<1ms, zero overhead, không gọi subprocess).
- Khi hết hạn lockout, file tự động được dọn dẹp và mở lại quyền gọi.

### 4. Fallback Routing
When blocked, auto-route to:
1. **OmniRoute** (ag-gemini-pool-3) for coding tasks
2. **Codex CLI** (if available and within its limits)
3. **9Router** (gpt-5.6-luna/terra/sol) for reasoning tasks

## Implementation for Hermes

### Agent-Side Check (in terminal calls)
```python
# Pseudo-code for pre-flight check
def check_claude_limits():
    result = terminal("claude auth status --text")
    # Parse output for "5h window: XX%" and "Weekly: YY%"
    if parse_5h_pct(result) >= 85 or parse_weekly_pct(result) >= 90:
        raise LimitExceededError(...)
```

### Skill Integration
Add to delegation context when spawning Claude Code tasks:
```yaml
context: |
  PRE-FLIGHT: Run `claude auth status --text` first.
  IF 5h >= 85% OR weekly >= 90% → ABORT, use OmniRoute instead.
  IF 5h >= 70% OR weekly >= 80% → WARN, use --max-turns 5, --effort low.
```

## Monitoring Commands

| Command | Purpose |
|---------|---------|
| `claude auth status --text` | Human-readable usage |
| `claude auth status` | JSON output (scriptable) |
| `/usage` | In-session detailed breakdown |
| `/cost` | Token usage with cache hits |

## Integration with Hermes Config

Add to `config.yaml` under `delegation` or `model_catalog`:
```yaml
delegation:
  claude_limit_check: true
  claude_5h_threshold_pct: 85
  claude_weekly_threshold_pct: 90
  fallback_on_limit: omni  # or 9router
```

## Error Message Format
```
❌ CLAUDE_LIMIT_EXCEEDED
   5-hour window: 87% (threshold: 85%)
   Weekly quota: 82% (threshold: 90%)
   → Routing to OmniRoute (ag-gemini-pool-3)
```

## Exceptions
- **Emergency fixes** (user explicitly overrides with `--force-claude`)
- **Read-only operations** (`/review`, `/cost`, `/context`, `auth status`)
- **Session resumption** (`-c` or `-r` flags) — may complete existing work

## Related Skills
- `claude-code` — Main Claude Code delegation skill
- `codex` — Codex CLI delegation (has similar limits)
- `agent-model-routing` — Auto-route based on difficulty/limits