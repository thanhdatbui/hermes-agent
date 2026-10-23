# GPM Profile Trash (GroupId == 0) Trap & SumiStore Dynamic Price / Preflight Discipline (2026-10-23)

## 1. Cạm Bẫy `PROFILE_IN_TRASH` & Quy Ước `GroupId` Trong GPMLogin SQLite
- **Hiện tượng:** Khi truy vấn trực tiếp bảng `Profiles` trong `profile_data.db` mà không kiểm tra trường `GroupId`, script có thể bốc trúng profile có session Google rất đẹp (`SID, HSID, SSID` còn hạn) nhưng khi gọi Local API khởi động:
  ```text
  GET /api/v3/profiles/start/{profile_id}?skip_proxy_check=true
  ```
  API trả về:
  ```json
  {"success": false, "data": null, "message": "PROFILE_IN_TRASH"}
  ```
  Việc cố truy cập `data["remote_debugging_address"]` gây văng lỗi `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Cấu trúc `GroupId` trong GPMLogin DB:**
  - `GroupId = 0`: **TRASH / RECYCLE BIN** (Profile đã bị xóa tạm vào thùng rác, Local API từ chối khởi chạy).
  - `GroupId = 1`: **All / Default group**.
  - `GroupId = 10`: **Google_Live_Ready** (Group chuẩn hóa chứa các tài khoản Gmail nuôi sống khỏe, sẵn sàng nhận link / đăng nhập).
  - `GroupId = 11`: **Google_Cooldown_Error** (Tài khoản đang bị cách ly kiểm tra).
- **Quy chuẩn truy vấn (Fail-Closed):**
  Mọi script lọc profile Gmail sống (như `find_healthy_gmail.py`, sniper candidate picker) **BẮT BUỘC** lọc tường minh:
  ```sql
  SELECT Id, Name, ProfilePath, JsonData, GroupId 
  FROM Profiles 
  WHERE GroupId = 10;
  ```
  Tuyệt đối cấm quét toàn bộ bảng `Profiles` mà bỏ qua `GroupId`.

---

## 2. SumiStore Dynamic Price Drift & Kiểm Tra Số Dư Thời Gian Thực
- **Biến động giá sản phẩm Flash:** Sản phẩm `Link Gemini Pro 18M (Phải dùng ngay)` (`SP-TY9J9GO9`) ban đầu có giá 9.000đ, nhưng shop có thể điều chỉnh giá lên 17.000đ (hoặc cao hơn) tùy thời điểm.
- **Cạm bẫy Hardcode:** Nếu script sniper hardcode giá `9000` (`if bal < 9000:`), khi tài khoản Telegram có đúng 17.000đ và giá hàng là 17.000đ, script sẽ đưa ra thông tin sai lệch hoặc không cảnh báo đúng khi giá biến động.
- **Chuẩn hóa:** Bắt buộc đọc `price` trực tiếp từ endpoint `GET /api/tele-products/{PRODUCT_ID}`:
  ```python
  prod = data.get("product", {})
  price = prod.get("price", 17000)
  if bal < price:
      print(f"[⚠️ CẢNH BÁO] Số dư hiện tại ({bal:,.0f}đ) < giá sản phẩm ({price:,.0f}đ)!")
  ```

---

## 3. URL Kiểm Tra Family Google Chuẩn Xác Trong Preflight
- **Cạm bẫy Redirect:** URL `https://families.google.com/families` trên trình duyệt máy tính tự động redirect về trang marketing ngoài `https://families.google/families/` chứ không trỏ vào trang quản lý tài khoản thực tế.
- **URL Chuẩn:** BẮT BUỘC dùng URL quản lý cài đặt Google Account Family:
  ```text
  https://myaccount.google.com/family/details
  ```
- **Dấu hiệu tài khoản sạch (Clean Family State):**
  - Giao diện hiển thị: *"Gia đình của bạn trên Google"* kèm nút lớn **"Bắt đầu"** (Start).
  - Không có danh sách thành viên hiện hữu, không có cảnh báo dính nhóm gia đình cũ.
  - Sau khi preflight xác nhận URL và text "Bắt đầu", tab được giữ Warm trong bộ nhớ RAM qua CDP để chuyển hướng sang link mua trong `< 0.5s`.
