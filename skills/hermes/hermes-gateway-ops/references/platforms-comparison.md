# Platform Comparison — Hermes Messaging Gateway (docs, 2026-08-08)

Nguồn: hermes-agent.nousresearch.com/docs → Messaging Platforms → Messaging Gateway.

## Danh sách platform đầy đủ

Telegram, Discord, Slack, Google Chat, WhatsApp, WhatsApp Business (Cloud API), Signal, SMS, Email, Home Assistant, Mattermost, Matrix, DingTalk, Feishu/Lark, WeCom, WeCom Callback, Weixin, BlueBubbles (iMessage), Photon (iMessage), QQ, Yuanbao, Microsoft Teams, LINE, ntfy, Raft, IRC, Buzz, SimpleX.

**Hermes Relay** (experimental): không phải platform chat — connector hệ thống front các platform (Discord/Telegram/Slack/WhatsApp) qua connector bên ngoài giữ credentials; capabilities thương lượng ở handshake.

## Capability matrix (docs)

| Platform | Voice | Images | Files | Threads | Reactions | Typing | Streaming |
|---|---|---|---|---|---|---|---|
| Telegram | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Discord | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Google Chat | — | ✅ | ✅ | ✅ | — | ✅ | — |
| WhatsApp | — | ✅ | ✅ | — | — | ✅ | ✅ |
| WhatsApp Cloud API | ✅ | ✅ | ✅ | — | — | ✅ | — |
| Signal | — | ✅ | ✅ | — | — | ✅ | — |
| SMS | — | — | — | — | — | — | — |
| Email | — | ✅ | ✅ | ✅ | — | — | — |
| Home Assistant | — | — | — | — | — | — | — |
| Mattermost | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Matrix | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DingTalk | — | ✅ | ✅ | — | ✅ | — | ✅ |
| Feishu/Lark | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WeCom | ✅ | ✅ | ✅ | — | — | — | — |
| WeCom Callback | — | — | — | — | — | — | — |
| Weixin | ✅ | ✅ | ✅ | — | — | ✅ | — |
| BlueBubbles | — | ✅ | ✅ | — | ✅ | ✅ | — |
| Photon (iMessage) | ✅ | ✅ | ✅ | — | ✅ | ✅ | — |
| QQ | ✅ | ✅ | ✅ | — | — | ✅ | — |
| Yuanbao | ✅ | ✅ | ✅ | — | — | ✅ | ✅ |
| Microsoft Teams | — | ✅ | — | ✅ | — | ✅ | — |
| LINE | — | ✅ | ✅ | — | — | ✅ | — |
| ntfy | — | — | — | — | — | — | — |
| Raft | — | — | — | — | — | — | — |
| IRC | — | — | — | — | — | — | — |
| Buzz | — | ✅ | — | ✅ | — | — | — |
| SimpleX | ✅ | ✅ | ✅ | — | — | ✅ | — |

Voice = TTS audio replies và/hoặc voice transcription. Streaming = cập nhật dần qua edit message.

## Notes từng platform

- **Telegram**: token BotFather; user ID qua @userinfobot; đầy đủ tính năng, free, không cần số ĐT public. **Khuyến nghị #1**.
- **Discord**: bot qua Developer Portal (invite scopes); agent có thể vào voice channel (`/voice join/leave`); reactions + threads. **Khuyến nghị #2**.
- **Slack**: app workspace; tốt cho team/workflow.
- **WhatsApp**: cần số ĐT + cầu whatsapp-web; **rủi ro lock số**; không threads/reactions.
- **WhatsApp Business Cloud API**: Meta Cloud API, có voice; không threads.
- **Signal**: cần số ĐT thật.
- **Email**: SMTP/IMAP; không realtime nhưng ổn định — tốt làm alert/cron báo cáo.
- **SMS**: Twilio — trả phí từng tin.
- **Feishu/Lark**: app + app secret; đầy đủ tính năng; phổ biến ở team VN (Hermes còn có toolset feishu_doc/feishu_drive).
- **Matrix / Mattermost**: self-host, team.
- **iMessage**: BlueBubbles / Photon — cần Mac/iOS ecosystem.
- **QQ / Yuanbao / Weixin / WeCom / DingTalk**: Trung Quốc; Yuanbao có toolset riêng trong Hermes (yuanbao skill: @mention, query info/members).
- **ntfy**: push notifications thuần.

## Voice

- STT auto-detect: local faster-whisper → Groq (free) → OpenAI → Mistral.
- TTS mặc định **Edge (free)**; providers: elevenlabs/openai/minimax/gemini/piper/kittentts...
- Slash trong messaging: `/voice on|off|tts|join|leave|status`.

## Slash commands trong messaging (docs)

`/new` `/reset` · `/model [provider:model]` · `/personality` · `/retry` · `/undo` · `/status` · `/whoami` (admin/user/unrestricted) · `/stop` · `/approve` · `/deny` · `/sethome` (home channel — nơi cron deliver) · `/compress` · `/title` · `/resume` · `/sessions [all] [search q]` · `/usage` · `/insights [days]` · `/reasoning` · `/voice` · `/rollback [number]` (filesystem checkpoints) · `/background <prompt>` (phiên nền riêng) · `/reload-mcp` · `/update` · `/help` · `/<skill-name>` (gọi skill).

## MEDIA: extensions được gửi native attachment

- Image: png, jpg, jpeg, gif, webp, bmp, tiff, svg
- Audio: mp3, wav, ogg, m4a, opus, flac, aac
- Video: mp4, mov, webm, mkv, avi
- Doc: pdf, txt, md, csv, json, xml, html, yaml, yml, log
- Office: docx, xlsx, pptx, odt, ods, odp
- Archive: zip, rar, 7z, tar, gz, bz2
- Book/package: epub, apk, ipa

Platform không hỗ trợ native → fallback link/plain-text.
