# Gmail Switcher Bento Fallback & Google Transport Error Triage

## 1. Lỗi Fallback Bento Card trong Account Switcher (Gmail Android S7)

### Hiện tượng & Root Cause
- Trong `gmail_reg_v10.py`, hàm `find_add_account_card_in_switcher(xml)` có fallback:
  ```python
  # Cũ: Vùng quét quá rộng y >= 300
  if 300 <= y <= 1850 and x <= 700 and not is_storage:
      fallback_candidates.append(card)
  ```
- Trên Samsung S7 SM-G930F (độ phân giải 1080x1920), vùng header của tài khoản đang active nằm ở $y \approx 336$ (bounds `[408, 204][672, 468]`).
- Khi menu switcher mở lên mà nút "Thêm tài khoản khác" nằm ở phía dưới (cần cuộn) hoặc chưa kịp render, fallback sẽ chọn phần tử có $y$ nhỏ nhất $\rightarrow$ tap trúng header ở $y=336$:
  * **Trường hợp 1 (Máy 03):** Tap trúng icon avatar $\rightarrow$ mở màn hình *"Thêm ảnh hồ sơ"* (Google Profile Photo UI) $\rightarrow$ script không thấy provider Google $\rightarrow$ crash `[04_google] Không chọn được provider Google`.
  * **Trường hợp 2 (Máy 01):** Tài khoản cũ trên máy bị lỗi phiên / checkpoint, header hiển thị cảnh báo *"Đã xảy ra lỗi và bạn cần đăng nhập lại"*. Khi fallback tap trúng, Google Play Services bung popup *"Hoàn tất đăng nhập để tiếp tục"* $\rightarrow$ script kẹt ở màn re-auth $\rightarrow$ timeout `[04b] Google sign-in chưa load xong`.

### Giải pháp Chuẩn
1. **Chặn cứng biên độ $y \ge 700$:**
   ```python
   # Mới: Chỉ nhận card phía dưới header active profile
   if 700 <= y <= 1850 and x <= 700 and not is_storage:
       fallback_candidates.append(card)
   ```
2. **Kỷ luật Cuộn trước khi Fallback:**
   Trong `wait_and_tap_add_account_in_switcher`, luôn ưu tiên tìm exact text (`Thêm tài khoản khác` / `Add another account`). Nếu chưa thấy, bắt buộc swipe cuộn lên `(540, 1500) -> (540, 900)` trước khi thử dùng fallback card.

---

## 2. Google Signup Transport/Lifecycle Error (HTTP 0 / XHR 6)

### Hiện tượng
- WebView gửi RPC `/lifecycle/_/AccountLifecyclePlatformSignupUi/data/batchexecute` bị đứt kết nối (proxy rớt, socket timeout, Singbox disconnect):
  > `Error code = 7, Path = .../AccountLifecyclePlatformSignupUi/data/batchexecute, Message = There was an error during the transport or processing of this request., HTTP status = 0, Unknown HTTP error (HTTP Status: 0) (XHR Error Code: 6)`  
  > *"Đã xảy ra lỗi: Rất tiếc, đã xảy ra sự cố. Vui lòng thử lại."*
- Code trước đây chỉ kiểm tra `is_google_transport_or_lifecycle_error_xml` sau bước nhập Tên, bỏ quên ở **Bước 10 (Password)** và **Bước 11 (Review)**.
- Khi gặp lỗi mạng ở 2 bước này, script chạy hết timeout rồi raise `[11_review] Không thấy Review` hoặc `[10_pass] Chua vao dung man password`.
- Hệ thống watchdog gom vào `failed_other` và báo Telegram là **"Lỗi script: 14"**, gây hiểu lầm là script hỏng logic trong khi bản chất là lỗi mạng/hạ tầng.

### Giải pháp Chuẩn
- Tích hợp kiểm tra `is_google_transport_or_lifecycle_error_xml(xml)` tại:
  1. **Bước 10:** Khi không thấy màn password, kiểm tra transport error trước khi báo `[10_pass] Chua vao dung man password`.
  2. **Bước 11:** Trong nhánh `else` của review screen wait, kiểm tra transport error trước khi báo `[11_review] Không thấy Review`.
- Raise đúng exception chuẩn: `[GOOGLE_TRANSPORT_ERROR] Google/GMS transport error...`.
- Phân loại lỗi vào nhóm lỗi nền tảng / hạ tầng mạng, không gộp vào lỗi script.
