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

## 3. Quy chuẩn sửa chữa (Fix Pattern O(1)) & Cảnh báo False Positive
- Chuyển từ exact equality sang substring / keyword matching an toàn:
  ```python
  folder_idx = next(
      (i for i, h in enumerate(headers) if any(k in h for k in ("folder video", "video folder", "render dich"))),
      None
  )
  ```
- **🛑 CẢNH BÁO REVIEWER (PITFALL - KHÔNG DÙNG TỪ KHÓA "tik"):**
  * TUYỆT ĐỐI KHÔNG đưa từ khóa `"tik"` vào danh sách `any(k in h for k in ...)` khi so khớp chuỗi con (`substring match`).
  * Lý do: Các file Excel quản lý farm có các cột như `"TikTok ID"`, `"Keyword Video"` đều chứa chuỗi con `"tik"`. Nếu workbook thiếu cột Folder Video hoặc cột bị dịch chuyển, bộ lọc sẽ khớp nhầm vào `"TikTok ID"` hoặc `"Keyword Video"`, dẫn đến truyền nhầm tham số folder video và gây lỗi nghiêm trọng khi tìm đường dẫn media.
- **Bổ sung Telemetry Logging:**
  * Thêm warning log tường minh khi không tìm thấy cột folder để telemetry quan sát được:
    ```python
    if folder_idx is None:
        logger.warning("[UPLOAD_HOOK] Workbook %s: no folder video column found in headers %r", workbook_path.name, headers)
    ```
- **Kỷ luật Closeout Gate khi commit nhiều file (Scope Invariant):**
  * Script `closeout_gate.py` so sánh exact committed scope với `--files`.
  * Nếu commit chứa nhiều file hơn danh sách `--files` (ví dụ: commit cả `benign_popup_registry.py` kèm theo), gate sẽ fail với lỗi `refusing partial committed scope`.
  * Bắt buộc: Hoặc truyền đủ toàn bộ các file đã commit vào `--files`, hoặc chỉ commit đúng các file đã được chỉ định trong Scope Lock.
- Đảm bảo tương thích ngược 100% với cả schema cũ (`Folder Video`, `video folder`) lẫn schema mới (`Folder Video (Render Dich)`).

---

## 4. Kiểm chứng focused & Xác minh thực tế trên Farm
- Tạo unit test mock/in-memory openpyxl với 2 bảng workbook có cả header cũ và header mới chứa chú thích ngoặc đơn.
- **Tiêu chuẩn test suite Closeout Gate:**
  * Bắt buộc có test case chống False Positive: Sheet có các cột `"TikTok ID"`, `"Keyword Video"` nhưng không có cột Folder Video -> xác nhận `res["folder_video"] == ""` chứ không bị khớp nhầm.
  * Bắt buộc có test case xử lý ngoại lệ: Sheet thiếu cột "Máy", hoặc truy vấn machine không tồn tại -> trả về `None`.
  * Trong file test độc lập, chèn `sys.path.insert(0, str(REPO_ROOT / "python_runner"))` và hỗ trợ import linh hoạt để `pytest` chạy độc lập từ bất kỳ workdir nào mà không bị ImportError.
- Xác minh `read_machine_row_from_tik_workbook` trích xuất chính xác `folder_video` và `account_id` trên cả hai định dạng.
- **Xác minh trực tiếp O(1) trên 8 file workbook thực tế:**
  * Chạy probe đọc `read_machine_row_from_tik_workbook(resolve_tik_workbook(r'D:/OneDrive/TaadaaData/kibe', tik), 1)` cho `tik` từ 1 đến 8.
  * Toàn bộ 8 file `Tik1.xlsx` đến `Tik8.xlsx` đều phải trả về `folder_video` hợp lệ (ví dụ: `Tik1` trả về `'1'`, `Tik7` trả về `'7'`) thay vì chuỗi rỗng `''`.

