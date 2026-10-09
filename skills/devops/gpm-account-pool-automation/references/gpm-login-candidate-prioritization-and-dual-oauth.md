# GPM Login Candidate Prioritization & Dual OAuth Protocol

## 1. Single Source of Truth cho Pool Status
- **KHÔNG** chỉ đọc file tĩnh `oauth_pipeline_status.json` vì file có thể stale (không chứa các connection được nạp từ script khác).
- **BẮT BUỘC** query trực tiếp endpoint live của OmniRoute:
  ```python
  import urllib.request, json
  req = urllib.request.Request("http://127.0.0.1:20129/api/providers")
  with urllib.request.urlopen(req, timeout=5) as resp:
      data = json.loads(resp.read().decode())
      conns = data.get("connections", [])
      live_anti_emails = set(
          (c.get("email") or c.get("name") or "").strip().lower()
          for c in conns if c.get("provider") == "antigravity"
      )
      live_chatgpt_web_emails = set(
          (c.get("email") or c.get("name") or "").strip().lower()
          for c in conns if c.get("provider") == "chatgpt-web" and c.get("testStatus") == "active"
      )
  ```

## 2. Phân tách nhiệm vụ tuyệt đối (Separation of Concerns)
- **Tạo / Xóa Profile GPM:** Đã có cronjob chuyên trách `sync_gpm_lifecycle.py` (chạy 07:15 - 08:45 hàng ngày) đảm nhiệm. Watchdog ca tối login (`post_evening_gpm_login_watchdog.py`) **TUYỆT ĐỐI KHÔNG** tự ý gọi `sync_gpm_profiles_lifecycle()` hoặc create/delete profile.
- **Watchdog ca tối login:** CHỈ tập trung vào: **Login Google và OAuth**.

## 3. Quy tắc 3 nhóm ưu tiên Candidates (GPM Login)
1. **Ưu tiên 1 (`has_google_session_ready_oauth`):**
   - Quét cookie profile GPM (`Default/Network/Cookies` hoặc `Default/Cookies`).
   - Nếu đã có `SID, SSID, HSID, SAPISID` từ google.com (đã login thành công trước đó) nhưng chưa có trong OmniRoute `live_anti_emails` -> Đưa lên đầu batch.
   - Luồng này chỉ mở browser -> Account Chooser -> click chọn là có mã OAuth trong 10 giây, **100% không dính checkpoint**.
2. **Ưu tiên 2 (`chatgpt_ready_priority`):**
   - Các acc chưa có session nhưng đã được bồi trust ban ngày (cờ `CHATGPT_READY` trên Excel hoặc state).
   - Acc đã có tương tác email thật trên điện thoại S7 -> Google trust cao hơn khi login PC.
3. **Ưu tiên 3 (`ready_gpm_oauth`):**
   - Các acc Gmail LIVE có profile GPM, tuổi ngâm >= 7 ngày, chưa nạp OmniRoute.
   - Nếu từng fail hôm nay: Chỉ retry khi đã qua ngày mới hoặc cooldown >= 24h.

## 4. Trần an toàn Concurrency
- `MAX_WORKERS = 2`: Cấm chạy 5 workers song song vì gây nghẽn proxy nội bộ, lag vòng lặp Playwright dẫn đến timeout 180s ở bước cuối (OAuth consent) và kích hoạt fraud score của Google.
- Giới hạn proxy: Tối đa 2 acc / 1 port proxy / 1 ngày.

## 5. Dual OAuth & Healer Ecosystem
- **Dual OAuth:** Sau khi login GPM và OAuth Antigravity thành công, pipeline gọi tiếp `batch_dual_oauth_5workers.py --email <email>` để trích xuất cookie session cho provider `chatgpt-web` và thêm model vào combo `chatgpt-web-pool`.
- **Healer Watchdog:** Cronjob `cron_chatgpt_web_pool_watchdog.py` (05:00 AM) tự động kiểm tra sức khỏe của cả 2 pool `antigravity` và `chatgpt-web`. Nếu session hết hạn, nó tự bật Profile GPM qua CDP để làm mới session.
