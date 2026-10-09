# USB Hub Micro-Drop Triage, Masked Serial Signature & ADB Retry Backoff

## 1. Hiện Tượng / Triệu Chứng (Symptoms)
- **Cụm lỗi Signature:** `focus-device-issue:Device serial 'device:<hash>' was not found in adb devices.`
- **Đặc điểm thời gian:** Nhiều máy văng cùng một giây hoặc vài giây ngắn ngủi (ví dụ 8 máy fail tại cùng timestamp `07:08:47`).
- **Thời lượng thực thi lỗi:** Thời gian từ lúc runner start đến lúc kết luận `config-error` chỉ kéo dài **100ms - 200ms**.
- **Hệ quả phân tích:**
  - `device:<hash>` thực chất là kết quả của hàm `mask_value(serial, prefix='device')` khi log lỗi ra JSONL/Summary, chứ không phải chuỗi ID bị nối prefix sai lệch.
  - Sau khi batch kết thúc, đa số máy (ví dụ 12/16 máy) đã tự động nhận diện lại trên `adb devices` và hoàn toàn ONLINE bình thường.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **USB Hub Bus Transient Reset / Micro-drop:**
   - Khi chạy song song nhiều worker (ví dụ trần 40 worker đồng loạt khởi chạy), tải dòng điện và bus USB qua các bộ chia (USB hub 10/20 port) có thể bị sụt áp nhẹ hoặc controller reset tạm thời trong tích tắc (~500ms - 1s).
2. **Preflight ADB Zero-Wait (Lỗi thiết kế vòng lặp retry):**
   - Vòng lặp kiểm tra `_validate_child_adb` cấu hình `ADB_ONLINE_ATTEMPTS = 2` nhưng gọi liên tục mà **không có `time.sleep`** ở giữa các lần gọi:
     ```python
     # ANTI-PATTERN: Retry tức thì không khoảng nghỉ
     for _attempt in range(1, ADB_ONLINE_ATTEMPTS + 1):
         devices = adb.list_devices()
         if serial in devices:
             return FlowResult(...)
         # Trôi ngay lập tức qua attempt 2 mà không chờ USB bus re-enumerate
     ```
   - Tổng thời gian 2 lần gọi chỉ tốn ~130ms, thiết bị chưa kịp re-enumerate trên bus USB thì runner đã vội vã đánh dấu `config-error` và dừng toàn bộ session của máy đó.

## 3. Quy Trình Chẩn Đoán Chuẩn Cho Coordinator (Diagnosis Workflow)
1. **Khảo sát O(1) ADB và đối chiếu Mapping:**
   - Không đoán mò hay viết script probe diện rộng. Lấy danh sách máy từ alert, tra `machine-map-80.txt` và so khớp tức thì với `adb devices`.
   - Phân loại rõ ràng:
     - Nhóm **Tự phục hồi (Online trở lại)**: Do micro-drop lúc kích hoạt batch.
     - Nhóm **Thực sự Offline (Hard-offline)**: Lỏng cáp, sụt nguồn hub hoặc thiết bị mất nguồn.
2. **Kiểm tra Timestamp trong Log:**
   - Đọc trực tiếp `run_manifest.json` và `log.jsonl` của batch lỗi.
   - Nếu nhiều máy fail tại cùng 1 giây (ví dụ 8 máy cùng timestamp) và start-to-end < 500ms -> Khẳng định 100% là **Micro-drop USB + Zero-wait Preflight**.

## 4. Giải Pháp Kỹ Thuật Chuẩn (Remediation Pattern)
1. **Thêm Backoff Sleep vào vòng lặp Retry ADB Preflight:**
   ```python
   # PROVEN FIX: Đệm thời gian chờ USB re-enumerate
   for _attempt in range(1, ADB_ONLINE_ATTEMPTS + 1):
       try:
           devices = adb.list_devices()
       except ADBError as exc:
           last_error = str(exc)
           continue
       if serial in devices:
           return FlowResult(ExitStatus.SUCCESS, "ADB device validated.", {"devices": devices})
       last_error = f"Device serial {mask_value(serial, prefix='device')!r} was not found in adb devices."
       if _attempt < ADB_ONLINE_ATTEMPTS:
           time.sleep(1.0)  # Chờ 1.0s để bus USB hoàn tất handshake
   ```
2. **Xử lý vật lý cho nhóm Hard-offline:**
   - Đối với các máy vẫn OFFLINE sau thời gian dài: yêu cầu cắm lại cổng USB / cấp lại nguồn hub cho đúng danh sách máy cụ thể.
