# ChatGPT-Web Sentinel Recovery & Codex Pool Consolidation Runbook

## 1. Bản Chất Kỹ Thuật: Cùng 1 Acc Nhưng "Cửa Trước (Web)" vs "Cửa Sau (Codex)"

### A. Sự Khác Biệt Giữa 2 Giao Thức
| Đặc tính | ChatGPT-Web (`chatgpt-web`) | Codex CLI (`codex`) |
| :--- | :--- | :--- |
| **Giao thức** | Cookie session giả lập trình duyệt (`/backend-api/conversation`) | OAuth PKCE Developer API (`/v1/responses`) |
| **Tường lửa** | **Cloudflare Turnstile & Sentinel** (Chặn bot, kiểm tra chuột/DOM) | **KHÔNG có Cloudflare Sentinel** (Thiết kế cho terminal/IDE) |
| **Chi phí / Quota** | **0 quota Codex** (Không tính vào chu kỳ tháng của Codex) | Có hạn ngạch chu kỳ riêng (Codex Scope Allowance) |
| **Vai trò tối ưu** | **Code Review / Plan Audit** (Tác vụ đọc/thẩm định text dài) | **Worker Code-Surgery** (Thực thi tool call, patch code) |

### B. Tử Huyệt Nhãn "Banned" Trên OmniRoute
- Khi OmniRoute gửi request HTTP giả lập trình duyệt, nếu Cloudflare nghi ngờ bot $\rightarrow$ Trả về **HTTP 403**:
  > `[403]: ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.`
- **Lỗi hiển thị**: Backend OmniRoute tự động gán nhãn `test_status = 'banned'`, gây hiểu nhầm nghiêm trọng là tài khoản đã bị OpenAI khóa vĩnh viễn.
- **Thực tế**: Tài khoản hoàn toàn sống bình thường 100%! Cùng tài khoản đó gọi qua cổng Codex vẫn trả về `200 OK` trong 2–3 giây.
- **Phân biệt Ban Thật vs Sentinel Challenge**:
  * *Ban thật*: Trình duyệt báo đỏ: *"Your account has been deactivated / disabled"*. Cả Web lẫn Codex đều chết.
  * *Sentinel Challenge*: Trình duyệt thật mở lên vẫn vào bình thường, chỉ có script HTTP cào thiếu telemetry mới bị 403.

---

## 2. Quy Trình Hồi Sinh Tài Khoản ChatGPT-Web Tự Động (GPM + Playwright CDP)

Khi tài khoản Web bị 403/banned hoặc cookie hết hạn (HTTP 401), thực hiện hồi sinh tự động trong <= 30 giây:

```python
import requests, time, sqlite3
from playwright.sync_api import sync_playwright

GPM_API = "http://127.0.0.1:19995/api/v3"
OMNI_DB = "C:/Users/Kibe/.omniroute/storage.sqlite"

def rescue_chatgpt_web_account(profile_id, connection_id):
    # 1. Khởi động profile GPM qua proxy 4G sạch
    res = requests.get(f"{GPM_API}/profiles/start/{profile_id}?win_scale=0.8", timeout=30).json()
    addr = res.get("data", {}).get("remote_debugging_address")
    
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://{addr}")
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else context.new_page()
        
        # 2. Điều hướng vào chatgpt.com (Trình duyệt thật tự giải Cloudflare Sentinel)
        page.goto("https://chatgpt.com/", timeout=35000, wait_until="domcontentloaded")
        time.sleep(3)
        
        # 3. Trích xuất cookie __Secure-next-auth.session-token (ghép chunk .0, .1 nếu có)
        cookies = context.cookies()
        session_token = None
        chunks = {}
        for c in cookies:
            name, val = c.get("name", ""), c.get("value", "")
            if name == "__Secure-next-auth.session-token":
                session_token = val
                break
            elif name.startswith("__Secure-next-auth.session-token."):
                chunks[name.split(".")[-1]] = val
        if not session_token and chunks:
            session_token = "".join(chunks[k] for k in sorted(chunks.keys(), key=lambda x: int(x) if x.isdigit() else x))
            
        browser.close()
    
    requests.get(f"{GPM_API}/profiles/stop/{profile_id}", timeout=10)
    
    # 4. Nạp đè token mới vào SQLite OmniRoute
    if session_token:
        with sqlite3.connect(OMNI_DB) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE provider_connections 
                SET api_key=?, is_active=1, test_status='active', last_error=NULL, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id=?
            """, (session_token, connection_id))
            conn.commit()
        return True
    return False
```

---

## 3. Quy Chuẩn Đồng Bộ & Gom Cụm Pool OmniRoute (Anti-Fragmentation)

### A. Tử Huyệt Timeout 45s (Lỗi HTTP 499 trên Luna High)
- Nếu combo pool đặt `targetTimeoutMs: 45000` (45 giây): Khi model suy luận sâu (`gpt-5.6-luna-high`) sinh thinking tokens ngầm vượt quá 45 giây $\rightarrow$ OmniRoute tự ngắt kết nối và trả về **HTTP 499** (đo thật ở các mốc 45.02s – 47.02s).
- **Quy tắc cứng**: Mọi pool chạy model thinking/reasoning (Codex Luna, Codex Terra) bắt buộc đặt:
  ```json
  "config": {
    "targetTimeoutMs": 90000,
    "maxRetries": 1,
    "retryDelayMs": 200,
    "stickyRoundRobinLimit": 8
  }
  ```

### B. Gom Cụm 1 Pool Duy Nhất (Tránh Đẻ Pool Song Song)
- **Cấm tạo 2 pool song song** (như `codex-luna` vs `codex-luna-pool`, `codex-terra` vs `codex-terra-pool`). Sự phân mảnh này dẫn đến:
  1. Combo cha (`omni-worker`) trỏ nhầm vào pool cũ có timeout 45s.
  2. Bỏ sót tài khoản: Pool mới nạp tài khoản nhưng combo cha vẫn ăn theo pool cũ thiếu acc.
- **Tiêu chuẩn cấu trúc Combo**:
  - `codex-luna`: Gom trọn vẹn 100% tài khoản Codex LIVE (`active=1`, `test_status='active'`), model `codex/gpt-5.6-luna-high`, timeout 90s, strategy `cache-optimized`.
  - `codex-terra`: Gom trọn vẹn tài khoản Codex LIVE, model `codex/gpt-5.6-terra`, timeout 90s, strategy `cache-optimized`.
  - Tier 3 trong `omni-worker`: Trỏ duy nhất vào `codex-luna`.
