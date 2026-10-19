# Physical Canary Gate & Dual-Checkpoint Visual Evidence Invariant

## 1. Incident Context: The "Run Canary Chưa" Failure
Khi vá sửa hoặc hoàn thiện các hàm thao tác UI/thiết bị (như bấm nút WinRT OCR, xử lý popup, thay đổi luồng tương tác):
- **Sai lầm thường gặp:** Chỉ chạy mock unit test trong phòng thí nghiệm (ví dụ `pytest test_mode1_ocr_tap.py` pass 10/10), sau đó tự mãn báo cáo xong hoặc hỏi xin phép: *"Anh cho phép em kích hoạt canary trên 1 máy thật nhé?"*.
- **Phản ứng gay gắt của User:** *"Tức là mày đéo thân thủ rule phải k"*.
- **Bài học cốt lõi:**
  1. Mock unit test **CHỈ** chứng minh logic ở mức module/unit; **KHÔNG BAO GIỜ** được coi là nghiệm thu hoàn tất cho tác vụ UI/Farm.
  2. Quyền chạy Canary đã được cấp sẵn trong ngân sách T1 (<= 15 dòng) và L0–L2. **CẤM TUYỆT ĐỐI** chờ User nhắc hoặc dùng `clarify` để xin phép chạy Canary.
  3. BẮT BUỘC chủ động chạy Canary trên 1 máy thật đại diện trước khi báo cáo hoàn thành.

---

## 2. Tiêu Chuẩn Thực Thi Canary Trên Thiết Bị Thật

### 2.1 Khóa Máy Bắt Buộc (Device Lock Invariant)
Mọi can thiệp ADB vào thiết bị farm thật bắt buộc phải có Lock, nếu không sẽ bị Hook Hard Gate chặn (`[HARD GATE #5 - DEVICE LOCK REQUIRED]`).
- BẮT BUỘC bọc qua `operator_device_lock` từ `automation_core`:
  ```python
  from automation_core import operator_device_lock

  # BẪY THAM SỐ CẦN TRÁNH:
  # Tham số định danh task là `project`, KHÔNG PHẢI `reason`!
  # Truyền `reason` sẽ gây lỗi: TypeError: acquire_device_lock() got an unexpected keyword argument 'reason'
  with operator_device_lock(machine=machine_id, serial=serial, project="canary_mode1_ocr_tap", timeout=60.0):
      # Thao tác thiết bị tại đây
  ```

### 2.2 Trình Tự Thực Thi 6 Bước An Toàn
1. **Đánh thức màn hình:**
   ```python
   adapter.shell(["input", "keyevent", "224"])  # KEYCODE_WAKEUP
   adapter.shell(["wm", "dismiss-keyguard"])
   time.sleep(1.0)
   ```
2. **Mở đúng màn hình mục tiêu:**
   Mở trực tiếp bằng deep-link/intent (ví dụ mở profile công khai chưa follow):
   ```python
   adapter.shell([
       "am", "start", "-a", "android.intent.action.VIEW",
       "-d", f"snssdk1180://user/profile?unique_id={target_user}",
       "com.ss.android.ugc.trill"
   ])
   time.sleep(5.0)  # Chờ app render đầy đủ, tránh chụp trúng splash screen loading
   ```
3. **Ảnh Hiện Trường Trước Thao Tác (Checkpoint 1 - Pre-Action):**
   ```python
   png_pre = adapter.screencap()
   pre_shot.write_bytes(png_pre)
   ```
4. **Thực thi hành động cần nghiệm thu:**
   Gọi hàm production thật (ví dụ `_tap_follow_button(engine)`).
   Theo dõi telemetry và log (`[OCR_TAP_SUCCESS]`, tọa độ `center=(x, y)`, v.v.).
   `time.sleep(3.0)` để app hoàn tất animation/chuyển trạng thái giao diện.
5. **Ảnh Hiện Trường Sau Thao Tác (Checkpoint 2 - Post-Action):**
   ```python
   png_post = adapter.screencap()
   post_shot.write_bytes(png_post)
   ```
6. **Teardown sạch sẽ về HOME:**
   ```python
   adapter.shell(["input", "keyevent", "3"])  # KEYCODE_HOME
   ```

---

## 3. Invariant LLM Soi Mắt Đối Chiếu Cặp Ảnh Trước Khi Gửi (Dual-Checkpoint Vision)

Sau khi có 2 file ảnh `canary_pre.png` và `canary_post.png`:
- **CẤM TUYỆT ĐỐI gửi ảnh mù:** Cấm gửi thẳng `MEDIA:<path>` kèm lời mô tả chung chung vô cảm hoặc suy đoán từ log.
- **Thao tác bắt buộc:** Gọi `browser_navigate` và `browser_vision` mở lần lượt từng ảnh để soi mắt:
  1. *Soi ảnh Pre-action:* Xác nhận đúng profile, nút mục tiêu đang ở trạng thái ban đầu (ví dụ nút màu đỏ "Follow" hiển thị rõ dưới chỉ số follower).
  2. *Soi ảnh Post-action:* Xác nhận trạng thái nút đã biến đổi thực tế (nút đỏ biến mất, xuất hiện nút xám "Đã follow v" / "Nhắn tin", popup đề xuất bật lên).
- **Phản hồi có bằng chứng:** Trong tin nhắn trả lời User, BẮT BUỘC tường thuật ngắn gọn chi tiết đã thấy tận mắt qua vision đối chiếu giữa 2 ảnh trước khi đính kèm thẻ `MEDIA:<path>`.
