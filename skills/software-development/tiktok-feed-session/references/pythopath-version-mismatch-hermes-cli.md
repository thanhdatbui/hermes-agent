# PYTHONPATH lệch & Hermes CLI fallback (08-07-2026)

## Vụ upload batch Tiktok-video fail: chuỗi chẩn đoán đầy đủ

### Triệu chứng (background process)
```
automation-core version mismatch: expected=0.4.40; actual=0.4.32;
runtime=D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe;
reason=metadata version did not match expected contract
```
Lịch sử: 08-03 noon schedule từng fail `ImportError: cannot import name
'FULL_SCOPE_TAKEOVER' from 'automation_core.device_lock'
(C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\...)`
— cùng root cause PYTHONPATH lệch, từng đánh sập schedule.

### Root cause
- `pyvenv.cfg` của consumer venv: `include-system-site-packages = true`, được tạo
  từ chính hermes-agent venv (`command = ...hermes-agent\venv\Scripts\python.exe
  -m venv --system-site-packages ...`).
- Hermes session export `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent;
  C:\...\hermes-agent\venv\Lib\site-packages` → xuất hiện ĐẦU sys.path của mọi
  child python → import automation_core 0.4.32 từ hermes venv thay vì local 0.4.40.
- `importlib.metadata.version()` đọc từ dist-info KHÔNG theo sys.path import —
  nên nó trả 0.4.32 (hermes) trong khi venv-core024/site-packages có
  `automation_core-0.4.40.dist-info`. Kiểm tra bằng CẢ version VÀ `__file__`.

### Chẩn đoán 3 bước
```bash
# 1. Xác nhận sai: version + file trỏ hermes venv
"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -c \
  "import importlib.metadata as m; print(m.version('automation-core')); import automation_core; print(automation_core.__file__)"
# 2. Xác nhận đúng khi sạch env
PYTHONPATH= "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -c \
  "import importlib.metadata as m; print(m.version('automation-core'))"
# 3. Kiểm tra sys.path có hermes venv ở đầu không
"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" -c "import sys; print('\n'.join(sys.path))"
```

### Fix
- Chạy script qua: `PYTHONPATH= powershell -File run_....ps1 ...`
- Hoặc `env -i PATH=... HOME=... PYTHONPATH="<consumer site-packages>;..." python ...`
  (pattern Tiktok_Reg dùng, sạch nhất — xem background process log trong session).
- **Pitfall:** `run_tiktok_upload_batch.ps1` set `$env:PYTHONPATH = Join-Path
  $projectRoot "scripts"` ở dòng 129 nhưng preflight version check chạy ở dòng
  ~64 TRƯỚC đó → vẫn dính PYTHONPATH kế thừa. Fix phải là clear ở ĐẦU script
  hoặc từ caller.
- `run-schedule-recovery-watch.ps1` set `$env:PYTHONPATH = $runnerRoot` ở dòng
  534 TRƯỚC Start-Process → không bị lệch. Vì vậy schedule recovery KHÔNG dính
  lỗi này (dùng core 0.4.37 đúng, Py3.12).

## Hermes CLI one-shot (fallback model thay Codex)

```bash
# One-shot, stdout-only, không TTY — chạy ngầm từ script/scheduler được
hermes -z "Trả lời cực ngắn tiếng Việt: 1+1 bằng mấy?" -m deepseek-v4-flash --provider 9router
# → "2"
```
- `-z` = one-shot; `-m` model; `--provider` provider (9router).
- `-Q` (quiet) CHỈ hợp với `hermes chat`, KHÔNG hợp với `-z` (unrecognized arguments).
- Path tuyệt đối (KHÔNG có trong system PATH): `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe`
- Model mặc định Hermes = `deepseek-v4-flash` / provider `9router`.

### Vì sao dùng cho recovery fallback
- `codex exec --model cmc/deepseek/deepseek-v4-flash --config model_provider="9router"`
  VẪN đi qua Codex CLI/account OpenAI → hết quota vẫn fail.
- Hermes CLI + 9router độc lập hoàn toàn với OpenAI account → fallback thật sự.
- Kiến trúc hiện tại: `build_advisor_command`/`build_repair_command` trong
  `recovery_supervisor.py` (~dòng 1213-1280) hardcode `codex exec`. Cổng
  `ready_for_fallback` (recovery_supervisor.py ~308) chỉ mở khi
  `PlannerStatus.PROVIDER_UNAVAILABLE` + evidence — cần map quota pattern
  (`usage limit|429|rate limit|quota` trong advisor-output.txt) thành
  PROVIDER_UNAVAILABLE thay vì để exit≠0 → INVALID.
