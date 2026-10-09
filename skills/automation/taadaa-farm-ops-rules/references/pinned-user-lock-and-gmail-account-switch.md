# Pinned User Device Lock, Chrome Tab Drift Prevention & Gmail Bento Account Switching (2026-09-20)

## 1. Pinned User Lock & 1h TTL Architecture (Bảo Vệ Lệnh Của User)

### Vấn đề:
Khi người dùng trực tiếp ra lệnh can thiệp, chạy batch hoặc canary test trên một máy cụ thể, nếu script chỉ gọi ADB trần hoặc xin lock thường (`user_authorized=False`), các tiến trình cronjob nuôi nick tự động (ví dụ `phase9-runner-tiktok-feed`, `post_evening_avatar_watchdog`) thức dậy theo lịch sẽ cướp quyền điều khiển thiết bị (đẩy TikTok hoặc trang sửa hồ sơ lên foreground).

### Cơ chế Pinned Lock (`automation_core.device_lock`):
- Mọi lệnh do người dùng/operator trực tiếp kích hoạt bắt buộc dùng `user_authorized=True`:
  ```python
  from automation_core.device_lock import DeviceContext

  with DeviceContext(serial=serial, machine=str(stt), project="operator-task", user_authorized=True) as lease:
      # Thiết bị được bảo vệ tuyệt đối trong khối này
      ...
  ```
- **Quy tắc bảo vệ Pinned Lock:**
  1. File lock sinh ra mang cờ `"user_authorized": true`, `"pinned": true`, `"ttl_seconds": 3600`.
  2. Mọi cronjob tự động (`user_authorized=False` hoặc takeover thông thường) khi gặp Pinned Lock đều bị **CHẶN ĐỨNG NGAY LẬP TỨC** (`DeviceLockNeedsUserDecision` hoặc `DeviceLockUnavailable`).
  3. Chỉ có cờ can thiệp tối cao `force_preempt=True` (`TAKEOVER_SCOPE_OPERATOR_PREEMPT`) mới có quyền reclaim.
- **Bảo toàn TTL 1 Giờ (Chống Deadlock Farm qua đêm):**
  - Reaper (`reap-dead-owner-locks.py`) chạy định kỳ mỗi 5 phút:
    + Nếu PID chủ đã chết (`owner_alive is False`): Thu hồi lock ngay lập tức (orphan crash).
    + Nếu PID còn sống hoặc không rõ, nhưng thời gian giữ lock >= 3600s (1 giờ): Thu hồi lock với lý do `pinned_1h_ttl` để giải phóng thiết bị, không để farm bị kẹt cứng sang ca sáng hôm sau.

---

## 2. Phòng Chống Trôi Tab Chrome (Chrome Tab Drift Protection)

### Vấn đề:
Khi switch qua lại giữa app đọc OTP (Gmail) và Chrome, nếu chỉ gọi intent trần:
`shell(device_id, "am", "start", "-n", "com.android.chrome/com.google.android.apps.chrome.Main")`
Chrome sẽ mở lại tab foreground gần nhất trước đó (ví dụ tab tìm kiếm Google cũ `google.com/search?q=...`), dẫn đến việc script không tìm thấy ô nhập OTP và click mù vào kết quả tìm kiếm Google.

### Giải pháp bắt buộc:
Sau khi đưa Chrome lên foreground, kiểm tra URL hoặc DOM XML:
```python
xml = get_ui_xml(device_id) or ""
if "google.com" in xml.lower() and not ("openai" in xml.lower() or "chatgpt" in xml.lower()):
    # Lập tức navigate hoặc bắn intent đưa lại về đúng URL đăng ký
    shell(device_id, "am", "start", "-a", "android.intent.action.VIEW", 
          "-d", "https://chatgpt.com/auth/login?screen_hint=signup", "com.android.chrome")
    time.sleep(2.0)
    xml = get_ui_xml(device_id) or ""
```

---

## 3. Cơ Chế Switch Account Trong App Gmail (Google Bento Popup)

### Vấn đề:
Trên các máy Phone Farm có 4–8 tài khoản Google. Khi mở app Gmail để nhận mã OTP của tài khoản vừa đăng ký, app Gmail thường hiển thị hòm thư của một tài khoản cũ (hoặc tài khoản TikTok trước đó). Nếu script chỉ quét mã 6 số regex mù quáng, nó sẽ nhặt nhầm mã OTP cũ (ví dụ mã xác nhận TikTok gửi từ tháng trước) và điền vào form -> Báo lỗi *"Mã không chính xác"*.

### Cạm bẫy Bento Header Popup:
Khi tap vào avatar Gmail góc trên phải (`985, 138`), Google hiện ra popup Bento:
- Tài khoản đang active nằm ở header: `og_compact_header_secondary_text`.
- Các tài khoản phụ nằm ở danh sách dưới: `og_secondary_account_information`.
**CẢNH BÁO TỬ HUYỆT:** Nếu `find_node_in_xml(xml, target_email)` match trúng node header `og_compact_header`, việc tap vào node này sẽ mở trang **Quản lý Tài khoản Google (Google Account Settings)** và che khuất hoàn toàn app Gmail!

### Quy trình Switch Account chuẩn (`ensure_gmail_account_active`):
1. Mở app Gmail, tap avatar (`985, 138`).
2. Nếu `target_email` nằm trong `og_compact_header`: ĐÃ ACTIVE $\rightarrow$ CẤM TAP VÀO HEADER, tap ngoài popup (`540, 1800`) để đóng và tiếp tục.
3. Nếu `target_email` nằm trong `og_secondary_account`: TAP ĐỂ CHUYỂN SANG NICK ĐÓ $\rightarrow$ Bỏ qua các dialog phụ ("Không, cảm ơn", "Bỏ qua").
4. **Lọc người gửi OTP nghiêm ngặt:** Chỉ trích xuất mã OTP khi tiêu đề hoặc XML xác nhận có chứa `"OpenAI"` hoặc `"ChatGPT"`. Tuyệt đối không lấy mã từ mail TikTok hay dịch vụ khác.
