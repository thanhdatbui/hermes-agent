# 5sim Realtime Price Quota, Live Inventory Probing & Auto-Retry Refund Architecture

## 1. Bản chất cơ chế 5sim: Hold Balance & Zero-Cost Probing
- **Hold Balance**: Khi gọi `GET /v1/user/buy/activation/{country}/{operator}/{product}`, 5sim chỉ tạm khóa (hold) số tiền tương ứng.
- **Auto Refund**:
  - Nếu trong 50s–60s không nhận được SMS OTP từ OpenAI, gọi `GET /v1/user/cancel/{order_id}` thì 5sim hoàn lại 100% số tiền ngay lập tức (`status: "CANCELED"`).
  - Tận dụng cơ chế này để viết script xoay vòng thử liên tục hàng chục số với chi phí thực tế là **0đ** cho tới khi có OTP thực tế.
- **Finish Order**: Chỉ gọi `GET /v1/user/finish/{order_id}` sau khi đã nhận mã OTP và verify thành công.

## 2. Bẫy dữ liệu ảo trên 5sim API: Stock > 0 nhưng "no free phones"
- **Hiện tượng**: `GET /v1/guest/prices?product=openai` báo `count: 250000+` (ví dụ Thailand, Vietnam), nhưng khi gửi lệnh mua thật qua API (`/buy/activation/...`) thì nhận về HTTP 200 kèm text `no free phones`.
- **Nguyên nhân**: Số lượng `count` trong bảng giá là dung lượng tổng danh bạ mạng của nhà mạng đó, không phải số lượng sim đang cắm trong khay modem thực tế.
- **Quy tắc**:
  - Luôn kiểm tra `if r.status_code == 200 and "no free phones" not in r.text:` để phát hiện tình trạng cháy hàng tạm thời.
  - Sàng lọc nhanh các nhà mạng thực sự mua được số (`can_buy == True`).

## 3. Phân khúc giá <= $0.10 cho OpenAI Phone Verification
- **Thực tế tỷ lệ giao OTP (OpenAI)**:
  - Các dải số siêu rẻ ($0.03 – $0.06 như England, Argentina, Brazil) có tỷ lệ nhận code thực tế 24h chỉ khoảng 1% – 5% (do bị bot MMO khai thác nhiều).
  - Các nước có tỷ lệ cao nhất trong phân khúc <= $0.10:
    1. **Bồ Đào Nha (`portugal` / `virtual51` - $0.10)**: Tỷ lệ 7 ngày đạt ~14.2%, kho số sạch.
    2. **Nam Phi (`southafrica` / `virtual66` - $0.10)**: Tỷ lệ 7 ngày đạt ~14.6%, kho số dồi dào (>190.000 số).
    3. **Anh (`england` / `virtual51` - $0.0609)**: Tỷ lệ 7 ngày đạt ~8.2%, giá siêu rẻ (~1.500đ).

## 4. Tự động hóa cập nhật giá và tỷ lệ Realtime trong Script
Thay vì fix cứng danh sách quốc gia trong code, script bắt buộc phải có hàm quét bảng giá động:
```python
def get_live_cheap_pool(max_price=0.1005):
    r = requests.get("https://5sim.net/v1/guest/prices?product=openai", headers=headers, timeout=10)
    data = r.json().get("openai", {})
    pool = []
    for country, ops in data.items():
        iso = ISO_MAP.get(country)
        if not iso: continue
        for op_name, details in ops.items():
            cost = details.get("cost", 0)
            count = details.get("count", 0)
            rate72 = details.get("rate72", 0)
            rate168 = details.get("rate168", 0)
            if cost <= max_price and count > 0 and (rate72 > 0.5 or rate168 > 0.5):
                pool.append({
                    "country": country, "iso": iso, "operator": op_name,
                    "cost": cost, "rate72": rate72, "rate168": rate168
                })
    # Ưu tiên tỷ lệ thành công 3-7 ngày gần nhất, sau đó đến giá rẻ
    pool.sort(key=lambda x: (-x["rate72"], -x["rate168"], x["cost"]))
    return pool
```

## 5. Tự động hóa DOM `auth.openai.com/add-phone` qua Playwright CDP
1. **Dropdown Quốc gia**: Là React-Aria Listbox (`button[aria-haspopup="listbox"]`). Click button mở list, sau đó tìm option theo selector `[role="option"][id*="-option-{ISO}"]` (ví dụ `PT`, `ZA`, `GB`, `AR`) và dispatch click.
2. **Channel SMS**: Luôn đảm bảo chọn radio SMS thay vì WhatsApp:
   `document.querySelector('input[type="radio"][value="sms"]')?.click()`
3. **Prefix điện thoại**: 5sim trả về số có kèm mã quốc gia (`+27...`, `+351...`). Bắt buộc bóc tách mã quốc gia trước khi điền vào `input[type="tel"]` vì dropdown OpenAI đã tự mang prefix.
4. **Bắt lỗi từ OpenAI**: Kiểm tra ngay selector `[role="alert"], [data-error]` sau khi submit. Nếu OpenAI từ chối số ("This phone number cannot be used..."), lập tức gọi API cancel hoàn tiền ngay và chuyển số mới mà không cần chờ 50s.
