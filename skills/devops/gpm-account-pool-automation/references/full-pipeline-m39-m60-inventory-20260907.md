# Full Pipeline 2FA → OAuth → Combo — Inventory & Recipe (2026-09-07)

## Mục đích
Thiết lập và chạy full pipeline (Bật 2FA Authenticator → Lưu Excel → Hot-session OAuth OmniRoute → Append Combo ag-gemini-pool-3) cho M39 và M60.

---

## Machine Inventory (verified 07/09/2026)

| Field | M39 | M60 |
|---|---|---|
| Email (target) | tachau17042004@gmail.com | crystalwwilsonlypp1@gmail.com |
| Password | Tachau17042004@Ks | Hnpixpbvnfun |
| Recovery | thanhdatbui1995@gmail.com | thanhdatbui1995@gmail.com |
| Serial S7 | ce0117113818c4d30c | ce09160963abd20e02 |
| ADB Status | ✅ online | ✅ online |
| Proxy Port | 5101 | 5126 |
| Proxy String | test.taadaa.click:5101:mobi1:TaadaaMobi#2026! | test.taadaa.click:5126:mobi26:TaadaaMobi#2026! |
| 2FA Secret (gmail_clean_v2) | BAJUVPFZ6QLNDTXH2VHRDWSCWDQG7HDK ✅ | None ❌ |
| OAuth OmniRoute | NOT YET | NOT YET |
| profiles_worker | (none for tachau — create new) | p_m60_crystalwwilsonlypp1_gmail_com ✅ |

### M39 — Pipeline Classification: SKIP_2FA
- 2FA ĐÃ CÓ SẴN trong cả gmail_clean_v2 và master_gmail_manager (sheet Kibe_Farm_S7 row 122, Master_All row 161).
- TOTP secret: `BAJUVPFZ6QLNDTXH2VHRDWSCWDQG7HDK`
- Bỏ qua bước bật 2FA, chạy thẳng: Hot-Session OAuth → Append Combo.
- Profile cần tạo mới: `D:\Taadaa\GPM auto\profiles_worker\p_m39_tachau17042004_gmail_com\`

### M60 — Pipeline Classification: FULL_PIPELINE
- crystalwwilsonlypp1@gmail.com: 2fa = None → cần bật 2FA trước.
- jessicaobakervi8yx@gmail.com: backup account nếu crystal fail (pass: Gygsymxscxc, recovery: Gygsymxscxc@gmail.com ← lưu ý recovery này trùng email chính, cần test IMAP trước)
- Profile đã tồn tại: `p_m60_crystalwwilsonlypp1_gmail_com`

---

## Pre-flight Excel Check Pattern

```python
import openpyxl, json, os

CLEAN_V2 = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
STATUS_JSON = r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json"

def preflight_classify(machine_id: int, email: str) -> str:
    """Returns: 'SKIP_ALL' | 'SKIP_2FA' | 'FULL_PIPELINE'"""
    # 1. OmniRoute already done?
    if os.path.exists(STATUS_JSON):
        with open(STATUS_JSON) as f:
            data = json.load(f)
        if email in data.get("omniroute_success", {}):
            return "SKIP_ALL"
    # 2. 2FA already in Excel?
    wb = openpyxl.load_workbook(CLEAN_V2, data_only=True)
    ws = wb.active
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        try:
            m = int(float(str(row[0])))
        except Exception:
            continue
        if m == machine_id and str(row[1] or "").strip().lower() == email.lower():
            fa2 = row[3]
            if fa2 and len(str(fa2).strip()) >= 16:
                return "SKIP_2FA"
            break
    return "FULL_PIPELINE"

# Usage:
# for email in targets:
#     mode = preflight_classify(machine_id, email)
#     if mode == "SKIP_ALL": continue
#     if mode == "SKIP_2FA": run_oauth_and_append(email, ...)
#     else: run_full_pipeline(email, ...)
```

---

## Full Pipeline Integration Recipe

### Script paths
```
D:\Taadaa\GPM auto\scripts\run_batch_2fa_kibe_pool.py   → process_single_account(item), save_secret_key_to_excels()
D:\Taadaa\GPM auto\scripts\hot_session_oauth.py          → trigger_hot_session_oauth(page, email, machine_id, port, profile_name)
D:\Taadaa\GPM auto\scripts\append_to_combo_pool3.py      → append_connections([{"cid": conn_id, "email": email, "port": port}])
D:\Taadaa\GPM auto\scripts\run_oauth_s7_pipeline.py      → approve_s7_google_prompt(), get_s7_security_code()
```

### Constants
```python
ADB_EXE    = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
CHROME_EXE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe"
OMNI_BASE  = "http://127.0.0.1:20129"
COMBO_ID   = "22975610-b162-41b9-b6b3-30be076265bd"  # ag-gemini-pool-3
MASTER_EXCEL = r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx"
CLEAN_V2_EXCEL = r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx"
PROXY_EXCEL = r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"
PROFILES_WORKER = r"D:\Taadaa\GPM auto\profiles_worker"
STATUS_JSON = r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json"
```

### Step sequence (per account)
```
1. preflight_classify() → determines mode
2. [FULL_PIPELINE only] process_single_account(item) → enables 2FA + saves Excel
3. Open Playwright persistent context (profiles_worker dir, proxy server)
4. Login Google (email + password + S7 security code if challenge)
5. trigger_hot_session_oauth(page, email, machine_id, port, profile_name)
   → returns {"status": "SUCCESS", "cid": conn_id, "port": port}
6. append_connections([{"cid": conn_id, "email": email, "port": port}])
   → appends to ag-gemini-pool-3 (COMBO_ID) via PUT /api/combos/{COMBO_ID}
7. Verify: GET /api/combos → count models in pool-3 incremented
```

### Proxy URL format
```python
proxy_url = f"http://192.168.110.2:{20000 + machine_id}"
# M39 → http://192.168.110.2:20039
# M60 → http://192.168.110.2:20060
```

### Proxy Port (for OmniRoute proxy assignment)
Read from `PROXYgandienthoai.xlsx` col `proXy`: parse port from string `test.taadaa.click:<PORT>:mobi<N>:...`
- M39 → port 5101
- M60 → port 5126

---

## OmniRoute State (verified 07/09/2026)
- `ag-gemini-pool-3` had **38 targets** before this session.
- M39 + M60 accounts were NOT in `oauth_pipeline_status.json["omniroute_success"]`.

---

## Pitfalls found this session

1. **M39 already had 2FA but no profile_worker dir for tachau**: The 3 existing m39 profiles (doanxuan/tonghong/vuthithanhhuyen) are different accounts. Must create `p_m39_tachau17042004_gmail_com` fresh.

2. **Don't use `python3` (3.12) for scripts requiring pandas/numpy**: The Hermes venv has numpy built for cp311, crashes on python3 (cp312). Use `python` (→ Python 3.11.15) for any script importing pandas/openpyxl/numpy.

3. **M60 has 5 rows in gmail_clean_v2** — 2 Hotmail (JaymeTolhurst78815, RondalGranston921724), 1 gmail (crystalwwilsonlypp1), 1 Hotmail (iyoqysdvmyznajyk), 1 gmail (jessicaobakervi8yx). Only use Gmail accounts for Google OAuth. Filter `email.endswith("@gmail.com")`.

4. **`khoalemagic` recovery gate**: `vuthithanhhuyen040420010404@gmail.com` on M39 has `khoalemagic@gmail.com` as recovery → EXCLUDE 100%. Always check recovery column before queuing.
