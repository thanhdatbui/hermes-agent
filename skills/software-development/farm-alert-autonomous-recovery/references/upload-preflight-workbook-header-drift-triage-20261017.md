# TikTok Upload Preflight Workbook Header Drift Protocol (2026-10-17)

## 1. Hiện tượng & Triệu chứng lỗi (Symptoms)
- Cảnh báo cronjob `daily-stale-upload-accounts-watchdog` ghi nhận hàng loạt máy Farm Kibe đang online bình thường nhưng bị gắn nhãn stale / kẹt không đăng clip (> 7 ngày hoặc > 14 ngày).
- Khi kiểm tra báo cáo thực thi `upload_result.json` tại `D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/<session>/machines/machine_<M>/<session>/upload_result.json`:
  ```json
  {
    "machine": 1,
    "row": 7,
    "status": "skipped",
    "reason": "missing_video_folder",
    "workbook": "Tik7.xlsx"
  }
  ```
- Toàn bộ farm bị skip upload hàng loạt dù thư mục video MP4 đã render đầy đủ và file Excel `Tik*.xlsx` có số folder hợp lệ.

---

## 2. Nguyên nhân cốt lõi (Root Cause)
- File logic: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/upload_preflight.py` trong hàm `read_machine_row_from_tik_workbook`:
  ```python
  folder_idx = next((i for i, h in enumerate(headers) if h in ("folder video", "video folder", "tik")), None)
  ```
- Kiểm tra exact match với tuple `("folder video", "video folder", "tik")`.
- Tuy nhiên, trong thực tế toàn bộ file Excel quản lý (`Tik1.xlsx` đến `Tik8.xlsx`) đã được chuẩn hóa lại header có chú thích trong ngoặc đơn:
  `'Folder Video (Render Dich)'` (chuyển lower thành `'folder video (render dich)'`).
- Do so sánh chính xác tuyệt đối, `folder_idx` trả về `None`, dẫn đến `folder_video = ""` và kích hoạt fail-closed skip toàn bộ với reason `missing_video_folder`.

---

## 3. Quy chuẩn sửa chữa (Fix Pattern O(1))
- Chuyển từ exact equality sang substring / keyword matching an toàn:
  ```python
  folder_idx = next(
      (i for i, h in enumerate(headers) if any(k in h for k in ("folder video", "video folder", "render dich", "tik"))),
      None
  )
  ```
- Đảm bảo tương thích ngược 100% với cả schema cũ (`Folder Video`, `video folder`) lẫn schema mới (`Folder Video (Render Dich)`).

---

## 4. Kiểm chứng focused
- Tạo unit test mock/in-memory openpyxl với 2 bảng workbook có cả header cũ và header mới chứa chú thích ngoặc đơn.
- Xác minh `read_machine_row_from_tik_workbook` trích xuất chính xác `folder_video` và `account_id` trên cả hai định dạng.
