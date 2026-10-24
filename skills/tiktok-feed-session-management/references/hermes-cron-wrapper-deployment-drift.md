# Hermes Cron Wrapper Deployment Drift & Dual-Repo Sync Contract

## Bối cảnh Kiến trúc
Hệ thống nuôi tài khoản TikTok Phone Farm sử dụng mô hình 2 tầng repo:
1. **Source Repo (`D:/Taadaa/tiktok-luot nuoi acc`)**: Nơi phát triển logic nghiệp vụ nuôi, chọn tài khoản (`python_runner/`), và các template wrapper cron (`scripts/hermes_cron/`).
2. **Deploy / Runtime Repo (`D:/Taadaa/Hermes/deploy/hermes-home/scripts`)**: Nơi lưu trữ các script thực thi được cấu hình trong `cron/jobs.json`.
3. **Hermes Runtime (`%LOCALAPPDATA%\hermes\scripts`)**: Thư mục thực thi trực tiếp của daemon Hermes cron trên máy tính host Kibe.

## Cơ chế Đồng bộ Runtime
- Hermes cron thực thi các job không có absolute path bằng cách tìm file trong `%LOCALAPPDATA%\hermes\scripts\<script_name>`.
- Job `cron-sync-watchdog` (chạy mỗi 15 phút) thực hiện copy 2 chiều giữa `D:\Taadaa\Hermes\deploy\hermes-home\scripts` và `%LOCALAPPDATA%\hermes\scripts`.
- **LỖ HỔNG (Drift Gap)**: `cron-sync-watchdog` KHÔNG tự động đọc từ `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/`.

## Triệu chứng Khi Gặp Sự Cố (Symptom)
- Code mới (như Dynamic Shift-Pool Row 0, Dynamic 3-tier Selection) đã test và commit đầy đủ trên `tiktok-luot nuoi acc`.
- Nhưng đến giờ chạy ca trong ngày, Farm vẫn chạy theo logic cũ (ví dụ: vẫn chạy Row cố định 2, 4, 6 cũ thay vì Dynamic Pool Row 0).
- Báo cáo Telegram watchdog không hiển thị telemetry mới hoặc hiển thị định dạng cũ.

## Root Cause & Anti-Pattern
- **Anti-Pattern**: Commit xong tại source repo (`tiktok-luot nuoi acc`) rồi báo hoàn thành mà không deploy ra tầng runtime.
- **Biến môi trường lệch**: Bản template trên deploy repo dùng `os.environ.get("TAADAA_DYNAMIC_SHIFT_POOLS", "")` (mặc định False), trong khi bản mới trên source repo dùng `use_dynamic = os.environ.get("USE_DYNAMIC_FEED", "1") == "1"` (mặc định True). Do chưa deploy, runtime chạy bản cũ và rơi vào nhánh cố định.

## Quy trình Chuẩn Bắt Buộc (Mandatory Sync SOP)
Mỗi khi chỉnh sửa bất kỳ file nào trong `D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/`:
1. **Kiểm tra Diff giữa Source và Deploy**:
   ```bash
   diff -u "D:/Taadaa/Hermes/deploy/hermes-home/scripts/<file>" "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_cron/<file>"
   ```
2. **Đồng bộ sang Deploy Repo**:
   Copy đè file mới từ `scripts/hermes_cron/` sang `D:/Taadaa/Hermes/deploy/hermes-home/scripts/`.
3. **Thực thi Deploy Wrapper Runtime**:
   Chạy script:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\deploy_hermes_cron_wrappers.ps1"
   ```
   Script này sẽ tính SHA-256 và byte-copy trực tiếp vào `%LOCALAPPDATA%\hermes\scripts\`, loại bỏ hoàn toàn độ trễ 15 phút của `cron_sync_watchdog`.
4. **Hậu kiểm**:
   Xác nhận SHA-256 của file tại `%LOCALAPPDATA%\hermes\scripts\<file>` khớp 100% với file tại source repo.
