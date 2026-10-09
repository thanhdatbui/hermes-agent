# Selector Priority & False-Positive Traps in Multi-Step OAuth Flows (2026-09-15)

## 1. Bối cảnh sự cố
Trong quá trình phát triển module tự động liên kết tài khoản ChatGPT qua Google OAuth (`hook_chatgpt_register.py`) trên thiết bị Samsung S7 (Android 8.0), phát sinh 2 bẫy logic nghiêm trọng dẫn đến việc script tự báo cáo thành công ảo hoặc kẹt vô tận (timeout).

---

## 2. Bẫy 1: Title Email Collision vs Password Form Detection

### Hiện tượng
Khi Chrome điều hướng từ Google Account Chooser sang màn hình nhập mật khẩu (`accounts.google.com/v3/signin/challenge/pwd`), Google hiển thị địa chỉ email mục tiêu ở phần header/title của trang (dưới dạng TextView hiển thị danh tính đang đăng nhập).

### Mã lỗi (Anti-Pattern)
```python
# BƯỚC 2: Account Chooser & Password
while time.time() < deadline:
    xml = get_ui_xml(device_id)

    # LỖI: Quét email_clean trước khi kiểm tra challenge/pwd!
    acc_node = find_node_in_xml(xml, email_clean, prefer_clickable=False)
    if acc_node:
        tap(device_id, *acc_node["coord"], wait=3.0)
        time.sleep(1.0)
        continue  # BỊ KẸT TẠI ĐÂY VÔ HẠN!

    # Nhánh này không bao giờ được chạm tới vì acc_node luôn True trên trang password!
    if "challenge/pwd" in xml or "Hiện mật khẩu" in xml:
        # Xử lý nhập mật khẩu...
```

### Hậu quả
Script liên tục phát hiện `email_clean` (thực chất là text ở tiêu đề trang mật khẩu), liên tục tap vào tiêu đề và gọi `continue`. Script không bao giờ nhảy vào khối xử lý nhập mật khẩu, dẫn tới hết timeout và fail tại `FAILED_AT_ACCOUNT_SELECT`.

### Giải pháp chuẩn (Rule)
**BẮT BUỘC đảo thứ tự ưu tiên kiểm tra:**
1. Kiểm tra màn hình con sâu nhất / trạng thái xác thực tiếp theo trước (`challenge/pwd`, `oauth/id`, `about-you`).
2. Chỉ khi KHÔNG ở các màn hình đó mới quét danh sách Account Chooser để tap email.
```python
    # 1. Ưu tiên kiểm tra màn hình mật khẩu trước
    if "challenge/pwd" in xml or "Hiện mật khẩu" in xml or "Enter your password" in xml:
        # Xử lý nhập pass...
        continue

    # 2. Sau đó mới quét Account Chooser để chọn email
    acc_node = find_node_in_xml(xml, email_clean, prefer_clickable=False)
    if acc_node:
        tap(device_id, *acc_node["coord"], wait=3.0)
        time.sleep(1.0)
        continue
```

---

## 3. Bẫy 2: Dialog Hệ Thống Chrome Che Mất Web ("Đăng nhập vào Chrome")

### Hiện tượng
Khi bấm "Tiếp tục với Google" trên trang đăng nhập của bên thứ 3 (ChatGPT), Chrome trên Android thường hiển thị một bottom sheet / dialog hệ thống:
> *"Đăng nhập vào Chrome - Đăng nhập vào trang web này và Chrome để sử dụng dấu trang..."*  
> Có 2 nút: `Tiếp tục bằng tài khoản của [Tên]` hoặc `Bỏ qua`.

Nếu script không chủ động phát hiện và dismiss dialog này, trang web bên dưới sẽ bị chặn tương tác hoàn toàn.

### Giải pháp chuẩn (Rule)
Trong mọi vòng lặp chờ chuyển trang OAuth trên Android Chrome, luôn bổ sung bộ quét dialog hệ thống:
```python
if "Đăng nhập vào Chrome" in xml or "sử dụng dấu trang" in xml or "Sign in to Chrome" in xml:
    skip_btn = find_node_in_xml(xml, "Bỏ qua", "Skip", prefer_clickable=True)
    if skip_btn:
        tap(device_id, *skip_btn["coord"], wait=2.0)
    else:
        tap(device_id, 540, 1800, wait=2.0)  # Tọa độ nút Bỏ qua ở đáy màn hình
    time.sleep(1.0)
    continue
```

---

## 4. Bẫy 3: Gõ Keyevent 66 (Enter) Trúng URL Bar Thay Vì Submit Form

### Hiện tượng
Khi gọi `hide_keyboard(device_id)` bằng cách tap vùng header (`x=540, y=200`), trên trình duyệt Chrome Android, tọa độ này vô tình rơi trúng **thanh địa chỉ URL (`url_bar`)**. 
Sau đó nếu script gửi lệnh `input keyevent 66` (Enter), Chrome sẽ kích hoạt tìm kiếm Google với chuỗi URL dang dở (ví dụ `www.`) thay vì submit form đăng nhập của trang web!

### Giải pháp chuẩn (Rule)
- Tuyệt đối KHÔNG dùng tap mù header để ẩn bàn phím trong trình duyệt web di động.
- Tìm nút submit thật bằng XML (`find_node_in_xml(xml, "Tiếp theo", "Next")`) và tap trực tiếp vào tọa độ của nút submit thay vì dựa vào phím Enter mềm.
