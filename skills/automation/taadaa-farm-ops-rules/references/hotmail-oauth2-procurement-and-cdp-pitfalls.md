# Quy Chuẩn Mua Hotmail OAuth2 & Xử Lý Cạm Bẫy Cổng Chrome CDP Trên Farm

## 1. Nguồn Cung Cấp Hotmail OAuth2 (CloneFBIG vs BoxTaiKhoan)

### A. CloneFBIG (Nguồn chính khuyến nghị - Đã nghiệm thu)
- **Thông tin dịch vụ**: Nhà cung cấp `clonefbig.com` (CMSNT ShopClone7).
- **Sản phẩm mục tiêu**: ID `3470` — *Hotmail - Outlook Trusted · Graph API Format · Live 6–12 Months · Recovery Mail Added (fviainboxes.com, smvmail.com)*.
- **Đơn giá**: 270 VNĐ / tài khoản.
- **Tồn kho thực tế**: Dồi dào (>4.700 accounts sẵn sàng xuất kho).
- **Cơ chế gọi API**:
  - Endpoint: `POST https://clonefbig.com/ajaxs/client/product.php`
  - Headers:
    - `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`
    - `X-Requested-With: XMLHttpRequest`
    - `Content-Type: application/x-www-form-urlencoded`
  - Form-data:
    ```ini
    action=buyProduct
    id=3470
    variant_id=0
    amount=1
    coupon=
    api_key=<CLONEFBIG_API_KEY>
    user_input={}
    ```
  - **Quy tắc mua**: BẮT BUỘC mua lẻ từng tài khoản (`amount=1`) qua vòng lặp để nhận trực tiếp mảng `data` trong phản hồi JSON, tránh lỗi cắt token khi xuất file lô trên web.
- **Cấu trúc dữ liệu trả về**: 5 trường phân cách bởi dấu `|`:
  `email|password|refresh_token|client_id|recovery_email`
- **Chất lượng Token**:
  - Độ dài `refresh_token`: 489 ký tự (chuỗi Microsoft MSA Artifacts nguyên vẹn, không bị cắt ngắn).
  - Client ID chuẩn: `9e5f94bc-e8a4-4e73-b8be-63364c29d753` (ứng dụng Office/Outlook).
  - Xác thực thành công HTTP 200 trả về `access_token` hợp lệ khi gửi request tới:
    `POST https://login.microsoftonline.com/consumers/oauth2/v2.0/token`

### B. BoxTaiKhoan (Nguồn cũ - Thường xuyên lỗi xuất kho)
- **Tình trạng**:
  - Mã cũ (Product 60): Đã bị shop xóa khỏi danh mục sản phẩm.
  - Mã mới (Product 129): Báo còn tồn kho trên web nhưng hệ thống fulfillment tự động bị lỗi. Khi đặt hàng qua API hoặc Web UI đều trả về:
    `"Không thể xử lý đơn hàng lúc này, vui lòng thử lại sau ít phút. Tiền đã được hoàn về tài khoản."`
- **Kết luận**: Tạm dừng đặt đơn trên BoxTaiKhoan cho đến khi shop khắc phục server xuất kho.

---

## 2. Công Cụ Tự Động Mua & Nạp Dữ Liệu (`buy_hotmail.py`)

- **Đường dẫn**: `D:\Taadaa\tools\buy_hotmail.py` (đồng bộ qua `D:\OneDrive\Taadaa_Sync_Shared\tools\buy_hotmail.py` cho cả Kibe và Admin).
- **Cấu hình mặc định**:
  - Provider: `clonefbig` (chuyển đổi qua lại bằng cờ `--provider clonefbig|boxtaikhoan`).
  - Product ID mặc định: `3470` cho clonefbig, `129` cho boxtaikhoan.
  - Tự động nạp vào workbook Admin (`--append-admin <N>`):
    - Tự động dò dòng trống bắt đầu từ STT máy `201+`.
    - Ghi đủ 11 cột tiêu chuẩn vào `D:\OneDrive\TaadaaData\admin\gmail_clean_v2.xlsx`.
    - Điền `recovery_email` vào cột 5 (*mail khôi phục*) nếu dữ liệu nhà cung cấp có trả về.
- **Lệnh mẫu**:
  ```bash
  # Mua 10 tài khoản và nạp tự động cho máy Admin (201+)
  D:/Taadaa/python-envs/automation/Scripts/python.exe D:/Taadaa/tools/buy_hotmail.py --provider clonefbig --append-admin 10
  ```

---

## 3. Cạm Bẫy Cổng Chrome CDP Port 9222 & ADB Forward

- **Hiện tượng**:
  - Chạy Chrome với cờ `--remote-debugging-port=9222`, nhưng khi gọi `curl http://127.0.0.1:9222/json/version` thì bị lỗi `curl: (52) Empty reply from server` hoặc kết nối không phản hồi.
- **Nguyên nhân gốc rễ**:
  - Trên host Windows điều khiển Farm Android, tiến trình ADB thường xuyên chạy các lệnh chuyển tiếp cổng:
    `adb forward tcp:9222 localabstract:chrome_devtools_remote`
  - Lệnh này chiếm giữ cổng IPv4 `127.0.0.1:9222` để giao tiếp với WebView/Chrome trên điện thoại Android kết nối qua USB.
  - Khi Chrome PC khởi động với `--remote-debugging-port=9222`, nó không thể bind vào `127.0.0.1:9222` nên fallback bind vào cổng IPv6 `[::1]:9222`.
- **Giải pháp & Kỷ luật kiểm tra**:
  1. Kiểm tra PID và địa chỉ đang lắng nghe:
     ```bash
     netstat -ano | grep 9222
     ```
  2. Nếu thấy `127.0.0.1:9222` do `adb.exe` nắm giữ và `[::1]:9222` do `chrome.exe` nắm giữ:
     - Gọi CDP qua IPv6: `http://[::1]:9222/json/version` hoặc `ws://[::1]:9222/...`
     - Trong Playwright: `browser = p.chromium.connect_over_cdp("http://[::1]:9222")`
  3. TUYỆT ĐỐI KHÔNG tự ý kill ADB server khi farm đang vận hành vì sẽ làm đứt kết nối 80-160 thiết bị đang chạy ca.
