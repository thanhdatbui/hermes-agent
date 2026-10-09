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
| `GET` | `/api/tele-products` | Lấy danh sách sản phẩm mở bán |
| `GET` | `/api/tele-products/{id}` | Chi tiết giá và tồn kho sản phẩm (vd: `SP-EJT5X2D7`) |
| `GET` | `/api/tele-balance` | Kiểm tra số dư Telegram hiện tại |
| `GET` | `/api/tele-orders` | Lịch sử các đơn đã mua |
| `POST` | `/api/tele-product/buy` | Đặt mua hàng (bắt buộc ký HMAC-SHA256) |
| `GET` | `/api/tele-purchases/{job_id}` | Kiểm tra trạng thái đơn mua async |

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
