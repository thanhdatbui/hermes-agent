# OmniRoute Provider Limits: Missing Model Quota Bars & `modelCompatOverrides` Diagnosis

## 1. Symptom & Problem Statement
On the OmniRoute Usage / Provider Limits dashboard (`http://<ip>:20129/dashboard/usage`):
- A multi-account card (e.g., Antigravity Google Pro accounts) suddenly stops displaying an entire model family (e.g., no Gemini models are shown; only Claude Opus/Sonnet bars remain).
- Cards show an active status dot (green), but quota bars for expected models (`gemini-3.7-flash-tiered`, `gemini-pro-agent`, `gemini-3.1-flash-lite`) are completely absent.
- Small red text `Token expired` appears on the card header alongside the green active dot.

---

## 2. Root Cause: Two-Layer Quota Visibility Architecture

In OmniRoute (`src/app/(dashboard)/dashboard/usage/components/ProviderLimits/`):

### Layer 1: Global Model Catalog Visibility (`modelCompatOverrides` / `customModels`)
- **Location in Database**: `C:\Users\Kibe\.omniroute\storage.sqlite` → table `key_value` (`namespace = 'modelCompatOverrides'`, `key = '<provider>'`, e.g. `antigravity`).
- **Mechanism**:
  1. The frontend hook `useVisibleQuotaData` calls `/api/provider-models?provider=<provider>`.
  2. `collectHiddenQuotaModelIds` extracts all model IDs where `record.isHidden === true`.
  3. `filterHiddenModelQuotas` strips all quota entries matching the hidden list before passing data to `QuotaCardGrid`.
  4. If an admin or bulk override marked Gemini models with `"isHidden": true`, upstream quota fetched from Google Cloud Code (`v1internal:retrieveUserQuota`) is discarded by the UI filter.

### Layer 2: Operator Per-User Quota Visibility (`settings.quotaVisibility`)
- **Location in Database**: `C:\Users\Kibe\.omniroute\storage.sqlite` → table `key_value` (`namespace = 'settings'`, `key = 'quotaVisibility'`).
- **Mechanism**:
  - Controlled by the `visibility_off` icon (eye with slash) directly on individual quota rows.
  - Persisted per provider (`{ "<provider>": { "hidden": ["<modelKey>"] } }`) via `PATCH /api/settings`.
  - Independent of model catalog state — used for personal decluttering without changing global model visibility.

---

## 3. Fast SQLite Diagnostics (O(1) Inspection)

Run on host to inspect `modelCompatOverrides` for hidden models:

```python
import sqlite3
import json

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cur = conn.cursor()
cur.execute("SELECT value FROM key_value WHERE namespace = 'modelCompatOverrides' AND key = 'antigravity'")
row = cur.fetchone()
if row:
    models = json.loads(row[0])
    hidden = [m.get('id') for m in models if isinstance(m, dict) and m.get('isHidden')]
    print("Hidden models:", hidden)
```

If `gemini-3.7-flash-tiered`, `gemini-pro-agent`, or `gemini-3.1-flash-lite` appear in `hidden`, Layer 1 filtering is the exact cause of missing quota bars.

---

## 4. Remediation Steps

### Option A: Web UI (Safe & Standard)
1. Open OmniRoute Dashboard → **Models** (`/dashboard/models`) or **Providers** → select **Antigravity**.
2. Locate the hidden Gemini models (look for the slashed-eye `visibility_off` icon).
3. Click to toggle them back to **Visible** (`visibility`).
4. Reload the Provider Limits / Usage page (`F5`).

### Option B: Direct SQLite Unhide
Update the JSON array in `key_value` where `namespace = 'modelCompatOverrides' AND key = 'antigravity'`, setting `"isHidden": false` for the desired model IDs.

---

## 5. Disambiguating "Token expired" vs Account Death

| UI Indicator | Meaning | Severity | Action Required |
| :--- | :--- | :--- | :--- |
| **Green dot + Red `Token expired`** | OAuth access token (1h TTL) has elapsed, but account is **HEALTHY & ACTIVE**. | **None (Informative)** | Tokens are rotated automatically on-demand via `refresh_token` when inference requests arrive. Do NOT re-authorize or disable accounts. |
| **Gray dot + Red banner `Failed to refresh credentials...`** | Upstream returned `401 Unauthorized` / `token_revoked`. | **Action Required** | Refresh token is genuinely invalid (password changed, session revoked by Google/OpenAI). Requires OAuth re-authentication. |

---

## 6. Root Cause Incident: Agent UI Cleanup Trap
- **Historical Context**: Một lỗi phổ biến từng xảy ra khi người dùng yêu cầu "lọc sạch model rác / dọn menu /model Telegram". AI Agent dùng browser tự động mở OmniRoute UI vào trang Provider Antigravity và bấm nút **"Ẩn tất cả" (`visibility_off`)**, sau đó chỉ unhide các alias cụ thể (như `gemini-3.7-flash-high`).
- **Hệ quả ngầm**: Nút "Ẩn tất cả" đặt `isHidden: true` lên toàn bộ upstream bucket keys (`gemini-3.7-flash-tiered`, `gemini-pro-agent`, `gemini-3.1-flash-lite`), khiến UI Usage dashboard giấu sạch toàn bộ hạn ngạch Gemini.
- **Kỷ luật Coordinator / Worker**: TUYỆT ĐỐI CẤM dùng browser bấm "Ẩn tất cả" trên OmniRoute để dọn dẹp menu client. Việc lọc model cho Hermes/Telegram phải thực hiện ở tầng cấu hình client (`config.yaml` / `FARM_MODELS` / `custom_providers`), không được can thiệp vào danh mục model gốc của Provider trên OmniRoute.
