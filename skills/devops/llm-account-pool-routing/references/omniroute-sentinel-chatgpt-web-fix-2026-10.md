# OmniRoute ChatGPT-Web Sentinel Fix (Oct 2026)

## Triệu chứng

- OmniRoute `/v1/chat/completions` trả `SENTINEL_BLOCKED` (HTTP 401/403)
- Log: `Sentinel /prepare blocked (HTTP 401)`
- Ngay sau auth thành công (GET `/api/auth/session` → HTTP 200)
- Model slug `chatgpt-web/gpt-5-6` → `Model not found` (HTTP 404)

## Root Cause (3 lỗi độc lập, tất cả cùng gây chặn)

### 1. OAI_CLIENT_VERSION/BUILD_NUMBER lỗi thời
```typescript
// Cũ (gây Sentinel reject ngay lập tức):
const OAI_CLIENT_VERSION = "prod-81e0c5cdf6140e8c5db714d613337f4aeab94029";
const OAI_CLIENT_BUILD_NUMBER = "6128297";

// Mới (Oct 2026):
const OAI_CLIENT_VERSION = "prod-a55478c3ac4c8f1df8539a0845d619d9fddce90d";
const OAI_CLIENT_BUILD_NUMBER = "12234531";
```

**Cách lấy version mới:**
```python
import urllib.request, re
req = urllib.request.Request('https://chatgpt.com/', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    html = r.read().decode('utf-8', errors='ignore')
m = re.search(r'data-build="([^"]+)"', html)
print(m.group(1))  # prod-a55478c3ac4c8f1df8539a0845d619d9fddce90d
```

### 2. `fetchDpl()` regex sai — sinh file JS rác
ChatGPT đã bỏ webpack bundle (`_next/static/chunks/webpack-*.js`), chuyển sang:
`<link rel="modulepreload" href="/cdn/assets/entry.client-go4vy0y8.js">`

OmniRoute cũ dùng regex `<script src="...">` → không tìm thấy → tự sinh `webpack-${randomHex(16)}.js`
→ OpenAI nhận thấy file JS này không tồn tại trên CDN → reject Sentinel immediately.

**Fix:**
```typescript
const FALLBACK_ENTRY_CLIENT_URL = `${CHATGPT_BASE}/cdn/assets/entry.client-go4vy0y8.js`;

// Thay regex cũ:
const scriptMatch = html.match(/<script[^>]+src="(https?:\/\/[^"]*\.js[^"]*)"/)
// Bằng regex mới:
const preloadMatch = html.match(/<link[^>]*rel="modulepreload"[^>]*href="([^"]*\.js[^"]*)"/);
const preloadHref = preloadMatch?.[1];
const scriptSrc = preloadHref
  ? preloadHref.startsWith("http") ? preloadHref : `${CHATGPT_BASE}${preloadHref}`
  : FALLBACK_ENTRY_CLIENT_URL;
```

### 3. Model slug prefix không được strip
OmniRoute combo/connection routing truyền vào `model = "chatgpt-web/gpt-5-6"` nhưng `MODEL_MAP` chỉ có key `"gpt-5-6"`.
Kết quả: slug = `"chatgpt-web/gpt-5-6"` → OpenAI trả `{"detail": "Model not found"}` (HTTP 404).

**Fix trong `open-sse/executors/chatgpt-web/models.ts`:**
```typescript
export function resolveChatGptModel(model, _body, _providerSpecificData) {
  const cleanModel = model.replace(/^(?:chatgpt-web|cgpt-web)\//, '');
  const slug = MODEL_MAP[cleanModel] ?? MODEL_MAP[model] ?? cleanModel;
  const effort = MODEL_FORCED_EFFORT[cleanModel] ?? MODEL_FORCED_EFFORT[model] ?? null;
  // ... isPro check unchanged
}

export function resolveChatGptSystemHints(model) {
  const cleanModel = model.replace(/^(?:chatgpt-web|cgpt-web)\//, '');
  return [...(MODEL_SYSTEM_HINTS[cleanModel] ?? MODEL_SYSTEM_HINTS[model] ?? [])];
}
```

## Model slug thực tế (Oct 2026)
ChatGPT `/backend-api/models` trả về trên free accounts:
```
gpt-5-6       → GPT-5.6 Luna
gpt-5-3-mini  → GPT-5.3 Mini
gpt-5-6-mini  → GPT-5.6 Luna
gpt-6         → GPT-6
gpt-6-mini    → GPT-6
auto          → Auto
```

**Mapping OmniRoute model safe:** dùng `gpt-5.6-luna-free` → maps to slug `auto` (luôn hoạt động với free account).

## Build & Restart Runbook (C:/Users/Kibe/OmniRoute)

```
# BẮT BUỘC theo UPDATE_RUNBOOK.md — KHÔNG dùng npm run build trực tiếp
npm run build:backend   # chỉ compile API routes, ~2-10 phút, không OOM

# Restart: kill node PID đang chạy run-next.mjs
taskkill /F /PID <pid>  # watchdog tự restart trong 5-30s

# Verify:
curl http://127.0.0.1:20129/api/health  # → {"status":"ok"}
```

**CẢNH BÁO:** `npm run build:backend` có thể chạy 10+ phút → worker `haiku_worker.py` cần timeout >= 600s.

## Cookie Nạp Vào OmniRoute
Cookie cần đầy đủ (10k+ chars): `__Secure-next-auth.session-token`, `cf_clearance`, `oai-did`, `oai-sc`, `__cf_bm`.
Thiếu Cloudflare cookies → vẫn bị 403 Turnstile dù đã vượt Sentinel.

Script: `D:/Taadaa/GPM auto/scripts/batch_rescue_chatgpt_web_16accs.py`
- Trích xuất full cookie từ GPM profile qua Playwright CDP
- Sync vào storage.sqlite + proxy_assignments + combos

## CRLF Issue với haiku_worker.py
Worker Haiku viết file TypeScript với CRLF trên Windows. Git config của OmniRoute expect LF.
→ Cần normalize sau mỗi lần worker edit:
```python
with open(path, 'rb') as f: c = f.read().replace(b'\r\n', b'\n')
with open(path, 'wb') as f: f.write(c)
```
Git diff sẽ cho thấy toàn file changed nếu CRLF còn sót → verify lại bằng `git diff --stat`.

## Commit Trail
```
be4325060 [L2-surgery] fix(chatgpt-web): update OAI_CLIENT_VERSION/BUILD_NUMBER, fix fetchDpl modulepreload regex, add model prefix stripping
```
Files: `open-sse/executors/chatgpt-web.ts` (15 ins, 14 del) + `open-sse/executors/chatgpt-web/models.ts` (5 ins, 3 del)
