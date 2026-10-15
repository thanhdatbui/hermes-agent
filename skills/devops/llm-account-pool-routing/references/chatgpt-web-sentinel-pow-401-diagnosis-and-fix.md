# ChatGPT Web Executor: Sentinel Proof-of-Work (PoW) 401 Diagnosis & Fix

## Bối cảnh
OmniRoute tích hợp executor `chatgpt-web` (`open-sse/executors/chatgpt-web.ts`), giả lập trình duyệt để gọi ChatGPT Web backend (`https://chatgpt.com/backend-api/conversation`).

OpenAI bảo vệ endpoint này bằng hệ thống **Sentinel Proof of Work (PoW)**:
1. Client gửi request tới `/backend-api/sentinel/chat-requirements/prepare`.
2. Server trả về challenge (dpl, client version, build number).
3. Client giải SHA-3 hash challenge và gửi token kèm header `openai-sentinel-chat-requirements-token`.

---

## 3 Triệu chứng lỗi và Nguyên nhân gốc rễ

### 1. `SENTINEL_BLOCKED` / HTTP 401 trên prepare endpoint
- **Triệu chứng:**
  ```
  [CGPT-WEB] Sentinel failed: 401
  {"error":{"message":"Sentinel rejected request: HTTP 401"}}
  ```
- **Nguyên nhân:**
  `OAI_CLIENT_VERSION` hoặc `OAI_CLIENT_BUILD_NUMBER` trong code không khớp với live site của OpenAI.
  Ví dụ: live site đã lên `prod-a55478c3ac4c8f1df8539a0845d619d9fddce90d` (build `12234531`), code OmniRoute gửi bản cũ `prod-81e0c5...` (build `12199...`).

- **Cách lấy live version:**
  ```python
  import urllib.request, re
  req = urllib.request.Request('https://chatgpt.com/', headers={'User-Agent': 'Mozilla/5.0...'})
  html = urllib.request.urlopen(req).read().decode()
  v = re.search(r'data-build="([^"]+)"', html)
  b = re.search(r'"buildNumber":(\d+)', html)
  print(f"OAI_CLIENT_VERSION = \"{v.group(1)}\"")
  print(f"OAI_CLIENT_BUILD_NUMBER = \"{b.group(1)}\"")
  ```

---

### 2. DPL cào hụt CDN Asset → Sinh file rác → HTTP 401
- **Triệu chứng:**
  Sentinel trả về 401 dù version đã đúng.
- **Nguyên nhân:**
  Hàm `fetchDpl()` cũ dùng regex:
  ```typescript
  // CŨ - ĐÃ HỎNG vì OpenAI không dùng webpack chunk nữa:
  const match = html.match(/<script[^>]+src="([^">]+_next\/static\/chunks\/webpack-[^">]+\.js)"/);
  ```
  Không tìm thấy, code fallback tự sinh file ngẫu nhiên:
  ```typescript
  return `webpack-${randomHex(16)}.js`; // OpenAI phát hiện CDN file này không tồn tại → 401
  ```
- **Fix:**
  OpenAI đã chuyển sang nạp ES Modules qua thẻ `<link rel="modulepreload">`:
  ```typescript
  // MỚI - Bắt modulepreload entry:
  const match = html.match(/<link[^>]+rel="modulepreload"[^>]+href="([^">]+\/cdn\/assets\/entry\.client-[^">]+\.js)"/);
  // Hoặc fallback về một entry point có thật trên CDN:
  const fallback = '/cdn/assets/entry.client-go4vy0y8.js';
  ```

---

### 3. Model prefix stripping (`chatgpt-web/auto` → `auto`)
- **Triệu chứng:**
  OpenAI trả về `404: {"detail":"Model not found"}`.
- **Nguyên nhân:**
  Khi client gọi tới OmniRoute với model có tiền tố provider như `chatgpt-web/gpt-5-6` hoặc `cgpt-web/auto`, hàm `resolveChatGptModel()` tra `MODEL_MAP` bằng toàn bộ chuỗi có tiền tố. Vì `MODEL_MAP` chỉ có key dạng `gpt-5-6`, tra cứu trả về undefined → gửi nguyên chuỗi `chatgpt-web/...` lên OpenAI → OpenAI trả về 404 Model not found.
- **Fix trong `open-sse/executors/chatgpt-web/models.ts`:**
  ```typescript
  export function resolveChatGptModel(model: string): string {
    const cleanModel = model.replace(/^(?:chatgpt-web|cgpt-web)\//, '');
    return MODEL_MAP[cleanModel] ?? MODEL_MAP[model] ?? cleanModel;
  }
  ```

---

## Free Tier vs Plus/Pro Tier Model Slugs

| Tier | Advertised Models | Backend Slug gửi lên OpenAI | Notes |
|------|-------------------|----------------------------|-------|
| Free | `auto`, `gpt-5.6-luna-free` | `auto` | Bắt buộc dùng `auto`. Gửi `gpt-5-6` hay `gpt-5.6-sol-high` đều bị 404! |
| Free + Think | `gpt-5.6-luna-free-thinking` | `auto` | Gửi kèm `system_hints: ["reason"]` |
| Plus/Pro | `gpt-5.6-sol-high`, `gpt-5-6` | `gpt-5-6-thinking` / `gpt-5-6` | Đòi hỏi tài khoản trả phí |

**Kỷ luật quan trọng cho combo:**
Tất cả các tài khoản Free (Gmail, Hotmail) trong combo `chatgpt-web-pool` **BẮT BUỘC** phải cấu hình model là `chatgpt-web/auto`. Nếu để `chatgpt-web/gpt-5.6-sol-high`, request sẽ bị 404 và làm hỏng cơ chế Round-Robin của combo.

---

## Runbook Build & Deploy sau khi sửa `chatgpt-web.ts`

1. **Chuẩn hóa Line Endings:**
   File `chatgpt-web.ts` và `models.ts` trên Windows thường bị đổi thành CRLF. Dùng script chuyển về LF để `git diff` sạch.

2. **Kiểm tra TypeScript:**
   ```bash
   cd C:/Users/Kibe/OmniRoute
   npm run typecheck:core
   # Phải 0 errors
   ```

3. **Biên dịch Backend (Windows Production):**
   ```bash
   npm run build:backend
   # CẤM chạy full 'npm run build' (Next.js 16 build full sẽ ăn hết RAM và crash)
   ```

4. **Khởi động lại Service qua Watchdog:**
   Kill tiến trình Node đang chạy port 20129:
   ```python
   import psutil
   for p in psutil.process_iter(['cmdline']):
       if 'run-next.mjs' in ' '.join(p.info.get('cmdline') or []):
           p.kill()
   ```
   Watchdog sẽ tự relaunch sau 20s.

5. **Verify Probe:**
   ```
   GET http://127.0.0.1:20129/api/health → 200 OK
   POST http://127.0.0.1:20129/v1/chat/completions (model: chatgpt-web/auto) → 200 OK
   ```
