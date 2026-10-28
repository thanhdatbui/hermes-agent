# 9Router Port 20128 Multimodal Fallback & Farm Tool UI Recognition

## Bối Cảnh Thực Chiến
Khi nhận ảnh chụp màn hình từ Telegram (`image_cache/img_*.jpg`), hệ thống có thể gặp lỗi phân tích ảnh phụ (`Error: No module named 'agent.aux_accounting'`) hoặc `browser_vision` không phản hồi. Đồng thời, cổng `:20129` (OmniRoute `auto/best-vision`) có thể bị timeout (>60s).

Nếu chỉ dựa vào WinRT OCR trên giao diện phần mềm phức tạp (nhiều cửa sổ con, font chữ nhỏ, ký tự đặc biệt như `$`), OCR tiếng Anh (`en-US`) sẽ làm méo mó nghiêm trọng:
- Dấu `$` bị nhận nhầm thành chữ `S` (ví dụ `55k$` biến thành `SS0k` dẫn tới hiểu lầm 550.000 VNĐ).
- Tên model và thiết bị bị cắt cụt (ví dụ `SM-G930F`, tên tool `v9.11.147 VIP`).
- Dễ dẫn tới ảo giác suy diễn sai bản chất sản phẩm (đoán mò là PC văn phòng cũ hoặc máy chủ AI thay vì tool tự động hóa farm).

## Quy Trình Cứu Hộ O(1) Qua 9Router (Port 20128)
Cổng `20128` (9Router) thường xuyên active trên localhost và hỗ trợ multimodal vision qua model `gpt-5.6-luna`:

```python
import base64, json, os, urllib.request

with open(r'D:\Taadaa\target.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

payload = {
    'model': 'gpt-5.6-luna',
    'messages': [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'Phân tích chi tiết giao diện trong ảnh: tool/phần mềm gì, chức năng gì, các thông số chính?'},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
            ]
        }
    ]
}

req = urllib.request.Request(
    'http://127.0.0.1:20128/v1/chat/completions',
    data=json.dumps(payload).encode(),
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ.get("NINEROUTER_API_KEY", "")}'
    }
)

with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read())
    print(data['choices'][0]['message']['content'])
```

## Dấu Hiệu Nhận Diện Tool Phone Farm Multi-Device
1. **Lưới thiết bị (Grid Matrix):** Màn hình chia thành hàng chục ô nhỏ (ví dụ 01 đến 76, 80 máy), mỗi ô mang tên mã máy (ví dụ `SM-G930F` = Samsung Galaxy S7).
2. **Cột điều khiển bên phải (Control Sidebar):** Chứa các nút ADB hàng loạt (`Vuốt Tự Động`, `Ghi lại hành động`, `Thực hiện nhiệm vụ`, `Lệnh ADB`, `Cài đặt APK`, `Đổi tên/info`).
3. **Thanh tiêu đề (Title Bar):** Thường có định dạng `[Tên Tool] vX.X.X (Phiên bản VIP / Pro)`.
4. **Mục đích sử dụng:** Thường liên quan đến cày view, tương tác mạng xã hội hoặc auto đặt đơn / áp voucher TikTok Shop (hiển thị màn hình chi tiết đơn COD, voucher giảm giá).
