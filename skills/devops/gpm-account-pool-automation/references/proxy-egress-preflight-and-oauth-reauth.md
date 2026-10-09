# Preflight Proxy Verification & Troubleshooting (Singbox & Upstream PPPoE)

## 1. Bản Chất Lỗi `Page.goto: Timeout exceeded` / `curl: (56) Recv failure: Connection was reset`
Khi thực hiện tự động hóa Playwright trên GPM Profile hoặc cURL qua cổng Singbox `192.168.110.2:200xx`:
- `192.168.110.2:200xx` là cổng **Singbox Inbound (Local proxy)** trên máy trạm trung gian.
- Socket kết nối tới `192.168.110.2:200xx` có thể **vẫn mở (PORT OPEN)** vì Singbox service đang chạy.
- Tuy nhiên, khi gửi gói tin HTTP ra ngoài Internet, Singbox chuyển tiếp tới **Upstream PPPoE/MobiProxy** (`test.taadaa.click:51xx`).
- Nếu cổng upstream bị nghẽn, mất mạng, đổi IP chưa xong, hoặc PPPoE session bị kẹt:
  - cURL báo: `curl: (56) Recv failure: Connection was reset`
  - Playwright báo: `playwright._impl._errors.TimeoutError: Page.goto: Timeout 15000ms/25000ms exceeded`, `net::ERR_CONNECTION_RESET`, hoặc `net::ERR_PROXY_CONNECTION_FAILED`.

---

## 2. Quy Tắc Bắt Buộc: Proxy Egress Preflight Trước Khi Khởi Động Trình Duyệt GPM

**CẤM TUYỆT ĐỐI** mở GPM Profile / Playwright và gọi `page.goto()` khi chưa kiểm chứng đường truyền egress của proxy có thông mạng Internet hay không.

### Script Kiểm Tra Preflight Nhanh (O(1), Timeout 5s):
```python
import requests

def check_proxy_egress(proxy_url: str, timeout_sec: int = 5) -> bool:
    """
    Kiểm tra proxy có thực sự ra được Internet hay không.
    proxy_url ví dụ: 'http://192.168.110.2:20011'
    """
    test_endpoints = [
        "http://httpbin.org/ip",
        "https://www.google.com/generate_204",
        "https://cloudflare.com/cdn-cgi/trace"
    ]
    for ep in test_endpoints:
        try:
            r = requests.get(ep, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout_sec)
            if r.status_code in [200, 204]:
                return True
        except Exception:
            continue
    return False
```

### Xử Lý Khi Preflight Thất Bại:
1. **Dừng lại ngay lập tức**: Không khởi chạy Playwright browser. Mở trình duyệt khi proxy chết chỉ làm lãng phí 25-30s timeout và có nguy cơ kích hoạt bot detection khi kết nối chập chờn.
2. **Tuân thủ Farm Invariant**: **CẤM TUYỆT ĐỐI** fallback sang direct IP hoặc gán chéo proxy sang máy khác.
3. **Báo cáo rõ ràng cho User/Admin**: Báo chính xác số máy, cổng proxy, và trạng thái `Connection reset / Dead upstream`.

---

## 3. Khắc Phục Lỗi OAuth Token Expired Cho Tài Khoản Đã Có Trong OmniRoute

### Hiện Tượng:
- Account có sẵn trong OmniRoute (`antigravity` provider) nhưng request tới Gemini/Claude trả về lỗi hoặc không nhận request.
- `GET /api/providers` báo: `testStatus: active` nhưng `tokenExpiresAt` đã quá hạn hàng chục tiếng, hoặc `expiresAt` < hiện tại.
- Lỗi dashboard: `Lỗi OAuth: invalid_grant` hoặc không thể refresh token.

### Quy Trình Re-Auth Cụ Thể (Targeted Re-auth):
1. **Tra cứu Profile GPM & Proxy tương ứng**:
   - Query `profile_data.db` của GPM để tìm đúng `ProfilePath` và `Proxy` tương ứng với email.
   - Singbox port: `20000 + Machine ID`.
2. **Kiểm tra Proxy Preflight**: Phải đảm bảo proxy kết nối Internet thành công.
3. **Lấy Authorize URL từ OmniRoute**:
   - `GET http://127.0.0.1:20129/api/oauth/antigravity/authorize?redirect_uri=http://127.0.0.1:20129/callback`
4. **Mở GPM Profile qua Playwright**:
   - Lắng nghe sự kiện `page.on('request', on_request)` để bắt tham số `code=` trong redirect về `/callback`.
   - Nếu profile còn session Google (`myaccount.google.com` sống): chỉ cần mở `authUrl`, chọn tài khoản, bấm Tiếp tục/Continue.
   - Nếu session Google hết hạn: Điền Password + TOTP 2FA từ `master_gmail_manager.xlsx`.
5. **Exchange Token**:
   - Gửi POST `http://127.0.0.1:20129/api/oauth/antigravity/exchange` kèm `code`, `codeVerifier`, `state`.
   - OmniRoute sẽ tự động cập nhật lại Access Token & Refresh Token mới cho account đó mà không làm mất cấu hình connection cũ.
