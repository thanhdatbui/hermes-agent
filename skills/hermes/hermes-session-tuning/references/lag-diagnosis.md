# Chẩn đoán Hermes session lag

## Bước 1 — Process (kiểm tra RAM/CPU loại trừ)
```bash
# BẮT BUỘC single-quote ngoài, $_ không bị bash nuốt:
powershell.exe -NoProfile -Command 'Get-Process | Sort-Object WS -Descending | Select-Object -First 20 Name,Id,CPU,@{n="MemMB";e={[math]::Round($_.WS/1MB)}} | Format-Table -AutoSize | Out-String -Width 200'
```
- `Hermes.exe` PID cha = main; `--type=renderer` con = UI (đây là cái lag khi cuộn/gõ, ~800MB với session nặng)
- `msedgewebview2` ~1.1GB là WebView của desktop app — bình thường
- `python -m hermes_cli.main serve` = backend agent (PID 36088 dạng này); mỗi slash_worker = 1 session active

## Bước 2 — Per-session API stats (parser python)
```bash
python3 - <<'EOF'
import re, os, collections
pat = re.compile(r'\[(\d{8}_\d{6}_\w+)\].*API call #\d+.*in=(\d+).*out=(\d+).*latency=([\d.]+)s')
stats = collections.defaultdict(lambda: {'n':0,'in':0,'lat':0.0,'maxlat':0.0,'maxts':''})
for f in ['agent.log','agent.log.1']:
    p = os.path.join(os.path.expanduser('~'),'AppData','Local','hermes','logs',f)
    try:
        for line in open(p, encoding='utf-8', errors='replace'):
            m = pat.search(line)
            if not m: continue
            s, tin, lat = m.group(1), int(m.group(2)), float(m.group(4))
            st = stats[s]
            st['n']+=1; st['in']+=tin; st['lat']+=lat
            if lat>st['maxlat']: st['maxlat']=lat; st['maxts']=line[:19]
    except FileNotFoundError: pass
for s,st in sorted(stats.items(), key=lambda x:-x[1]['n']):
    print(f"{s}: calls={st['n']} avg_in={st['in']//max(st['n'],1)} avg_lat={st['lat']/max(st['n'],1):.1f}s max_lat={st['maxlat']:.1f}s @ {st['maxts']}")
EOF
```
Tiêu chí: `avg_in` ~300K+/call → thủ phạm (context bloat). `avg_lat` 10s+ = token-heavy, không phải network.

## Bước 3 — Compression events
```bash
grep -h 'Preflight compression' ~/AppData/Local/hermes/logs/agent.log | tail -10
grep -h 'context compression started\|context compression done' ~/AppData/Local/hermes/logs/agent.log | tail -10
```
- `Preflight compression: ~527,538 tokens >= 524,288 threshold` = sắp bị nén
- `messages=716->554 rough_tokens=~203,885` = nén xong, session vẫn còn 554 messages → UI vẫn nặng

## Bước 4 — Phân biệt Hao Quota do Prompt Bloat vs Tần suất Call (Volume Surge)
Khi user hỏi "có cập nhật gì nặng lên mỗi prompt không, sao hôm nay hao quota hơn hẳn":

```bash
python3 - <<'EOF'
import glob, os, re, collections
from datetime import datetime

pat_call = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?API call #(\d+):.*?model=([^\s]+).*?in=(\d+).*?out=(\d+)')
log_files = glob.glob(os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes', 'logs', 'agent.log*'))

by_day = collections.defaultdict(lambda: {'count': 0, 'in_tok': 0, 'first_turns': []})
for lf in log_files:
    try:
        for line in open(lf, encoding='utf-8', errors='replace'):
            m = pat_call.search(line)
            if not m: continue
            dt_str, call_n, model, tin = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            day = dt_str[:10]
            by_day[day]['count'] += 1
            by_day[day]['in_tok'] += tin
            if call_n == 1:
                by_day[day]['first_turns'].append(tin)
    except FileNotFoundError: pass

print(f"{'Date':<10} | {'Calls':>6} | {'Total In':>10} | {'Avg In':>8} | {'Base Turn 1 (Min)':>18}")
print("-" * 65)
for day in sorted(by_day.keys()):
    d = by_day[day]
    tot_m = f"{d['in_tok'] / 1e6:.1f}M"
    avg_in = d['in_tok'] // max(d['count'], 1)
    min_t1 = min(d['first_turns']) if d['first_turns'] else 0
    print(f"{day:<10} | {d['count']:>6} | {tot_m:>10} | {avg_in:>8} | {min_t1:>18} tok")
EOF
```

- **Prompt Bloat thật sự**: `Base Turn 1 (Min)` tăng vọt (vd từ 21K lên 50K+) hoặc `Avg In` tăng mạnh dù cùng dạng task → kiểm tra `system_prompt`, `MEMORY.md`, danh mục skills hoặc `AGENTS.md`.
- **Volume Surge (nguyên nhân phổ biến)**: `Base Turn 1` và `Avg In` giữ nguyên (vd ~21.8K và ~176K/call), nhưng số lượng `Calls` tăng gấp 2-3x trong ngày do nhiều DM threads / Telegram groups chạy song song giờ cao điểm.
- **Dấu hiệu cạn pool OmniRoute/9Router**: xuất hiện các file `sessions/request_dump_*.json` với mã lỗi `503 ALL_TARGETS_SKIPPED` (`all targets were skipped by pre-dispatch filters / capability pre-filter narrowed the pool and remaining targets quota-exhausted`).

## Ngưỡng nén thực tế
- Config: `compression.threshold` (0.5 default), `target_ratio` (0.2), `protect_last_n` (20)
- ctx deepseek qua 9router = 1,048,576 → threshold 0.5 = nén ở ~524K; 0.3 = ~314K; 0.2 = ~210K
- `DEEPSEEK_V4_REASONING_EFFORTS = ("low","high","max")`, default effort deepseek = "high"
- Config mới chỉ áp cho session mới (reasoning_config + compression resolve lúc session init)

## Config đã set máy này (2026-08-06)
- `compression.threshold: 0.3` (trước 0.5)
- `agent.reasoning_effort: max`, `reasoning_overrides: {gemini/gemini-3.6-flash: high}`
- Model: `cmc/deepseek/deepseek-v4-flash` @ custom:9router `http://127.0.0.1:20128/v1`
