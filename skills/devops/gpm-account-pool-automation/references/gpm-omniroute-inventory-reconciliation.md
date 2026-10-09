# GPM Profile & OmniRoute Antigravity Pool Inventory Reconciliation

## 1. Mục đích
Quy trình đối soát tự động nhằm phát hiện các profile GPM đã đăng nhập Google/Gmail thành công, session còn sống, đã dọn Google Prompt và bật 2FA TOTP nhưng **chưa từng được kết nối vào OmniRoute (Antigravity OAuth pool)**. Dùng để mở rộng pool an toàn hoặc audit trạng thái tài nguyên định kỳ.

---

## 2. 3-Tier Verification Gate cho Profile GPM
Để đảm bảo tài khoản đưa vào OmniRoute không bị lỗi auth hoặc văng checkpoint giữa chừng, profile bắt buộc phải vượt qua 3 tầng xác minh:

1. **Tier 1: DOM Live Verification (Bằng chứng DOM thực tế):**
   - Đọc kết quả từ file log / audit gần nhất:
     - `C:\Users\Kibe\gpm_group1_verification_results.json` (`has_valid_session: true` và `match: "YES"`).
     - `D:\Taadaa\GPM auto\logs\prompt_removal_results.json` (`status: "SUCCESS"` hoặc `"PARTIAL_SUCCESS"`, `twosv_verified: true`).
   - Nếu chưa có hoặc cũ, chạy script kiểm tra DOM `myaccount.google.com` (theo Section 9 trong SKILL.md).

2. **Tier 2: Cookie Jar & Expiration Check (Bảo vệ tính toàn vẹn session):**
   - Đọc file SQLite cookie tại `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\{ProfilePath}\Default\Network\Cookies`.
   - Bắt buộc copy ra temp file trước khi mở để tránh lock DB.
   - Query 5 session cookies cốt lõi của Google:
     ```sql
     SELECT name, expires_utc FROM cookies 
     WHERE host_key LIKE '%.google.com' 
       AND name IN ('SID', 'SAPISID', 'SSID', 'HSID', '__Secure-1PSID')
     ```
   - Điều kiện: Số lượng `>= 3` cookies và `expires_utc` còn hạn sử dụng:
     ```python
     def chrome_time_to_unix(c_time):
         return (c_time - 11644473600000000) / 1000000
     is_valid = any(chrome_time_to_unix(exp) > time.time() for exp in exp_times)
     ```

3. **Tier 3: Excel Metadata & 2FA Decoupling:**
   - Đối chiếu trong `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Master_All` hoặc `Kibe_Farm_S7`):
     - `2FA_Secret`: Khác rỗng (Base32 32 ký tự).
     - `Trạng Thái`: `LIVE`.
     - `Ghi Chú`: Ghi nhận `Đã tắt Google Prompt` (chỉ dùng 2FA TOTP, không rung chuông S7).

---

## 3. Trích xuất Tài khoản OmniRoute

### A. Qua API (Port 20129)
- Endpoint: `GET http://localhost:20129/api/providers`
- **Lưu ý định dạng dữ liệu trả về**: API trả về một dictionary `{"connections": [...], "total": N}`, **không phải list**.
  ```python
  resp = requests.get("http://localhost:20129/api/providers", timeout=5).json()
  connections = resp.get("connections", [])
  omni_emails = {
      (c.get("email") or c.get("name") or "").strip().lower()
      for c in connections
      if c.get("provider") == "antigravity" or "antigravity" in c.get("id", "")
  }
  ```

### B. Qua SQLite Database (`storage.sqlite`)
- Đường dẫn: `C:\Users\Kibe\.omniroute\storage.sqlite`
- Query danh sách hiện tại:
  ```sql
  SELECT DISTINCT lower(trim(email)), lower(trim(name)) 
  FROM provider_connections 
  WHERE provider = 'antigravity';
  ```
- Query lịch sử từng gọi request thành công:
  ```sql
  SELECT DISTINCT lower(trim(account)) 
  FROM call_logs 
  WHERE provider = 'antigravity' AND account IS NOT NULL;
  ```

---

## 4. Script Mẫu Đối Soát Nhanh (Reconciliation Runner)

```python
import os, json, sqlite3, re, tempfile, shutil, time

GPM_PROFILE_BASE = r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile"
GPM_DB = os.path.join(GPM_PROFILE_BASE, "profile_data.db")
OMNI_DB = r"C:\Users\Kibe\.omniroute\storage.sqlite"
PROMPT_RESULTS = r"D:\Taadaa\GPM auto\logs\prompt_removal_results.json"

# 1. OmniRoute existing set
conn_omni = sqlite3.connect(OMNI_DB)
c_omni = conn_omni.cursor()
c_omni.execute("SELECT email, name FROM provider_connections WHERE provider='antigravity'")
omni_accounts = set()
for em, name in c_omni.fetchall():
    if em: omni_accounts.add(em.strip().lower())
    if name and "@gmail.com" in name: omni_accounts.add(name.strip().lower())
conn_omni.close()

# 2. Verified GPM from prompt_removal_results
verified_gpm = {}
if os.path.exists(PROMPT_RESULTS):
    with open(PROMPT_RESULTS, "r", encoding="utf-8") as f:
        for it in json.load(f):
            if it.get("status") in ("SUCCESS", "PARTIAL_SUCCESS"):
                em = (it.get("email") or "").strip().lower()
                if em: verified_gpm[em] = it

# 3. Reconcile
candidates = []
for email, item in verified_gpm.items():
    if email not in omni_accounts:
        candidates.append(item)

print(f"Found {len(candidates)} verified GPM profiles ready for OmniRoute:")
for c in candidates:
    print(f"- {c.get('name')} | ID: {c.get('id')} | Email: {c.get('email')}")
```
