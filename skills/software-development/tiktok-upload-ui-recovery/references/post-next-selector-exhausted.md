# POST_NEXT_SELECTOR_EXHAUSTED: Root Cause, UI Pattern & Fix Guide

## 1. Triệu Chứng (Symptom)
- Error code: `[FAILED] [POST_NEXT_SELECTOR_EXHAUSTED] POST: final composer/editor Next surface was not confirmed`
- Xảy ra tại: `WorkflowState.POST` trong `state_machine.py` (`D:/Taadaa/Tiktok-video`).

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Màn hình "Xem trước" (Preview / Single-surface Composer)**:
   - Build TikTok mới trên nhiều máy (ví dụ máy 34) không dùng flow 2 bước (Editor Next -> Composer -> Post), mà sau khi chọn video mở thẳng màn hình "Xem trước" với:
     - Header / Tiêu đề: `"Xem trước"`
     - Caption, hashtag, nhạc đã được render sẵn
     - Góc dưới bên phải: Nút màu hồng/đỏ hình viên thuốc (pill button) có icon mũi tên hướng lên kèm chữ `"Đăng"`.
   - Trên màn hình này **hoàn toàn không có nút "Tiếp" hoặc "Next"**.
2. **Cơ chế Fallback bị trôi vào Selector Next**:
   - Khi logic `state_machine.py` quét nút `"Đăng"` trên preview:
     ```python
     if not post_tapped and 'text="Đăng"' in xml_text and "Xem trước" in xml_text:
         post_tapped = self._tap_post_with_intent(adapter, xml_text, text="Đăng")
     ```
   - Nếu nút Đăng có thuộc tính `content-desc="Đăng"` (hoặc nằm trong ViewGroup/Button có icon khiến node không có `text="Đăng"` thuần), điều kiện `'text="Đăng"' in xml_text` bị False.
   - Code bỏ qua nhận diện Preview, trôi xuống:
     ```python
     # Step 1: Tap "Next" / "Tiếp"
     logger.info("Looking for Next button...")
     next_tapped = adapter._tap_if_found(xml_text, text_contains="Tiếp")
     ...
     if not next_tapped:
         failure_code = "POST_NEXT_SELECTOR_EXHAUSTED"
     ```
   - Vì không có "Tiếp"/"Next", flow báo lỗi `POST_NEXT_SELECTOR_EXHAUSTED`.

## 3. Quy Tắc Sửa Code (Scope Lock & Defensive Handling)
1. **Bổ sung Resource ID `sp3` và `rzu` (Evidence thực tế Máy 34)**:
   - Trên TikTok build mới (như máy 34 - `m34_current_dump.xml`):
     - Tiêu đề Preview: `resource-id="com.ss.android.ugc.trill:id/rzu"`, text `"Xem trước"`.
     - Nút Đăng: `resource-id="com.ss.android.ugc.trill:id/sp3"`, text `"Đăng"`, class `android.widget.Button`, bounds `[564,1770][1032,1902]`.
     - Nút Sửa ảnh bìa: `resource-id="com.ss.android.ugc.trill:id/spb"`, text `"Sửa ảnh bìa"`.
   - Trong `state_machine.py`:
     - Bổ sung `"sp3"` vào tuple candidate post button resource IDs tại line ~12613 và line ~12797 (`("sh8", "shd", "sox", "soz", "sp7", "sp3", "rbp", "t66", "post_action", "post_button")`).
2. **Mở rộng nhận diện nút Đăng trên bề mặt "Xem trước"**:
   - Nhận diện bề mặt Preview: `"Xem trước" in xml_text or "rzu" in xml_text`.
   - Selector thử lần lượt: `resource_id="sp3"`, `text="Đăng"`, `content_desc="Đăng"`, `text="Post"`, `content_desc="Post"`.
3. **Chặn trôi sang Step 1 (Next button) nếu đã ở bề mặt Preview**:
   - Nếu XML chứa `"Xem trước"` hoặc tiêu đề Preview, tuyệt đối không fall-through sang tìm `"Tiếp"` / `"Next"`. Thay vào đó, áp dụng cơ chế xác định vị trí nút Đăng (pill button góc dưới bên phải) hoặc retry tap có chủ đích.

## 4. Pitfall Lập Trình ADB / ATX Session
- **Khai báo `AdbClient` trong `automation_core`**:
  - Signature của `AdbClient.__init__` là:
    ```python
    def __init__(self, adb_path: str = 'adb', serial: str | None = None, ...)
    ```
  - **LỖI NGUY HIỂM**: Gọi `AdbClient(serial)` truyền positional argument sẽ gán serial vào `adb_path`, dẫn tới:
    `ADBError: adb executable not found: ce031603b3158b0b02`.
  - **ĐÚNG**: Luôn luôn truyền bằng keyword argument:
    ```python
    adb = AdbClient(serial=device_serial)
    ```
