# Per-group repo binding + global rule block (worked recipe, 2026-08-08)

Kibe machine, HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes`. All commands from git-bash.

## Common rule block (embed in EVERY repo-bound override AND in agent.system_prompt)

```
QUY TẮC BÁO CÁO: khi chạy batch/lệnh dài, KHÔNG gửi từng bước hay tool output trung gian; các lượt trung gian dùng [SILENT]; chỉ gửi 1 báo cáo tóm tắt cuối cùng (kết quả từng máy, thời gian, file log) khi hoàn tất hoặc khi có lỗi cần xử lý. KHÔNG soạn lại lịch sử các bước đã làm trong Telegram. QUY TẮC ẢNH MÀN HÌNH: khi user yêu cầu ảnh màn hình máy N — tìm serial từ D:\CodexRuntime\tiktok-video\config-machine-N.yaml hoặc workbook mapping (D:\OneDrive\Tiktok\Tik1.xlsx), chụp bằng "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p (save local rồi gửi qua MEDIA:), KHÔNG cần mở app xiaowei. Nếu không tìm được serial, báo rõ thay vì đoán.
```

## Global (auto for all non-override chats: new groups, DM)

```bash
hermes config set agent.system_prompt "Bạn là Hermes vận hành các repo dự án Taadaa. Khi user nêu repo (tên hoặc đường dẫn), cd ĐÚNG repo đó trước mọi lệnh terminal. Đọc AGENTS.md + HANDOFF.md + PROJECT_RULES.md trong repo, KHÔNG tự bịa lệnh. Không sửa file ngoài repo, không đọc credential/workbook. <COMMON>"
```

## Personality presets (switch live via /personality, no restart)

```bash
hermes config set agent.personalities.van_hanh_mac_dinh.description "Mặc định: tóm tắt kết quả cuối, im lặng giữa chừng"
hermes config set agent.personalities.van_hanh_mac_dinh.system_prompt "<global prompt above>"
hermes config set agent.personalities.van_hanh_chi_tiet.system_prompt "<no QUY TẮC BÁO CÁO — send concise per-step results>"
hermes config set agent.personalities.im_lang.system_prompt "MỌI lượt trung gian trả [SILENT]... chỉ 1 báo cáo cuối"
```
In chat: `/personality` (list) · `/personality van_hanh_chi_tiet` (switch) · `/personality none` (clear).

## Repo-bound group overrides (replace GLOBAL for that chat — embed common block!)

```bash
hermes config set gateway.platforms.telegram.channel_overrides.-5494641602.system_prompt "Bạn phụ trách repo D:\Taadaa\Tiktok_Reg (đăng ký tài khoản TikTok). Trước MỌI lệnh terminal phải cd /d/Taadaa/Tiktok_Reg. Tuân theo AGENTS.md + HANDOFF.md + PROJECT_RULES.md trong repo. <COMMON>"
# NOTE: no quotes around the leading-dash key — quoting makes the key literal ('"-5494641602"') and silently unmatched.
```
Known group map (2026-08-08):
- `-5435853713` Tiktok video → `D:\Taadaa\Tiktok-video`
- `-5494641602` Tikok Reg → `D:\Taadaa\Tiktok_Reg`
- `-5145780745` Tiktok Log In → `D:\Taadaa\tiktok-log-in`
- `-5377611430` Tiktok Luot Nuoi Acc → `D:\Taadaa\tiktok-luot nuoi acc`

## Verify after every config change

```bash
python - <<'EOF'
import yaml
cfg = yaml.safe_load(open(r'C:\Users\Kibe\AppData\Local\hermes\config.yaml', encoding='utf-8'))
ov = cfg['gateway']['platforms']['telegram']['channel_overrides']
for cid, o in ov.items(): print(cid, '| BÁO CÁO:', 'QUY TẮC BÁO CÁO' in str(o.get('system_prompt','')))
EOF
```
Stored keys must equal the bare chat_id. Then `hermes config check` + `hermes gateway restart` + `/new` in the affected chat (system prompt pins at session creation).

## Empirically proving an override reached the model

Query state.db directly (better than trusting screenshots):
- session id from `sessions/sessions.json` (`session_id` per session_key)
- `SELECT role, substr(content,1,150) FROM messages WHERE session_id='<id>' ORDER BY id` → the agent's answer should state the bound repo/cwd.