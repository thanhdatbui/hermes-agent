# Kibe venv-core Version Contract & Single-Nick Avatar/Hashtag Reconciliation (2026-10-10)

## 1. Bẫy Mismatch `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION` trên Kibe Farm
- **Hiện tượng:** Khi chạy `run_tiktok_upload_avatar.ps1` (hoặc wrapper gọi `run_tiktok_upload_batch.ps1`), nếu agent set biến môi trường:
  `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45`
  thì batch preflight lập tức dừng với ngoại lệ:
  `automation-core version mismatch: expected=0.4.45; actual=0.4.44; runtime=D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe`
- **Nguyên nhân sâu xa:**
  Trong môi trường `venv-core024\Lib\site-packages`, tồn tại cả hai thư mục dist-info:
  - `automation_core-0.4.44.dist-info`
  - `automation_core-0.4.45.dist-info`
  Khi `run_tiktok_upload_batch.ps1` thiết lập `PYTHONPATH=D:\Taadaa\Tiktok-video\scripts`, hàm `importlib.metadata.version('automation-core')` trong Python 3.11 quét và trả về `0.4.44`.
  Mã nguồn PowerShell của `run_tiktok_upload_batch.ps1` có logic:
  ```powershell
  $defaultAutomationCoreVersion = "0.4.44"
  $configuredAutomationCoreVersion = [string]$env:TIKTOK_VIDEO_AUTOMATION_CORE_VERSION
  if ([string]::IsNullOrWhiteSpace($configuredAutomationCoreVersion)) {
      $expectedAutomationCoreVersion = $defaultAutomationCoreVersion
  } else {
      $expectedAutomationCoreVersion = $configuredAutomationCoreVersion.Trim()
  }
  ```
  Nếu không set biến môi trường này, script mặc định mong đợi `0.4.44` — khớp 100% với `actual=0.4.44`.
- **Quy tắc điều phối:**
  - Trên **Kibe local**: **KHÔNG** ép gán `TIKTOK_VIDEO_AUTOMATION_CORE_VERSION=0.4.45` (để mặc định hoặc gán `0.4.44`).
  - Trên **Admin remote**: runner PowerShell cho phép bypass nếu `$env:USERNAME -eq 'Admin' -and $actualAutomationCoreVersion -eq "0.4.45"`.

---

## 2. Quy trình Chuẩn hoá Đơn Nick Toàn Diện từ Ảnh Screenshot Profile
Khi nhận ảnh chụp màn hình một tài khoản (ví dụ `@.thy.v5`):
1. **Định danh O(1):**
   - Tra SQLite `account_mapping` hoặc `avatar_replace_queue`: `@.thy.v5` $\to$ Máy 19, Tik 4, `Folder Video` = 148, `video gốc` = 259.
2. **Đối soát nội dung & Phát hiện lệch Niche:**
   - Folder đang thực tế đăng bài (`148`) chứa video nữ sinh THPT Lê Quý Đôn (`6.mp4`).
   - Nhưng workbook `Tik4.xlsx` lại ghi `Keyword: Ngoại ngữ`, `video gốc: 259`.
   - Avatar cũ trên nick lại cắt dính clip chăm sóc mẹ & bé sơ sinh có chữ đỏ.
3. **Trích xuất & Kiểm chứng Vision (Score $\ge 9.0/10$):**
   - Bóc tách frame cận cảnh (0.8s) từ `6.mp4`: nụ cười tươi, kính tròn, đồng phục học sinh.
   - Tính toán headroom và đường mắt (1/3 trên), xuất circular preview giả lập TikTok.
   - Gọi Vision API chấm điểm thẩm mỹ và bố cục đạt 9.2/10.
4. **Đồng bộ hóa 4 tầng dữ liệu:**
   - **Tầng đĩa:** Ghi nguyên tử `avatar.jpg` vào cả `D:/TIKTOK-videonuoinick/148/` và `D:/video goc/148/`.
   - **Tầng Workbook (`Tik4.xlsx`):** Khóa `video gốc = 148`, đổi `Keyword Video = 'Học sinh'`, cập nhật Hashtag Pool học đường viral, set `Avatar = 'PENDING'`.
   - **Tầng Niche Database (`state.db`):** Cập nhật `niche = 'hocsinh'` cho folder 148 trên cả ổ C: và D:.
   - **Tầng Queue SQLite (`tiktok_tracker.db`):** Cập nhật `video_goc = '148'`, `status = 'PENDING'`.
5. **Kích hoạt Runner & Nghiệm thu 3 Lớp:**
   - Khởi chạy standalone runner: `run_tiktok_upload_avatar.ps1 -Tik 4 -ForceAvatarMachineList "19" -MaxParallel 1`.
   - Đối soát `summary.csv` (`ExitCode=0, Status=THÀNH CÔNG, Verified=True`).
   - Đọc `report.json` (`status=AVATAR_SMOKE_SUCCESS, avatar_status=FORCED_REPLACED_VERIFIED`).
   - Soi mắt ảnh Gate 6 qua Vision: `avatar-save-surface-guard.png` (màn hình Crop) và `avatar-uploaded-confirmed.png` (màn hình Sửa hồ sơ).
   - Khi cả 3 lớp pass: `UPDATE avatar_replace_queue SET status='DONE'` và cập nhật cột `Avatar = 'OK'` trong `Tik4.xlsx`.
