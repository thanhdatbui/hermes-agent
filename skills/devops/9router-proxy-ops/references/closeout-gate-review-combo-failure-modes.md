# Closeout Gate — `review` Combo Failure Modes & Triage

## Cấu trúc combo `review` (canonical, 2026-10-15)
```
Tier 0: chatgpt-web-pool  (ChatGPT Web round-robin, primary reviewer)
Tier 1: codex-terra        (Codex Terra least-used, fallback reviewer)
Tier 1: ag-opus-pool       (Claude Opus 4.6 Thinking, 78 Antigravity accounts)
Tier 2: oc/nemotron-3.5-lightning-free
Tier 3: openrouter/nvidia/nemotron-3-super-120b-a12b:free
Tier 4: oc/muse-spark-1.3-contributor-free
Tier 5: oc/muse-spark-1.2-contributor-free
```

## Kiểm tra trạng thái combo nhanh (O(1))
```python
import urllib.request, json
data = json.load(urllib.request.urlopen('http://127.0.0.1:20129/api/combos'))
for c in data['combos']:
    if c['name'] == 'review':
        for m in c.get('models', []):
            print(m['id'], m.get('kind'), m.get('comboName') or m.get('model'))
```

## Smoke-test từng tier (bắt buộc trước khi chạy closeout_gate)
```python
import urllib.request, json, time

for m in ['chatgpt-web-pool', 'codex-terra', 'ag-opus-pool', 'ag-gemini-pool-3']:
    t0 = time.time()
    req = urllib.request.Request(
        'http://127.0.0.1:20129/v1/chat/completions',
        headers={'Content-Type': 'application/json'},
        data=json.dumps({'model': m, 'messages': [{'role':'user','content':'1'}],
                         'max_tokens': 5, 'stream': False}).encode()
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f'{m}: OK ({time.time()-t0:.1f}s)')
    except Exception as e:
        print(f'{m}: FAIL ({time.time()-t0:.1f}s) -> {e}')
```

## Failure modes đã quan sát

### chatgpt-web-pool timeout (Cloudflare / stale cookie)
- Symptom: `review` model request treo 300s, no upstream log entries for chatgpt-web tier.
- Cause: Toàn bộ ChatGPT-Web accounts bị Cloudflare Turnstile invalidation hoặc session cookie hết hạn.
- Fix ngắn hạn: Closeout gate với `--model ag-gemini-pool-3` hoặc `--model ag-sonnet` nếu `chatgpt-web-pool` down.
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/tools --files follow_health_helper.py --model ag-gemini-pool-3 --json-output
  ```
- Fix dài hạn: Làm mới session cookie ChatGPT-Web qua GPM login + CDP extract `__Secure-next-auth.session-token`.

### codex-terra 503 ALL_TARGETS_SKIPPED
- Symptom: `HTTP Error 503: Service Unavailable` với thời gian < 2s, không có upstream request nào.
- Cause: Tất cả Codex Terra accounts đang trong cooldown / quota exhausted.
- Triage: `GET http://127.0.0.1:20128/api/connections?provider=codex` — kiểm tra trạng thái từng account.
- Fix: Chờ cooldown reset (thường 1-4h) hoặc thêm Codex account mới qua OAuth endpoint `:20128`.

### ag-opus-pool cooldown 122h
- Symptom: Log OmniRoute: `antigravity | all 1 active accounts cooling down for model claude-opus-4-6-thinking (reset after 122h)`
- Cause: Toàn bộ Claude Opus accounts trên tất cả Antigravity connections đang trong thời gian cooldown dài (5 ngày).
- Triage: Không cần tắt pool — chờ tự reset. Fallback sang `ag-gemini-pool-3` hoặc `ag-sonnet` combo.
- Lưu ý: Log `[Encryption] Decryption failed. Ciphertext prefix: enc:v1:...` cùng với cooldown log là bình thường — đây là OmniRoute đang cố đọc thông tin credential encrypted cho các account đang cooldown.

### Các model tier thấp hơn (nemotron, muse-spark) timeout/403
- Symptom: `HTTP Error 403: Forbidden` (opencode tier expired) hoặc timeout.
- Cause: OpenCode quota hết, hoặc route bị block. Không nên dùng các model này làm fallback Reviewer vì không đủ reasoning.
- Fix: Không cần action — đây là tier emergency safety net, không dùng cho review code thực tế.

## Khi `review` combo hoàn toàn không khả dụng → Thủ tục Closeout an toàn

1. **Xác nhận ag-gemini-pool-3 đang hoạt động** (model dự phòng reviewer hợp lệ):
   ```python
   # Test nhanh — phải OK trong < 15s
   import urllib.request, json
   req = urllib.request.Request('http://127.0.0.1:20129/v1/chat/completions',
       headers={'Content-Type': 'application/json'},
       data=json.dumps({'model': 'ag-gemini-pool-3',
                        'messages': [{'role':'user','content':'ping'}],
                        'max_tokens': 5}).encode())
   with urllib.request.urlopen(req, timeout=15) as r:
       print('ag-gemini-pool-3 OK:', json.loads(r.read())['choices'][0]['message']['content'])
   ```

2. **Patch `ALLOWED_REVIEW_MODELS` tạm thời** trong `closeout_gate.py`:
   - Thêm `"ag-gemini-pool-3"` vào set `ALLOWED_REVIEW_MODELS`.
   - Chạy gate với `--model ag-gemini-pool-3`.
   - Revert patch sau khi `review` combo phục hồi.

3. **Thứ tự ưu tiên fallback reviewer** (từ tốt nhất đến chấp nhận được):
   1. `review` (combo chuẩn — dùng khi hoạt động bình thường)
   2. `ag-gemini-pool-3` (Gemini Pro 16 accounts — reasoning đủ mạnh cho code review)
   3. `ag-sonnet` (Claude Sonnet — đủ capability, ít quota hơn opus)
   4. `gpt-web-luna` (Luna free — backup cuối, chỉ dùng khi tất cả bên trên fail)

## Kiểm tra nhanh sức khỏe tổng thể OmniRoute (:20129)
```python
import urllib.request, json
# Health endpoint (không timeout như /v1/models)
data = json.load(urllib.request.urlopen('http://127.0.0.1:20129/api/health', timeout=5))
print('Status:', data['status'])  # 'ok' nếu process còn sống

# Xem danh sách combo (nhanh < 2s)  
data = json.load(urllib.request.urlopen('http://127.0.0.1:20129/api/combos', timeout=5))
print('Combos:', [c['name'] for c in data['combos']])

# /v1/models CHẬM (~5s, 850KB) — chỉ dùng khi cần verify model count
```

## Lưu ý quan trọng
- `/api/health` trả về `{"status":"ok"}` KHÔNG có nghĩa là combo `review` đang hoạt động — process sống nhưng upstream providers có thể hoàn toàn bị block.
- `chatgpt-web-pool` và `ag-opus-pool` timeout silently (không log lỗi ngay) — phải đợi `targetTimeoutMs` (60s) mới fallback.
- `Encryption Decryption failed` logs là bình thường khi account trong cooldown — không phải lỗi cần xử lý.
