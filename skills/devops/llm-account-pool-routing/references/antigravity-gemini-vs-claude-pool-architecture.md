# Antigravity Pool Architecture: Gemini vs Claude — Tách Biệt Hoàn Toàn

Dữ liệu từ code + SQLite `storage.sqlite` + 490 quota_snapshot rows (07-08/09/2026).

---

## 1. Hai Pool Hoàn Toàn Độc Lập

Google Antigravity / Cloud Code chia quota thành **2 family pools riêng biệt, không chia sẻ**:

| Pool | Model IDs (live catalog) | API RPC nguồn | Reset window |
|------|--------------------------|---------------|--------------|
| **GEMINI** | `gemini-3.7-flash-tiered`, `gemini-3.8-flash-tiered`, `gemini-pro-agent`, `gemini-3.1-pro-low/high`, `gemini-3.1-flash-lite`, `gemini-3.x-flash-*` | `retrieveUserQuota` (per-model buckets, nhóm theo `family:gemini`) | Rolling ~5h + weekly |
| **CLAUDE** | `claude-opus-4-6-thinking`, `claude-sonnet-4-6` (+ `gpt-oss-120b-medium`) | `retrieveUserQuota` (nhóm `family:claude`) | Rolling ~5h riêng biệt |
| **WEEKLY** | `gemini_weekly`, `claude_gpt_weekly` | `retrieveUserQuotaSummary` (RPC thứ 3, #4017) | 7 ngày |

**Key rule từ `getAntigravityQuotaFamily()` trong `antigravityQuotaFamily.ts`:**
- `gemini-*` → `family:gemini`
- `claude-*`, `cloud-*`, `anthropic/` → `family:claude`
- Quota tiêu theo **family scope**, không phải per-model → toàn bộ Gemini models dùng chung 1 gemini bucket; toàn bộ Claude models dùng chung 1 claude bucket.

---

## 2. API RPCs — 3 Nguồn Quota Data

```
POST v1internal:fetchAvailableModels     → catalog + remainingFraction per model
POST v1internal:retrieveUserQuota        → live consumption per model (5h window) ← source of truth
POST v1internal:retrieveUserQuotaSummary → weekly family-level buckets (undocumented RPC)
```

`retrieveUserQuotaSummary` trả về `groups[]`, mỗi group = 1 model family:
- `displayName: "Gemini Models"` → key `gemini_weekly`
- `displayName: "Claude and GPT models"` → key `claude_gpt_weekly`

**OmniRoute priority:** `retrieveUserQuota` win over `fetchAvailableModels` khi có data. `fetchAvailableModels` là static catalog dễ stale (có thể báo đầy khi thực ra đã dùng).

---

## 3. Starter vs Pro: Cả Hai Đều Có Claude

**Lầm tưởng phổ biến:** Starter không có Claude.

**Thực tế từ DB (490 snapshot rows, 15 Starter + 14 Pro account):**

| Tài khoản Plan | Số model Claude | Remaining Claude (avg) | Exhausted? |
|----------------|-----------------|------------------------|------------|
| **Starter** | 3 (sonnet, opus, claude_gpt_weekly) | ~66% | 0/15 exhausted |
| **Pro** | 3 (sonnet, opus, claude_gpt_weekly) | ~58% | 4/14 exhausted |

Starter **CÓ** `claude-opus-4-6-thinking` + `claude-sonnet-4-6` — giống Pro về danh sách model, khác nhau về quota volume.

---

## 4. Empirical: Gemini vs Claude per Plan (call_logs)

### 4a. Aggregate Request Counts

| Plan | Accts | Gemini requests | Claude requests | G:C ratio |
|------|-------|-----------------|-----------------|-----------|
| **Pro** | 14 | 85,424 | 389 | **219.6:1** |
| **Starter** | 15 | 466 | 218 | **2.1:1** |
| Business | 10 | 0 | 0 | — (unused) |

### 4b. Tại sao G:C khác nhau lớn giữa Pro và Starter?

- **Pro** là worker chính trong `ag-gemini-pool-3`: gần như toàn bộ tải là Gemini; Claude chỉ được gọi trực tiếp.
- **Starter** thường nằm ở đuôi combo, được routing Claude nhiều hơn tương đối (natural spillover thường trên Claude combo khi Pro Gemini bận).

---

## 5. Pool Independence — Chứng Minh Từ Thực Tế

Gemini exhausted KHÔNG ảnh hưởng Claude và ngược lại:

| Tài khoản | Plan | Gemini rem% | Claude rem% | Ghi chú |
|-----------|------|-------------|-------------|---------|
| brittanysbarneskn2xa | Starter | **0.0% exhausted** | 100.0% | Gemini cạn, Claude còn nguyên |
| thanhdatbui1995 | Starter | **0.0% exhausted** | 36.3% | Gemini cạn, Claude còn 36% |
| longtuong201058 | Starter | 99.4% | 34.7% | Gemini nguyên, Claude tiêu 65% |
| namdung150755 | Starter | 100.0% | **9.7%** | Gemini nguyên, Claude gần hết |
| dangmy30011996 | Pro | **0.1%** | 97.9% | Gemini sắp cạn, Claude gần nguyên |
| jinrakal | Pro | 1.0% | **0.0% exhausted** | Gemini gần cạn, Claude đã hết |
| marcusephillips | Pro | 0.8% | **0.0% exhausted** | Gemini gần cạn, Claude đã hết |
| dokieu04092004 | Pro | **0.0% exhausted** | **0.0% exhausted** | Cả 2 pool cạn cùng lúc (heavy user) |

---

## 6. Tốc Độ Tiêu Hao

### GEMINI pool
- **Pro:** Hầu hết <10% remaining (nhiều tài khoản 0–1%), reset mỗi ~5h.
- **Starter:** Chậm hơn — chỉ 2/15 exhausted, 10/15 còn 100% (ít tải).

### CLAUDE pool
- **Pro:** Tiêu ít hơn nhiều so với Gemini (~58% còn lại avg), nhưng 4/14 Pro exhausted Claude hoàn toàn.
- **Starter:** ~66% còn lại avg, không ai exhausted — dùng Claude ít.

---

## 7. Model Catalog Sự Khác Biệt Starter vs Pro

Qua `isDiscoverableAntigravityModelId()` và `retrieveUserQuota` data:
- **Starter:** 10 Gemini slots + 3 Claude slots (incl. gemini_weekly và claude_gpt_weekly weekly buckets)
- **Pro:** Tương tự 10 Gemini + 3 Claude slots
- Không có sự khác biệt về **danh sách model** — chỉ khác về **quota volume** (xem `references/antigravity-quota-benchmarks-and-capacity-limits.md`)

---

## 8. SQL Chẩn Đoán Pool Separation

```python
# Gemini vs Claude remaining per account (Python — sqlite3 CLI unavailable trên Windows)
import sqlite3, json
db = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
db.row_factory = sqlite3.Row
cur = db.cursor()

cur.execute('''
  SELECT qs.connection_id, qs.window_key,
         qs.remaining_percentage, qs.is_exhausted, qs.next_reset_at,
         MAX(qs.created_at) as latest_at,
         pc.name,
         json_extract(pc.provider_specific_data, "$.plan") as plan
  FROM quota_snapshots qs
  JOIN provider_connections pc ON pc.id = qs.connection_id
  WHERE qs.provider = "antigravity"
  AND pc.is_active = 1
  GROUP BY qs.connection_id, qs.window_key
  ORDER BY plan, pc.name, qs.window_key
''')
```

```python
# Call logs Gemini vs Claude per account
cur.execute('''
  SELECT cl.account, cl.model,
         json_extract(pc.provider_specific_data, "$.plan") as plan,
         COUNT(*) as req_count
  FROM call_logs cl
  LEFT JOIN provider_connections pc ON pc.id = cl.connection_id
  WHERE cl.provider = "antigravity"
  AND cl.status = 200
  GROUP BY cl.account, cl.model
''')
```

**Pitfall:** `sqlite3` CLI không có sẵn trên Windows (`command not found`). Dùng `python3 -c "import sqlite3..."` hoặc script Python thay thế.

---

## 9. Routing Implications

1. **Pool Gemini cạn ≠ Pool Claude cạn** — có thể route Claude khi Gemini exhausted.
2. **Starter không thiếu Claude** — có thể dùng Starter cho Claude workloads với điều kiện không dồn tải nặng (quota Starter mỏng ~190-250 req/tuần tổng cộng cả Gemini lẫn Claude).
3. **Claude Pro pool exhausted** (4/14 Pro) thường xảy ra RIÊNG với Gemini Pro pool (hầu hết <10%) — 2 pool tiêu độc lập.
4. **Combo `ag-claude`/`ag-opus` nên dùng Pro** vì bucket tuần Claude Pro lớn hơn nhiều Starter.
5. **weekly buckets (`gemini_weekly`, `claude_gpt_weekly`)** là tầng thứ 3 — reset theo tuần, không theo 5h. Dùng để theo dõi tổng tải tuần, bổ sung cho 5h bucket.
