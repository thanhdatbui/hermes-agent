# Avatar Status Tracking & Pending Batch Resolver Pattern

## 1. Vấn đề & Bối cảnh (2026-09-06)
- **Thiếu cơ chế ghi nhận Avatar trên Workbook**:
  Khác với video (có cột `Video Đã Đăng` làm cursor lũy tiến), các file `Tik1..Tik6.xlsx` trước đây không có cột trạng thái Avatar.
- **Hạn chế của Video #1 Hook**:
  Workflow đăng video (`_force_avatar_upload_allowed`) chỉ tự động kích hoạt flow up avatar ở lần đăng video đầu tiên (`int(video_number) == 1`). Khi nick đã đăng video 1 nhưng chưa có avatar (hoặc dàn nick mới Row 5/6 đang trong giai đoạn 10 ngày đầu chỉ lướt feed, 0 đăng video), avatar hook sẽ không tự kích hoạt.
- **Bất tiện khi chạy batch Avatar**:
  Launcher `run_tiktok_upload_avatar.ps1` trước đây bắt buộc phải truyền tay `-ForceAvatarMachineList "<máy1,máy2>"`. Khi muốn chạy up avatar cho toàn bộ một Row (ví dụ Row 5 hoặc Row 6), người vận hành không thể ra lệnh tự động chạy các máy còn thiếu nếu không tự soi từng máy.

---

## 2. Kiến trúc 3 tầng: Đánh dấu & Tự Động Lọc Máy Chưa Có Avatar

### Tầng 1: Cột `Avatar` trên các Workbook `Tik1..Tik6.xlsx`
- Bổ sung cột **`Avatar`** (alias trong `CANONICAL_HEADERS`: `avatar`, `avatar da up`, `avatar status`) vào header `TaiKhoan` trong `Tik1..Tik6.xlsx`.
- **Quy ước giá trị**:
  - `OK`: Nick trên máy đã được up avatar thành công và đã verify.
  - `None` (hoặc rỗng): Chưa up avatar.
  - `MISSING_ID`: Ô ID trống, chưa có nick để up avatar.
- **Atomic Workbook Update (`AccountSource.update_avatar_status`)**:
  Hàm cập nhật sử dụng `atomic_workbook_update` (kèm lock và backup), tự động dò tìm cột `Avatar` (hoặc tự động thêm header `Avatar` ở cột cuối nếu chưa có), đối soát đúng `self._row_index` và `device_id` của máy để gán `Avatar = "OK"`.

### Tầng 2: Durable Ledger JSONL (`avatar-ledger.jsonl`)
- Đường dẫn: `D:/CodexRuntime/tiktok-video/idempotency/avatar-ledger.jsonl`.
- Khi state machine đạt `self.context.avatar_status in ("FORCED_REPLACED_VERIFIED", "UPLOADED_VERIFIED")`:
  Ghi nhận ngay 1 record độc lập:
  ```json
  {
    "timestamp": "2026-09-06T18:40:34.210651",
    "machine": 36,
    "device_id": "ce10160ac8f1962305",
    "account": "jasomntqsso",
    "folder": 284,
    "tik": 4,
    "status": "VERIFIED_SUCCESS"
  }
  ```
- Phục vụ audit, chống up đè trùng lặp và làm nguồn fallback khi file Excel bị conflict/đang bận đồng bộ OneDrive.

### Tầng 3: Auto Pending Resolver trên Launcher `run_tiktok_upload_avatar.ps1`
- **Cơ chế tự động resolve khi không truyền `-ForceAvatarMachineList`**:
  1. Đọc file `Tik{Tik}.xlsx` tương ứng.
  2. Lọc các dòng thỏa mãn đồng thời:
     - `Máy` là số nguyên hợp lệ và khác `38` (bảo vệ bất biến an toàn: Máy 38 luôn loại trừ khỏi batch).
     - `ID` hợp lệ (không rỗng, không phải `MISSING_ID` hoặc placeholder).
     - Cột `Avatar` chưa có giá trị `OK`.
  3. Nếu danh sách rỗng (tất cả máy đã có avatar): Báo cáo hoàn tất và dừng an toàn (`exit 0`), không tạo tiến trình con.
  4. Nếu có máy chưa up: Tự động gom danh sách máy thành chuỗi CSV (ví dụ `"1,2,5,9,14"`) và truyền vào tiến trình batch upload.

---

## 3. Cách vận hành lệnh Up Avatar theo Row
- **Chạy tự động các máy chưa có avatar cho Row K**:
  ```powershell
  cd "D:\Taadaa\Tiktok-video"
  # Tự động lọc và chạy các máy thiếu avatar ở Row 5 (Tik5):
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_tiktok_upload_avatar.ps1" -Tik 5 -MaxParallel 2

  # Tự động lọc và chạy các máy thiếu avatar ở Row 6 (Tik6):
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_tiktok_upload_avatar.ps1" -Tik 6 -MaxParallel 2
  ```
- **Chạy chỉ định máy cụ thể (Force override)**:
  ```powershell
  # Vẫn hỗ trợ ghi đè danh sách máy khi cần up lại máy cụ thể:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "run_tiktok_upload_avatar.ps1" -Tik 4 -ForceAvatarMachineList "36" -MaxParallel 1
  ```
