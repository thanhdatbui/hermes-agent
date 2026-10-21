# Sumistore Reseller / Sub-shop API Integration Architecture

## 1. Bản chất kiến trúc API Đấu Kho Hàng (sumistore.me)
- Hệ thống hỗ trợ tích hợp mở kho hàng tự động cho đại lý / bot / sub-shop.
- **Base URL:** `https://sumistore.me`
- **Tài liệu trực quan:** `https://sumistore.me/api/tele-guide?product_id={PRODUCT_ID}`

## 2. Xác thực (Authentication)
- Dùng **`API ID`** lấy trực tiếp từ Bot Telegram của shop (Vào bot Telegram shop -> API -> copy API ID).
- Gửi qua header bắt buộc cho mọi request:
  `X-Tele-API-ID: <TELE_API_ID>`
- Tuyệt đối không lưu API ID vào URL query parameters hoặc client-side local storage không an toàn.

## 3. Các Endpoint nghiệp vụ chính
| Method | Endpoint | Chức năng |
| :--- | :--- | :--- |
| `GET` | `/api/tele-products` | Lấy danh sách sản phẩm mở bán (chứa `products[].product_key`, `stock`, `available`) |
| `GET` | `/api/tele-products/{product_key}` | Chi tiết giá và tồn kho sản phẩm (vd: `p_9XGh048dZmiOkW0ppDKtwMgU` hoặc `SP-EJT5X2D7`) |
| `GET` | `/api/tele-balance` | Kiểm tra số dư Telegram hiện tại (`owner.balance`) |
| `GET` | `/api/tele-orders` | Lịch sử các đơn đã mua |
| `POST` | `/api/tele-product/buy` | Đặt mua hàng (bắt buộc ký HMAC-SHA256) |
| `GET` | `/api/tele-purchases/{job_id}` | Kiểm tra trạng thái đơn mua async |

### Lưu ý định dạng Product Key & Stock Monitor (Cập nhật 2026-10-21):
- Sản phẩm trên hệ thống dùng trường `product_key` (dạng chuỗi `p_<hash>`, ví dụ `p_9XGh048dZmiOkW0ppDKtwMgU`).
- Kiểm tra tồn kho thời gian thực: Polling `GET /api/tele-products/{product_key}` kiểm tra điều kiện `available == True` và `stock > 0`.
- Tần suất poll an toàn: 0.8s - 1.0s/lần (server phản hồi trung bình ~300ms; poll quá nhanh <0.3s dễ kích hoạt Cloudflare WAF/Challenge).
- Tiền điều kiện nạp số dư: Gọi `GET /api/tele-balance` xác nhận số dư Telegram `owner.balance >= price` trước khi bật sniper; mua hàng trừ tiền thẳng từ số dư Telegram bot.

## 4. Cơ chế ký bảo mật mua hàng (HMAC-SHA256 & Idempotency)
- **Công thức ký:**
  `message = f"{timestamp}|{nonce}|{body}"`
  `signature = hmac.new(api_id.encode(), message.encode(), hashlib.sha256).hexdigest()`
- **Headers bắt buộc khi gọi `/api/tele-product/buy`:**
  - `Content-Type: application/json`
  - `X-Tele-API-ID: <TELE_API_ID>`
  - `X-Timestamp: <UNIX_TIMESTAMP_SECONDS>` (hết hạn sau 300s)
  - `X-Nonce: <UUID_HEX_STRING>` (chuỗi duy nhất mỗi lần gọi)
  - `X-Signature: <LOWERCASE_HEX_SIGNATURE>`
  - `X-Idempotency-Key: <ORDER_KEY>` (khóa chống trừ tiền trùng lặp)
  - `Prefer: respond-async` (xử lý đơn hàng qua hàng đợi bền vững)

## 5. Python Implementation Template
```python
import os, time, uuid, hmac, hashlib, json, requests

def buy_product(api_id: str, product_id: str, quantity: int = 1):
    base_url = "https://sumistore.me"
    url = f"{base_url}/api/tele-product/buy"
    body = json.dumps({"id": product_id, "quantity": quantity})
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    order_key = f"order_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    raw_sig = f"{timestamp}|{nonce}|{body}".encode()
    signature = hmac.new(api_id.encode(), raw_sig, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Tele-API-ID": api_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "X-Idempotency-Key": order_key,
        "Prefer": "respond-async"
    }

    r = requests.post(url, data=body.encode(), headers=headers, timeout=30, allow_redirects=False)
    data = r.json()
    if r.status_code == 202:
        status_path = data.get("status_url")
        # Polling kết quả job đơn hàng
        time.sleep(1)
        res = requests.get(f"{base_url}{status_path}", headers={"X-Tele-API-ID": api_id}, timeout=20)
        return res.json()["purchase"]
    elif r.ok and data.get("success"):
        return data
    else:
        raise RuntimeError(data.get("message", "Mua chưa thành công"))
```

## 6. End-to-End Auto-Claim Workflow via GPM CDP & Cross-Host Alarm (Cập nhật 2026-10-21)
- **Quy chuẩn Auto-Claim trọn gói (Chống bẫy dừng nửa chừng):**
  - Đối với các sản phẩm giao link kích hoạt bảo hành siêu ngắn (5–10 phút như Gemini Pro 18M / Google One 5TB qua Jio): CẤM TUYỆT ĐỐI dừng lại ở việc khởi động browser rồi ném link cho User tự bấm tay. User yêu cầu tự động kích hoạt end-to-end 100%.
  - Luồng chuẩn: Bóc tách `activation_link` từ JSON response mua hàng -> Khởi chạy Profile GPM có Session Google Cookies sống qua Local API (`/api/v3/profiles/start/{id}?skip_proxy_check=true`) -> Lấy `data.remote_debugging_address` -> Kết nối Playwright qua CDP (`connect_over_cdp`) -> Mở URL đích.
- **Cạm bẫy Modal che nút kích hoạt Google One ("Nhận bộ nhớ" vs "Kích hoạt gói"):**
  - Trên trang đích `one.google.com/activate-plan/...`, các dòng mô tả lợi ích như *"Nhận tổng bộ nhớ 5 TB dùng chung..."* có gắn sự kiện click mở dialog giải thích. Nếu selector click nhầm vào text này, một modal xuất hiện kèm nút *"Đóng"*, vô hiệu hóa và che phủ nút hành động chính bên dưới.
  - **Khắc phục:** Bắt buộc đóng mọi modal dialog đang mở (`page.locator('button:has-text("Đóng")').click()`), sau đó click chính xác vào nút hành động `page.locator('button:has-text("Kích hoạt gói")')` (hoặc `button:has-text("Tham gia")` / `button:has-text("Chấp nhận")`). Hậu kiểm điều hướng thành công tại URL chứa `/celebration` với title `Google One Confirmation Page` và body *"Bạn là thành viên gói Google AI Pro"*.
- **Còi báo động liên tục xuyên máy (Cross-Host Continuous Alarm):**
  - Để báo hiệu khẩn cấp khi User rời máy tính: Điều phối qua `admin_ssh.py` bắn lệnh sang Admin-PC (`admin-farm` `192.168.110.119`) khởi chạy tiến trình nền `admin_alarm.py` (`winsound.Beep(1200, 250)` + `winsound.Beep(1800, 300)`).
  - Vòng lặp hú còi vô tận cho đến khi nhận được cờ dừng (`stop_admin_alarm.py` tạo file `stop_alarm.flag` hoặc gọi `pkill -f admin_alarm.py`), đảm bảo User không bị bỏ lỡ thông báo.
