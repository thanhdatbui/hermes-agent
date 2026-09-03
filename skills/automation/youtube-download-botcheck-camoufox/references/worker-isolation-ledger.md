# Worker isolation + Ledger liên máy (download_by_niche.py) — 17/08/2026

## Worker isolation (mỗi worker: proxy riêng + cookies riêng)

Cơ chế đã code vào `download_by_niche.py`:
- `--parallel N` = folder-level: `chunks = [folder_list[i::N] for i in range(N)]` → ThreadPoolExecutor
- Mỗi worker: `set_worker(proxy_subpool=pool[i::N], cookies_file=files[i % len(files)])`
- Thread-local `_WORKER_LOCAL` → `_worker_proxy()` (xoay trong subpool, không trùng IP worker khác) + `_worker_cookies()` (ưu tiên hơn `args.cookies_file`)
- `load_proxy_pool(args)` tách ra từ `next_proxy` (cache `_PROXY_POOL`); `format_proxy(raw)` parse `host:port:user:pass` → `http://user@host:port`

Sinh N bộ cookies (mỗi lần chạy Camoufox = session khác):
```bash
for i in 2 3 4; do python -c "
from camoufox.sync_api import Camoufox
from pathlib import Path
def netscape(cookies):
    lines=['# Netscape HTTP Cookie File']
    for c in cookies:
        d=c.get('domain',''); flag='TRUE' if d.startswith('.') else 'FALSE'
        lines.append('\t'.join([d,flag,c.get('path','/'),'TRUE' if c.get('secure') else 'FALSE',str(int(c.get('expires',0) or 0)),c.get('name',''),c.get('value','')]))
    return '\n'.join(lines)+'\n'
with Camoufox(headless=True) as b:
    p=b.new_page(); p.goto('https://www.youtube.com',wait_until='domcontentloaded',timeout=60000); p.wait_for_timeout(6000)
    Path('D:/CodexRuntime/tiktok-video/youtube-cookies-$i.txt').write_text(netscape(p.context.cookies()),encoding='utf-8')"
; done
```
Rồi chạy download với `--cookies-dir D:/CodexRuntime/tiktok-video` (quét `youtube-cookies*.txt`).

## Ledger liên máy — BẮT BUỘC

Thư mục: `D:/OneDrive/SharedData/tiktok-video/global-ledger/` (OneDrive sync, 2 chiều)
- File: `Admin.jsonl`, `Kibe.jsonl` (còn nhiều file backup cũ `*-Admin-PC-*.jsonl` — `read_ledger` đọc tất cả)
- Record: `{"machine","source_url","video_id","hashes","status","folder","recorded_at"}`
- `read_ledger` → set sources/videos/hashes; `append_record` ghi file theo `--ledger-machine-id` (canonical: admin→Admin, kibe→Kibe)

Chạy download PHẢI có:
```
--global-ledger-dir "D:/OneDrive/SharedData/tiktok-video/global-ledger" --ledger-machine-id Kibe
```

## Backfill ledger từ state.db (khi quên flag)

state.db: `videos` (video_id, source_channel, folder, checked_at, status='downloaded') + `perceptual_hashes` (video_id, hash_value — **hash_value là JSON LIST string**, phải `json.loads` không `int()`)

```python
import sqlite3, json
from pathlib import Path
db=sqlite3.connect('D:/CodexRuntime/tiktok-video/state.db'); db.row_factory=sqlite3.Row
rows=db.execute("SELECT v.video_id,v.source_channel,v.folder,v.checked_at,h.hash_value FROM videos v LEFT JOIN perceptual_hashes h ON v.video_id=h.video_id WHERE v.status='downloaded'").fetchall()
ledger=Path('D:/OneDrive/SharedData/tiktok-video/global-ledger/Kibe.jsonl')
existing=set()
for line in ledger.read_text(encoding='utf-8-sig').splitlines():
    try: existing.add(json.loads(line).get('video_id') or '')
    except Exception: pass
added=0
with ledger.open('a',encoding='utf-8') as f:
    for row in rows:
        vid=row['video_id']; key=vid.split(':')[-1]
        if key in existing or vid in existing: continue
        rec={'machine':'Kibe','source_url':row['source_channel'],'video_id':vid,'status':'downloaded','folder':row['folder'],'recorded_at':row['checked_at']}
        hv=row['hash_value']
        if hv:
            try:
                parsed=json.loads(hv)
                if isinstance(parsed,list): rec['hashes']=parsed
            except Exception: pass
        f.write(json.dumps(rec,ensure_ascii=False)+'\n')
        existing.add(key); existing.add(vid); added+=1
print(f'scan: {len(rows)} | mới ghi: {added}')
```

Kết quả thật: scan 2886 → ghi 2886 (21.778 records tổng).

## Ngưỡng min-videos

- Chặn `min_videos < 42` tại `download_by_niche.py` (~line 1006) + `source_pool_builder.py` (~line 585) — sửa cả 2 khi muốn mốc 30
- min 45 → 267 sources; min 30 → 295 sources (đã loại vtv24)
- Chạy download min 30: `--min-videos 30 --target-videos 45 --max-videos 65`
