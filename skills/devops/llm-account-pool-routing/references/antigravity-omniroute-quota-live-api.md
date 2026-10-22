# Antigravity Pool: OmniRoute Live Quota API

## Nguồn chính xác duy nhất để kiểm tra quota Antigravity

**ĐỪNG dùng:** `pool_state.json` (local cooldown cục bộ, chỉ cập nhật sau khi bị 429)
**ĐỪNG dùng:** `quota_snapshots` SQLite table (time-series lịch sử, cũ, không sync real-time)
**ĐÚNG:** `GET http://127.0.0.1:20129/api/usage/provider-limits`

## Response Structure

```json
{
  "caches": {
    "<connection_id>": {
      "fetchedAt": "2026-10-22T16:46:26.738Z",
      "plan": "Pro",
      "quotas": {
        "gemini-3.1-flash-lite": {
          "used": 275,
          "total": 1000,
          "resetAt": "2026-10-22T18:49:06.000Z",
          "remainingPercentage": 72.53002,
          "unlimited": false,
          "fractionReported": true,
          "quotaSource": "retrieveUserQuota"
        },
        "claude-sonnet-4-6": { ... },
        "gpt-oss-120b-medium": { ... }
      }
    }
  },
  "intervalMinutes": ...,
  "lastAutoSyncAt": ...
}
```

## Quota Family Architecture (QUAN TRỌNG)

- **Gemini 3.7 flash và 3.8 flash HIGH dùng CHUNG pool** → cả hai đều tiêu thụ từ `gemini-3.1-flash-lite` quota key.
- **Window key `gemini-3.1-flash-lite`** trong `quota_snapshots` và `/api/usage/provider-limits` = Gemini family quota.
- Khi `gemini-3.8-flash-high` bị 429, tra `gemini-3.1-flash-lite.remainingPercentage` là chính xác.

## Cách ánh xạ email → connection_id → quota

```python
import urllib.request, json, os

# Step 1: Lấy danh sách connections
r1 = urllib.request.urlopen("http://127.0.0.1:20129/api/providers", timeout=5)
conns = json.loads(r1.read()).get("connections", [])
email_to_id = {c["email"]: c["id"] for c in conns if c.get("provider") == "antigravity" and c.get("email")}

# Step 2: Lấy quota cache
r2 = urllib.request.urlopen("http://127.0.0.1:20129/api/usage/provider-limits", timeout=10)
caches = json.loads(r2.read()).get("caches", {})

# Step 3: Ánh xạ từ profile đến email qua google_accounts.json
import json, os
def get_profile_email(prof_dir):
    ga_path = os.path.join(prof_dir, ".gemini", "google_accounts.json")
    if os.path.exists(ga_path):
        return json.load(open(ga_path)).get("active")
    return None

# Step 4: Filter profile sẵn sàng
def is_profile_ready(email, caches, email_to_id, now_iso, max_cache_age_mins=30):
    cid = email_to_id.get(email)
    if not cid: return False  # không có trong OmniRoute
    cache = caches.get(cid)
    if not cache: return True  # chưa dùng bao giờ = còn quota
    
    # Kiểm tra cache freshness
    fetched_at = cache.get("fetchedAt", "")
    # (thêm logic kiểm tra tuổi cache nếu cần)
    
    flash_quota = cache.get("quotas", {}).get("gemini-3.1-flash-lite")
    if flash_quota:
        rem = flash_quota.get("remainingPercentage", 0)
        reset_at = flash_quota.get("resetAt", "")
        if rem <= 0 and reset_at > now_iso:
            return False  # Thực sự hết quota, chưa reset
    return True
```

## Logic lựa chọn profile chuẩn (thay pool_state.json)

```
Profile READY = 
  is_active = 1 (từ /api/providers)
  AND (rate_limited_until IS NULL OR rate_limited_until < NOW)
  AND test_status = 'active'  
  AND backoff_level = 0
  AND email khớp google_accounts.json của folder profile
  AND gemini-3.1-flash-lite.remainingPercentage > 0 
      OR resetAt của quota đã qua (quota đã reset)
      OR không có quota snapshot (chưa dùng = còn 100%)
  AND profile không bị locked (lease)
  AND pool_state.json cooldown_until < NOW (giữ để bắt 429 tức thì trong phiên)
```

**Sort:** `remainingPercentage DESC`, tiebreak `priority ASC`

## Pitfalls

- **Cache lag:** OmniRoute refresh quota định kỳ (mặc định ~3-15 phút). Quota có thể hết sau khi cache snapshot được tạo. `pool_state.json` bắt 429 tức thì vẫn cần để xử lý gap giữa các lần fetch.
- **acc_27 / acc_24 / acc_26:** Các acc này có quota 100% trong OmniRoute cache nhưng vẫn trả về 429 vì OmniRoute OAuth token trong oauth_creds.json có thể expired. Chạy `sync_omniroute_gemini_creds.py` để sync lại token từ OmniRoute SQLite sang profile folder.
- **Window key mismatch:** AGY CLI dùng `DEFAULT_MODEL = "gemini-3.8-flash-high"` nhưng quota trong OmniRoute lưu dưới `gemini-3.1-flash-lite` (Gemini family). Đây là thiết kế đúng — chúng dùng chung pool.
- **`pool_state.json` không đồng bộ với OmniRoute:** Cooldown trong `pool_state.json` chỉ là guard cục bộ, không phản ánh trạng thái thực tế của OmniRoute. Nếu cooldown hết mà OmniRoute vẫn báo quota cạn → phải tin OmniRoute.

## Endpoint phụ hữu ích

```
GET /api/providers              → danh sách connections (email, id, isActive, priority, rateLimitedUntil)
GET /api/providers/quota-windows → window definitions per provider
GET /api/usage/provider-limits  → live quota cache (NGUỒN CHÍNH)
```
