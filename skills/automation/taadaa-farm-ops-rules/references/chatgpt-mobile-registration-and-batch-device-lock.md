# ChatGPT Mobile Registration & Batch Device Lock Invariants

## 1. WebView Input Matching Quirk (Chrome on Android / S7)
- **Vấn đề:** Khi mở link ChatGPT signup (`chatgpt.com/auth/login?screen_hint=signup`), ô nhập email trong Chrome WebView có:
  - `text=""`
  - `content-desc=""`
  - `resource-id="email"`
  - `hint="Email address"`
- **Pitfall:** Hàm tìm kiếm XML thông thường nếu chỉ soi `text`, `content-desc`, `resource-id` sẽ bỏ qua thuộc tính `hint`, dẫn đến `find_node_in_xml(...)` trả về `None`.
- **Quy tắc:**
  - `node_has_target` bắt buộc phải bao gồm `attrs.get("hint", "")` vào danh sách giá trị cần kiểm tra.
  - Vị trí tìm kiếm ô input email phải truyền target `"email"` kèm theo: `find_node_in_xml(xml, "Email address", "Địa chỉ email", "email", prefer_clickable=True)`.

## 2. Omnibox & Keyevent 4 (Back Navigation) Pitfalls
- **CẤM TUYỆT ĐỐI `keyevent 4` (KEYCODE_BACK) để ẩn bàn phím trong WebView:** Khi bàn phím chưa kịp hiển thị hoặc đã tự ẩn, `keyevent 4` sẽ đóng tab Chrome hoặc văng thẳng ra màn hình Home của Samsung S7, khiến các bước gõ email / OTP tiếp theo chạy mù trên Home launcher.
- **Tránh thanh Omnibox URL của Chrome:** Không tap tọa độ `(540, 200)` vì trúng vào vùng thanh địa chỉ (Y=60..220) kích hoạt chế độ gõ URL và bàn phím ảo nhảy lên.
- **Vị trí ẩn phím an toàn:** Tap vào vùng trống logo/header dưới thanh URL, ví dụ `(540, 600)`.

## 3. Bắt buộc DeviceLock độc quyền khi chạy Batch
- **Quy tắc:** Mọi runner tương tác với thiết bị (kể cả script batch tạm thời, ad-hoc runner hay watchdog) **BẮT BUỘC** phải gọi `acquire_device_lock` từ `automation_core.device_lock`:
  ```python
  from automation_core.device_lock import DeviceLock, DeviceLockUnavailable, acquire_device_lock

  device_lock = acquire_device_lock(
      machine=str(stt),
      serial=serial,
      project="chatgpt_link",
      user_authorized=True  # Ngăn cản tuyệt đối cronjob feed/avatar cướp quyền
  )
  try:
      # Thực thi tác vụ can thiệp thiết bị...
  finally:
      device_lock.release()
  ```
- **Hậu quả nếu thiếu:** Các cronjob chạy ngầm (nuôi feed, upload avatar, dọn dẹp) khi thức dậy sẽ kiểm tra `C:\Users\Kibe\.codex\device-locks`, thấy máy không có cờ lock sẽ lập tức chiếm foreground thiết bị và đè chết app đang chạy.

## 4. Canary Gate & Done Gate Enforcement
- Khi sửa code AUTOMATION (tương tác trực tiếp với thiết bị farm):
  - Unit test pass $\neq$ Bug fixed. Thiết bị thật là oracle duy nhất có giá trị.
  - Bắt buộc kiểm tra và chạy Canary trên $\ge 1$ máy rảnh qua `python D:/Taadaa/tools/done_gate.py --task-type automation --canary-file <path_anh>`.
  - Cấm lấp liếm/bào chữa khi bị bắt lỗi. Phản hồi chuẩn hóa theo format:
    `[FAULT-CONFIRMED] + Evidence + Root Cause + Structural Fix + Verification`.
