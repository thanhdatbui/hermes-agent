# Quy Chuẩn Khung Giờ và Logic Tổng Hợp Báo Cáo Feed Session Watchdog (`feed_session_watchdog.py`)

## 1. Khung giờ Session Windows (`SESSION_WINDOWS`)
Lịch chạy runner thực tế phân bổ các slot/block với jitter thời gian. Khung giờ trong Watchdog phải bao phủ liên tục, không lọt khe giữa các phiên để tránh thất lạc run folder:

* **Ca 1 (Sáng)**:
  * **Phiên 1/3**: `06:00` - `07:30`
  * **Phiên 2/3**: `07:30` - `09:00`
  * **Phiên 3/3 (Đăng video)**: `09:00` - `12:00` *(BẮT BUỘC từ 09:00 để gom đầy đủ các đợt runner dispatch sớm ~09:15–09:30)*
* **Ca 2 (Chiều)**:
  * **Phiên 1/3**: `12:00` - `13:40`
  * **Phiên 2/3**: `13:40` - `15:15`
  * **Phiên 3/3 (Đăng video)**: `15:15` - `18:30`
* **Ca 3 (Tối)**:
  * **Phiên 1/3**: `18:30` - `20:15`
  * **Phiên 2/3**: `20:15` - `21:45`
  * **Phiên 3/3 (Đăng video)**: `21:45` - `23:59`

---

## 2. Logic Merge & Phân Loại Upload Video (Phiên 3)
1. **Bảo toàn trạng thái Thành công qua các đợt chạy lại (Retries/Multi-run)**:
   * Khi Phiên 3 chạy nhiều đợt (ví dụ: đợt chính lúc 09:16 và đợt vớt lúc 10:30), các máy đã đăng video thành công ở đợt trước sẽ trả về `status: skipped` kèm `reason: already_uploaded_in_shift`.
   * `merge_upload_result(prev, new)` BẮT BUỘC giữ lại kết quả `success` của đợt trước, không để `skipped` đè mất `success`.
   * Đối soát ground truth với ledger `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`: Nếu máy ghi nhận `status: success` trong ca/shift ngày hôm đó -> Phân loại vào nhóm **Success**.
2. **Bảo toàn chi tiết lỗi**:
   * Nếu đợt trước máy bị `failed` kèm lỗi chi tiết (vd: `upload_subprocess_nonzero`), và đợt sau bị skip -> Giữ lại kết quả `failed` để report chính xác vào **Lỗi script/xác minh**.
3. **Phòng vệ NoneType (`Null-Safe`)**:
   * `merge_upload_result(prev, new)` phải kiểm tra an toàn `if not prev: return new` và `if not new: return prev`.

---

## 3. Tối Ưu Quét Đĩa Hiệu Năng Cao (Tránh Timeout I/O)
* **Tuyệt đối không dùng `glob.glob(recursive=True)` quét lặp lại nhiều lần** trên cây thư mục `live/<date>/<run>/machines/`.
* **Sử dụng `parse_run_all(run_dir)` với `os.scandir` trong 1 lượt duy nhất**: Đọc đồng thời `summary.txt`, `follow_result.json`, `upload_result.json` giúp giảm thời gian xử lý từ >900s xuống ~1-2s.
