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
- **Tách riêng Helper Script Python (`scripts/resolve_avatar_pending_machines.py`)**:
  - **BẪY PowerShell Inline Python CLI Mangling**: Tránh dùng `python -c $pyScript` với here-string đa dòng chứa f-string / double quotes, vì bộ parser tham số của Windows CLI sẽ làm vỡ dấu ngoặc kép và văng lỗi `SyntaxError: '(' was never closed`. Tách hẳn thành script độc lập `scripts/resolve_avatar_pending_machines.py` và gọi qua `& python -B $resolverScript [string]$Tik`.
  - **BẪY Tên file `tik3.xlsx` (Chữ thường)**: File của Tik 3 là `tik3.xlsx` (chữ thường), khác với `Tik1.xlsx`, `Tik2.xlsx`, `Tik4.xlsx`... Helper script bắt buộc xử lý case-insensitivity hoặc mapping riêng `tik3.xlsx` cho Tik 3.
  - **Cơ chế tự động resolve khi không truyền `-ForceAvatarMachineList`**:
    1. Đọc file `Tik{Tik}.xlsx` tương ứng (`tik3.xlsx` đối với Tik 3).
    2. Lọc các dòng thỏa mãn đồng thời:
       - `Máy` là số nguyên hợp lệ (lưu ý: KHÔNG tự ý loại trừ Máy 38; Máy 38 vẫn là máy hợp lệ của farm khi có nick và chưa có Avatar).
       - `ID` hợp lệ (không rỗng, không phải `MISSING_ID` hoặc placeholder).
       - Cột `Avatar` chưa có giá trị `OK`.
    3. Nếu danh sách rỗng (tất cả máy đã có avatar): Báo cáo hoàn tất và dừng an toàn (`exit 0`), không tạo tiến trình con.
    4. Nếu có máy chưa up: Tự động gom danh sách máy thành chuỗi CSV (ví dụ `"1,2,5,9,14"`) và truyền vào tiến trình batch upload.
  - **Hỗ trợ switch `-WhatIf`**: Cho phép chạy preflight kiểm tra danh sách máy pending mà không khởi chạy batch thực tế.

- **CẢNH BÁO BẪY LOẠI TRỪ MÁY 38 TOÀN CỤC (User Correction 2026-09-06: "Tự nhiên bỏ qua 38. 38 nãy up cho tik4 chứ lq gì tik 5 6")**:
  Việc chừa Máy 38 trước đây chỉ áp dụng cho một batch riêng lẻ của Tik4 (khi máy đang giữ hiện trường/chờ xử lý). CẤM TUYỆT ĐỐI tự suy diễn thành quy tắc cấm toàn cục trên farm. Khi chạy Tik1..Tik3, Tik5, Tik6 hay các lượt avatar/feed chung, Máy 38 vẫn là thiết bị hợp lệ và chạy bình thường.

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

---

## 4. PITFALL: Bẫy suy đoán ảo trạng thái Avatar từ số Video Đã Đăng (`Video Đã Đăng >= 1 != Avatar OK`) (Hit 2026-09-08)
- **Triệu chứng & Sai lầm**:
  - Khi kiểm tra máy đã up avatar hay chưa, đọc thấy cột `Avatar = "OK"` trong Excel và kết luận toàn bộ dàn máy đã có avatar.
  - Khi user soi thiết bị thật (hoặc gửi ảnh screenshot profile), nick đã đăng nhiều video (như 4 video) nhưng avatar trên app TikTok vẫn là icon camera / placeholder mặc định.
- **Nguyên nhân gốc rễ**:
  - Script migration dữ liệu trước đây (`migrate_avatar_columns.py`) đã tự tiện suy đoán logic sai: `if Video Đã Đăng >= 1: ws.cell(r, avatar_col).value = "OK"`.
  - Thực tế các đợt upload video trước đó của Tik4 (Row 4) không tích hợp flow up avatar hoặc chạy bằng runner cũ không có avatar hook. Do đó nick đã đăng 4 video nhưng CHƯA TỪNG được tải avatar lên.
  - Việc gán khống `Avatar = "OK"` làm launcher `run_tiktok_upload_avatar.ps1` tự động bỏ qua các máy này vì tưởng đã hoàn tất, gây kẹt hiện trạng thiếu avatar toàn dải.
- **Kỹ thuật xác minh độc lập O(1) qua TikTok CDN**:
  - Khi nghi ngờ cột `Avatar` trong Excel bị nạp ảo, kiểm tra trực tiếp qua request HTTP GET `https://www.tiktok.com/@<username>` và bóc tách trường `avatarLarger`:
    + URL CDN chứa mã số `1594805258216454` hoặc domain placeholder `musically-maliva-obj` $\rightarrow$ **Avatar mặc định (CHƯA up)**.
    + URL CDN chứa tiền tố `tos-alisg-avt-...` $\rightarrow$ **Avatar thật của kênh (ĐÃ up)**.
- **Quy tắc nghiệm thu & bảo toàn dữ liệu**:
  1. **TUYỆT ĐỐI CẤM suy luận `Video Đã Đăng >= 1` $\rightarrow$ `Avatar = OK`**.
  2. Cột `Avatar` trên workbook con (`TikN.xlsx`) CHỈ được mang giá trị `OK` khi:
     - Có entry `VERIFIED_SUCCESS` trong durable ledger `avatar-ledger.jsonl`.
     - Có report run `AVATAR_SMOKE_SUCCESS` / `FORCED_REPLACED_VERIFIED`.
     - Hoặc đã được verify trực tiếp qua CDN/UI app.
  3. Mọi dòng chưa thỏa mãn điều kiện trên BẮT BUỘC để trống (`None`) để launcher tự động phát hiện và đưa vào danh sách chạy batch.

---

## 5. BẪY XUNG ĐỘT TIẾN TRÌNH & ĐIỀU PHỐI BATCH AVATAR AN TOÀN VỚI LỊCH CRON NUÔI ACC (2026-09-08)
- **Cơ chế hoạt động của launcher `run_tiktok_upload_avatar.ps1`**:
  - Launcher được thiết kế để thực thi NGAY LẬP TỨC (`immediate execution`), **HOÀN TOÀN KHÔNG TỰ CANH HOẶC CHỜ LỊCH CRON NUÔI ACC**.
  - Khi chạy, launcher kiểm tra lock thiết bị qua `machine_inventory.py --lock-root <CODEX_DEVICE_LOCK_DIR>`.
  - Nếu kích hoạt trong khi các ca nuôi acc (Ca 1: 06:00-10:00, Ca 2: 12:30-16:30, Ca 3: 19:00-23:00) đang chạy:
    + Toàn bộ máy đang bị cron nuôi acc giữ lock sẽ bị ghi nhận `SKIPPED_DEVICE_LOCKED` và bỏ qua.
    + Nếu bypass lock: hai tiến trình sẽ tranh chấp mở app TikTok, gây văng app, gãy phiên nuôi hoặc làm hỏng quy trình upload avatar.
- **Quy tắc điều phối & Giám sát bằng Watchdog**:
  1. **Khung giờ chạy an toàn nhất**:
     - Khoảng thời gian rảnh rỗi giữa các ca, đặc biệt là **Đêm muộn sau Ca 3 (`22:30 – 00:45`)**.
     - BẮT BUỘC kết thúc trước `01:00` sáng để không tranh chấp với chuỗi Reg tự động ban đêm (`night-chain-reg-pipeline`).
  2. **Điều kiện kích hoạt Watchdog (Idle Preflight Gate)**:
     - Tiến trình nuôi feed (`multi_machine_feed_session`, `run-feed-session.ps1`, `run_tiktok.py`, `hermes_cron_runner.py`) đã dừng 100% (xác minh qua `psutil`).
     - Toàn bộ `device-locks` liên quan đến `nuoi acc` trong `~/.codex/device-locks/` đã được nhả sạch về 0.
     - Sau khi thỏa mãn cả 2 điều kiện mới phát lệnh chạy PowerShell batch avatar cho các máy pending.


