# Gắn chat → repo: channel_overrides (Hermes gateway)

Mục tiêu user (08-08): mỗi Telegram group = 1 repo dự án; chat trong group → agent làm việc ĐÚNG repo đó, không "đi mò".

## Sự thật từ source (hermes-agent v0.18.2)

- **Có** `ChannelOverride` (`gateway/config.py`, ~L410): per-channel override cho `model`, `provider`, `system_prompt`. Config:
  ```yaml
  gateway:
    platforms:
      telegram:
        channel_overrides:
          "<chat_id>":            # DM dùng số ID; group dùng -100...
            model: deepseek-v4-flash
            provider: custom:9router
            system_prompt: |
              Bạn phụ trách repo: D:\Taadaa\Tiktok-video
              ▸ Mọi lệnh terminal phải cd vào D:\Taadaa\Tiktok-video TRƯỚC
              ▸ Lệnh upload: python -m tiktok_workflow --config <cfg-N.yaml> --machine N --no-dry-run
              ▸ Không sửa file ngoài repo, không đọc credential
  ```
- **KHÔNG có** per-chat cwd: session gateway có biến cwd (`gateway/session_context.py` `set_session_vars(cwd)` → `agent.runtime_cwd.set_session_cwd`) nhưng `_set_session_env` (`gateway/run.py` ~L15168) gọi **không truyền cwd** → mọi chat dùng chung `config.yaml terminal.cwd` (bridge TERMINAL_CWD). `AGENTS.md`/`.hermes.md` cũng load theo cwd global đó, không theo chat.
- Vì vậy binding chat→repo = **instruction-level** (system_prompt ép cd + scoping), không phải khóa cứng. Nếu cần khóa cứng thật: mỗi repo 1 **profile** riêng (mỗi profile 1 `terminal.cwd` + 1 gateway/bot) — nặng, chỉ khi cần cách ly tuyệt đối.

## Recipe setup

1. Tạo group → add bot → **tắt Group Privacy** (BotFather → /mybots → Bot Settings → Group Privacy; sau đó phải remove + re-add bot vào group vì Telegram cache privacy lúc join).
2. Thêm group vào whitelist: `TELEGRAM_GROUP_ALLOWED_CHATS=-100xxxx` trong `.env` (hoặc config `group_allowed_chats`), và `require_mention: true` nếu không muốn bot trả lời mọi tin.
3. Lấy chat ID: nhắn 1 tin trong group → đọc `$HERMES_HOME/logs/gateway.log` dòng `session agent:main:telegram:group:-100...`.
4. Viết `channel_overrides` (cú pháp trên) → `hermes gateway restart`.
5. Test: nhắn trong group "bạn đang làm repo nào" → phải trả về đúng repo; nhắn "cd && pwd" xác nhận cwd.

## Lưu ý

- `/model` trong chat hiện bàn phím chọn provider — các entry (MoA, 9router, OpenCode Go, cockpit, Copilot, Anthropic, custom) = provider có trong config máy; số trong ngoặc = số model provider expose, không phải thứ tự. `custom` = custom_providers (máy này: cockpit localhost:60818 gpt-5.6-luna codex_responses; 9router 127.0.0.1:20128 deepseek-v4-flash chat_completions).
- Cú pháp đổi model theo phiên: `/model provider:model`.
- Cron theo repo thì dùng `workdir` của cronjob (nạp AGENTS.md của repo + cwd đúng) — không phụ thuộc gateway chat.
