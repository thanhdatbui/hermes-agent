# channel_overrides — gắn group Telegram ↔ repo (worked example 2026-08-08)

Máy user: HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes` (Windows, git-bash).

## 1. Lấy chat_id + tên group

```bash
# session keys trong log → chat_id
grep -oE "telegram:group:-[0-9]+:[0-9]+" "$HOME/AppData/Local/hermes/logs/gateway.log" | sort -u

# map tên group → chat_id từ sessions.json (display_name)
python - <<'EOF'
import json
d = json.load(open(r'C:\Users\Kibe\AppData\Local\hermes\sessions\sessions.json', encoding='utf-8'))
for k, v in d.items():
    if isinstance(v, dict) and 'group:' in k:
        print(k.split(':')[3], '→', v.get('display_name'), '| session:', v.get('session_id'))
EOF
```

Group tên gõ tắt không cần sửa (vd "Tikok Reg" = repo Tiktok_Reg) — map theo nghĩa, đối chiếu `ls -d /d/Taadaa/*/`.

## 2. Ghi override (KHÔNG nháy key âm!)

```bash
# ✅ đúng: key không nháy
hermes config set gateway.platforms.telegram.channel_overrides.-5435853713.system_prompt "<prompt>"

# ❌ SAi: nháy quanh key → lưu '"'"-5435853713"'"' (kèm literal quote) → override không bao giờ khớp
hermes config set 'gateway.platforms.telegram.channel_overrides."-5435853713".system_prompt' "<prompt>"
```

Triệu chứng lỗi nháy: config hợp lệ, restart OK, `/new` OK, nhưng agent KHÔNG cd repo (chạy như không có rule). Không có log lỗi.

Dọn key sai (CLI không có unset):
```python
import yaml
p = r'C:\Users\Kibe\AppData\Local\hermes\config.yaml'
cfg = yaml.safe_load(open(p, encoding='utf-8'))
ov = cfg['gateway']['platforms']['telegram']['channel_overrides']
for k in list(ov.keys()):
    if k != '<chat_id_đúng>':
        del ov[k]
open(p, 'w', encoding='utf-8', newline='\n').write(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))
```
Sau đó `hermes config check`.

## 3. Gateway restart + /new

- `hermes gateway restart` (nạp lại config; KHÔNG phải `/new`)
- `/new` trong group → session mới nạp system_prompt mới (đổi giữa chừng bị cấm vì prompt-cache invariant)
- ⚠️ restart ngắt agent đang chạy (batch upload... ) — kiểm tra process trước:
  `powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'tiktok_workflow|venv-core024'}"`

## 4. Verify bằng state.db (không tin mô tả ảnh)

```python
import sqlite3
con = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db')
cur = con.cursor()
# session group mới nhất
cur.execute("SELECT id, source, display_name FROM sessions WHERE session_key LIKE 'agent:main:telegram:group:%' ORDER BY id DESC LIMIT 3")
# message thực tế của session đó
cur.execute("SELECT role, substr(content,1,120) FROM messages WHERE session_id=? AND role!='system' ORDER BY id", (sid,))
```
Bằng chứng OK: user "chạy git status" → assistant trả "Đang ở repo D:\...\Tiktok-video (main)" + cd trước mọi lệnh.

## 5. Global rule + personalities (group mới tự nạp)

```bash
hermes config set agent.system_prompt "<rule chung>"          # mọi chat không override
hermes config set agent.personalities.ten_bo.description "..." 
hermes config set agent.personalities.ten_bo.system_prompt "..."
```
User đổi runtime: `/personality` (list) · `/personality ten_bo` (đổi, ghi config + in-memory — không restart) · `/personality none` (xóa). Override group thắng global.

## Prompts chuẩn cho repo-vận hành (đã verify hoạt động)

Mỗi override = repo + cd rule + «đọc AGENTS/HANDOFF/PROJECT_RULES» + 2 block quy tắc:
```
QUY TẮC BÁO CÁO: batch dài → KHÔNG gửi từng bước; lượt trung gian [SILENT]; chỉ 1 tóm tắt cuối (kết quả từng máy, thời gian, log path) hoặc lỗi cần xử lý. KHÔNG soạn lại lịch sử các bước.
QUY TẮC ẢNH MÀN HÌNH: máy N → serial từ config-machine-N.yaml / workbook, "C:\Program Files (x86)\xiaowei\tools\adb.exe" -s <serial> exec-out screencap -p → MEDIA:. Không cần app mirror. Không đoán serial.
```