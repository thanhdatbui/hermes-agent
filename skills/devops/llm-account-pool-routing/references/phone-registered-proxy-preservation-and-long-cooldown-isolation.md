# Phone-Registered Proxy Preservation & Long Cooldown Isolation Runbook

## 1. Phone-Registered Account Proxy Preservation Invariant

### Ngữ cảnh & Triệu chứng sai lầm:
Khi kiểm tra bảng `proxy_assignments` trong `storage.sqlite` của OmniRoute (`:20129`), agent thấy một cổng proxy 4G MobiProxy (ví dụ `test.taadaa.click:5113`) đang được gán cho nhiều tài khoản (cả Gmail Google OAuth, Hotmail Codex, và GPM Web).
- **Sai lầm thường gặp (False Diagnosis):** Agent kết luận đây là "map proxy bừa bãi / dồn cục vô lý" và tự ý re-balance, chuyển các tài khoản Hotmail sang dải MikroTik rảnh rỗi (`10008..10035`).

### Quy tắc bất biến (Farm Hardware Invariant):
- Các tài khoản Hotmail hoặc Google được dùng để đăng ký tài khoản TikTok trên điện thoại thật (Samsung S7 farm) **BẮT BUỘC PHẢI GIỮ NGUYÊN CỔNG PROXY GÁN CỨNG THEO MÁY ĐÓ**.
- **SoT đối soát:**
  1. `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`: Cột Máy và Mail đăng ký (ví dụ: Nick `yenngo9591` ở Máy 49 dùng mail `vanharlingenmach959@hotmail.com`).
  2. `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`: Cột Proxy của Máy tương ứng (Máy 49 được gán cổng `5113:mobi13`).
- **Lý do kỹ thuật:** Khi tài khoản được nạp vào Codex / OpenAI / Google, việc giữ nguyên IP/cổng proxy đồng nhất với thiết bị đã reg giúp duy trì fingerprint mạng (ASN, Subnet, Location), chống bị Microsoft / OpenAI / Google kích hoạt Security Challenge hoặc checkpoint ban do đổi IP đột ngột (IP jump).
- **CẤM:** Tuyệt đối không tự ý tách hay đổi proxy của các tài khoản Hotmail đã gắn với máy farm sang proxy khác nếu không có lệnh rõ ràng từ User.

---

## 2. Long-Term Cooldown Isolation (Cách ly tài khoản hết Quota 400+ tiếng)

### Hiện tượng:
- Các tài khoản OpenAI Free / Codex có thể bị rate-limit dài hạn lên tới hàng trăm giờ (`415h`, `400h`).
- Trong bảng `provider_connections`, trường `provider_specific_data` lưu JSON chứa `codexScopeRateLimitedUntil: {"codex": "<ISO_TIMESTAMP>"}` (ví dụ: `2026-10-26T07:40:00.000Z`).
- Nếu tài khoản này vẫn nằm trong danh sách `models` của combo `codex-terra`, `codex-luna`, hoặc `review`:
  1. Mỗi khi combo fallback qua Codex, OmniRoute sẽ thử tài khoản đó và ghi log:
     `codex | all 1 active accounts cooling down for model gpt-5.6-terra (reset after 415h 21m 28s)`
  2. Request bị ngâm hoặc trả về 429/503/504, làm cạn kiệt ngân sách retry của caller (Hermes Gateway).

### Cơ chế Cách ly & Phục hồi chuẩn (Quarantine Workflow):
1. **Kiểm tra trạng thái Cooldown:**
   ```python
   import sqlite3, json
   from datetime import datetime, timezone
   
   conn = sqlite3.connect(r'C:/Users/Kibe/.omniroute/storage.sqlite')
   cur = conn.cursor()
   now_iso = datetime.now(timezone.utc).isoformat()
   
   cur.execute("SELECT id, email, provider_specific_data FROM provider_connections WHERE provider='codex'")
   for cid, email, data in cur.fetchall():
       rl = None
       if data:
           try:
               d = json.loads(data)
               rl = (d.get('codexScopeRateLimitedUntil') or {}).get('codex')
           except: pass
       if rl and rl > now_iso:
           print(f"[COOLDOWN - QUARANTINE] {email} until {rl}")
       else:
           print(f"[AVAILABLE] {email}")
   ```

2. **Cách ly khỏi Combo Models (`combos` table):**
   - Lọc bỏ các `connectionId` có `codexScopeRateLimitedUntil > now` khỏi mảng `models` trong combo `codex-terra` và `codex-luna`.
   - Lưu lại `data` mới vào DB để OmniRoute chỉ gọi các tài khoản thực sự khả dụng (`AVAILABLE`).

3. **Tự động phục hồi (De-quarantine):**
   - Khi thời gian UTC vượt qua `codexScopeRateLimitedUntil` (`now_iso >= rl`), tài khoản tự động được coi là hết hạn phạt và có thể được thêm lại vào combo candidate pool.
