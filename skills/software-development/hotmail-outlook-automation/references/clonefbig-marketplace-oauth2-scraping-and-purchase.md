# CloneFBIG Hotmail OAuth2 Purchase and Extraction Protocol

## 1. Context & Product Information
* **Shop**: `clonefbig.com` (Mã nguồn CMSNT / ShopClone7).
* **Sản phẩm Hotmail Graph API**:
  * Product ID: `3470`
  * Tên: *Hotmail - Outlook Trusted · Graph API Format · Live 6–12 Months · Recovery Mail Added (fviainboxes.com, smvmail.com)*
  * Giá: ~270đ ($0.0104 / acc).
  * Định dạng chuẩn: `email|password|refresh_token|client_id|recovery_email`.

---

## 2. Điểm Nghẽn API & Giải Pháp (API JSON Truncation Pitfall)

### Triệu chứng lỗi khi mua qua API thuần:
* Khi gọi `POST https://clonefbig.com/api/buy_product`:
  * API trả về `status: "success"` nhưng chuỗi `data` bị cắt ngắn trường `refresh_token` xuống còn ~101 ký tự (mất hơn 350 ký tự đuôi của chuỗi MSA Artifacts).
  * Khi đưa vào `hotmail_provider.exchange_refresh_token()`, máy chủ Microsoft trả về lỗi:
    `AADSTS70000: The provided value for the input parameter 'refresh_token' or 'assertion' is not valid.`

### Cơ chế trích xuất chuẩn qua Web UI / Chrome CDP:
* CSDL của shop lưu đầy đủ 100% token gốc (~457-500 ký tự).
* Trang chi tiết đơn hàng `https://clonefbig.com/product-order/<trans_id>` nhúng toàn bộ chuỗi token đầy đủ vào thuộc tính `data-checkbox` / value của checkbox:
  `<input type="checkbox" class="form-check-input checkbox_product_sold" data-checkbox="email|pass|FULL_TOKEN|client_id|rec_mail">`

---

## 3. Quy Trình Mua & Nạp Chuẩn Từng Bước

### Bước 1: Mua tài khoản qua Chrome CDP / AJAX
Gọi AJAX trong context trình duyệt đã đăng nhập (hoặc kèm `api_key`):
```javascript
$.ajax({
    url: 'https://clonefbig.com/ajaxs/client/product.php',
    method: 'POST',
    dataType: 'JSON',
    data: {
        action: 'buyProduct',
        id: 3470,
        amount: N,
        coupon: '',
        api_key: '<API_KEY>'
    },
    success: function(res) { console.log(res.trans_id); }
});
```

### Bước 2: Trích xuất chuỗi đầy đủ qua Chrome CDP (port 9222)
1. Điều hướng tab sang: `https://clonefbig.com/product-order/<trans_id>`.
2. Trích xuất dữ liệu từ các input/checkbox trên bảng:
```javascript
(() => {
    let rows = Array.from(document.querySelectorAll('table tbody tr'));
    return rows.map(r => {
        let inputs = Array.from(r.querySelectorAll('input, textarea')).map(i => i.value);
        return inputs[1] || inputs[0] || '';
    }).filter(Boolean);
})()
```

### Bước 3: Kiểm tra token với Microsoft Graph API
Trước khi nạp vào sheet, bắt buộc chạy hàm xác thực:
```python
from hotmail_provider import exchange_refresh_token

parts = line.split('|')
email, password, refresh_token, client_id = parts[0], parts[1], parts[2], parts[3]
access_token, err = exchange_refresh_token(refresh_token, client_id)
assert access_token is not None, f"Token dead: {err}"
```

### Bước 4: Nạp vào `gmail_clean_v2.xlsx`
1. Tạo backup `gmail_clean_v2_backup_<timestamp>.xlsx`.
2. Ghi từng tài khoản vào các cột:
   * Col 1: `số máy` (STT int)
   * Col 2: `tài khoản gmail` (email)
   * Col 3: `pass mail` (password)
   * Col 5: `mail khôi phục` (recovery email)
   * Col 7: `ngày tạo` (`YYYY-MM-DD`)
   * Col 9: `token` (refresh_token đầy đủ)
   * Col 10: `client_id` (client_id UUID)
3. Chạy `_detect_clean.py` và test suite để xác nhận nguồn mail đã sẵn sàng.
