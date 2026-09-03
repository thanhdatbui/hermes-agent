# Quy trình Tạo Workbook Tik4, Render Random và Fix Upload Hook Cuối Ca (2026-08-19)

## 1. Quy tắc Tạo Workbook Tik4 (`Tik4.xlsx`)
- **Nguồn tài khoản**: Slot 4 trong `taikhoan_dat_v2_updated .xlsx` (dòng thứ 4 của mỗi máy).
- **Vị trí lưu**: `D:\OneDrive\TaadaaData\kibe\Tik4.xlsx` (mirror `D:\OneDrive\Tiktok\Tik4.xlsx`).
- **Mapping cột**:
  - `Máy`: 1..80
  - `device ID`: Lấy từ slot 4 của máy trong REG.
  - `ID`: Lấy từ slot 4 (nếu None -> `MISSING_ID`, có -> `OK`).
  - `Folder Video` (Output): `(máy - 1) * 8 + 4` -> `4, 12, 20, 28, ..., 636`.
  - `video gốc` (Source): `240 + máy` -> `241..320`.
  - `Keyword Video` & `Hashtag Pool`: Tra cứu slug từ `folders` trong DB (`state-real-1-tiktok-final.db` hoặc `state.db`) -> map sang label tiếng Việt qua `niches_pool.txt` -> generate pool hashtag chuẩn niche.

## 2. Render Random Tik4 (`run_tik4_random_render.ps1`)
- **Launcher**: `run_tik4_random_render.ps1`
- **Slot**: `--slot 3` (0-based: Tik1=0, Tik2=1, Tik3=2, Tik4=3).
- **Parallel**: `--parallel 1` (chạy 1 worker để giữ CPU an toàn).
- **Min/Target videos**: `min_videos=30`, `max_videos=45`.
- **Output**: `D:\TIKTOK-videonuoinick\<Folder Video>`.
- **Watchdog cron**: `tik4_render_watchdog.py` chạy định kỳ 5 phút (`*/5 * * * *`), tự động báo cáo Telegram mỗi khi xong thêm 10 folder hoặc hoàn tất 80/80.

## 3. Khắc phục Upload Hook Phiên Cuối Ca Nuôi Acc
- **Nguyên nhân cũ**: `from flows.upload_preflight import ...` trong `multi_machine_feed_session.py` bị `ModuleNotFoundError` khi chạy qua `python_runner.run_tiktok`.
- **Fix chuẩn**:
  - Dual import fallback: `from python_runner.flows.upload_preflight import ...` rồi fallback `from flows.upload_preflight import ...`.
  - Workbook read retry: Thêm retry loop (3 lần, delay 1.5s) để chống tranh chấp file lock với OneDrive sync engine.
  - Case-insensitive verify: Kiểm tra kết quả `tiktok_workflow` không phân biệt hoa thường (`post verification passed`, `upload video success`, `upload completed`).
  - Diagnostic: Ghi nhận `stderr_tail` vào `upload_result.json` và log.

## 4. Tải Kho Video Gốc 480 Folders
- **Worker Policy**: `--parallel 16` kết hợp xoay 38 cổng proxy di động (`PROXYgandienthoai.xlsx`).
- **RAM / Whisper**: Mô hình Whisper đã được serialize qua 1 Global Thread Lock (`436066f`) nên 16 workers chạy song song an toàn, không bị leak heap/RAM ảo.
