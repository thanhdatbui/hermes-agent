# GPM Local API v3 Pagination, Duplicate Profile Resolution & OmniRoute Codex Verification

## 1. GPM Local API v3 Pagination Contract (`/api/v3/profiles`)

### Pitfall (First-Page-Only Trap)
Calling `http://127.0.0.1:19995/api/v3/profiles?page=1&limit=100` does NOT return 100 profiles if the server limits per-page to 50. 
If an automation script only queries `page=1` without following `pagination.total_page`, it will see at most 50 profiles and emit a **false negative** (e.g., claiming a Gmail has no profile when it is sitting on page 2, 3, or 4).

### Canonical Pagination Implementation (Fail-Closed)
```python
import requests

def get_all_gpm_profiles(gpm_api: str = "http://127.0.0.1:19995/api/v3") -> list[dict]:
    profiles = []
    page = 1
    total_pages = None
    expected_total = None

    while True:
        res = requests.get(f"{gpm_api}/profiles?page={page}&per_page=50", timeout=10).json()
        pagination = res.get("pagination") or {}
        page_total = pagination.get("total_page")
        if not isinstance(page_total, int) or page_total < 1:
            raise ValueError(f"Invalid GPM pagination total_page={page_total!r}")

        if total_pages is None:
            total_pages = page_total
            expected_total = pagination.get("total", pagination.get("total_count"))
            if expected_total is not None and (not isinstance(expected_total, int) or expected_total < 0):
                raise ValueError(f"Invalid GPM pagination total={expected_total!r}")
        elif page_total != total_pages:
            raise ValueError(f"GPM pagination total_page changed during fetch: {total_pages} -> {page_total}")

        data = res.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError(f"GPM page {page}/{total_pages} returned empty data")
        
        profiles.extend(data)
        if page >= total_pages:
            break
        page += 1

    if expected_total is not None and len(profiles) != expected_total:
        raise ValueError(f"GPM profile count mismatch: fetched {len(profiles)}, expected {expected_total}")
    
    return profiles
```

---

## 2. Duplicate GPM Profiles & `AMBIGUOUS_GPM_PROFILE` Handling

### Pitfall (Silent Overwrite & Arbitrary Session Revive)
When building a map of `email -> profile`, using `email_map[email] = profile` silently overwrites older profiles. If two profiles exist for the same Gmail (e.g. one created recently, one created 2 years ago), the script may launch the stale or wrong profile.

### Resolution Contract
1. Group profiles into a list per email: `email_map.setdefault(email, []).append(profile)`.
2. Detect duplicates: `duplicates = {k: v for k, v in email_map.items() if len(v) > 1}`.
3. If duplicate candidates exist, **do not arbitrarily select one**. Return `AMBIGUOUS_GPM_PROFILE` and log all candidates (`id`, `profile_path`, `created_at`).
4. To safely disambiguate:
   - Launch profiles under inspection with CDP.
   - Navigate to `https://mail.google.com/mail/u/0/#inbox` and verify real authenticated inbox title: `Hộp thư đến (...) - <email> - Gmail`.
   - Keep the verified live profile, stop the obsolete duplicate, and delete it via `GET /api/v3/profiles/delete/{id}?mode=1` or `DELETE /api/v3/profiles/{id}`.

---

## 3. OmniRoute Codex Hook & Verification Routing Guard

### Pitfall (Unprefixed Model Fallback to OpenRouter 402)
When an access token is imported into OmniRoute via `POST /api/oauth/codex/import-token`, a new provider connection is created.
- If a post-import verification test sends `{"model": "gpt-5.5"}` or `{"model": "gpt-5.6-luna"}` without a fully qualified provider prefix or without binding to an active combo, OmniRoute may route the request to OpenRouter (`openrouter/openai/...`), resulting in `HTTP 402 Insufficient credits`.
- This causes false-positive failure diagnoses (e.g., misclassifying valid Codex tokens as "quota exhausted" or "broken").

### Verification Contract
1. Always pass the target connection ID in headers:
   ```python
   headers = {
       "Content-Type": "application/json",
       "Authorization": "Bearer any",
       "x-omniroute-connection-id": str(conn_id),
       "x-connection-id": str(conn_id)
   }
   ```
2. Target the exact pool model or qualified provider model:
   ```json
   {
       "model": "codex/gpt-5.6-luna-medium",
       "messages": [{"role": "user", "content": "ping"}],
       "max_tokens": 10
   }
   ```
3. Check the response provider/model: if the response indicates OpenRouter or an unexpected upstream, reject the test verification as a routing configuration error rather than an account failure.
