# Upload Hook: Tik Workbook Mapping & Config File Requirement

## Bối cảnh & Quy tắc Vận Hành
Khi kết thúc phiên lướt feed cuối cùng của một ca (Phiên 3/3), `multi_machine_feed_session.py` tự động kích hoạt `_run_upload_hook` để đăng video lên TikTok:
- **Nguyên tắc ánh xạ 1-1:** Ca nuôi chạy Row nào thì tự động đăng theo file workbook Tik tương ứng:
  - Account Row 1 $\rightarrow$ `Tik1.xlsx` (Folder 1, 9, 17, 25... theo công thức $(m-1) \times 8 + 1$)
  - Account Row 2 $\rightarrow$ `Tik2.xlsx` (Folder 2, 10, 18, 26... theo công thức $(m-1) \times 8 + 2$)
  - Account Row 3 $\rightarrow$ `tik3.xlsx` (Folder 3, 11, 19, 27... theo công thức $(m-1) \times 8 + 3$)
  - Account Row 4 $\rightarrow$ `Tik4.xlsx` (Folder 4, 12, 20, 28... theo công thức $(m-1) \times 8 + 4$)

## Các Pitfall Kỹ Thuật Quan Trọng

### 1. File cấu hình `config.example.yaml` bắt buộc trong repo `Tiktok-video`
- Subprocess upload gọi:
  ```bash
  python -m scripts.tiktok_workflow --config <config_file> --workflow-workbook <workbook_path> --machine <m> --no-dry-run
  ```
- Script tìm `config-machine-<m>.yaml` trong `D:\Taadaa\Tiktok-video`. Nếu không tìm thấy cấu hình riêng từng máy, nó **fallback về `config.example.yaml`**.
- **Sự cố:** Nếu trong `D:\Taadaa\Tiktok-video` thiếu file `config.example.yaml`, CLI của `tiktok_workflow` văng lỗi ngay:
  ```text
  Config error: Config file not found: D:\Taadaa\Tiktok-video\config.example.yaml
  ```
  dẫn đến toàn bộ lượt upload của 80 máy đều trả về `status: failed`, `reason: upload_subprocess_nonzero` và không có video nào được đẩy lên thiết bị.
- **Khắc phục:** Luôn duy trì file `D:\Taadaa\Tiktok-video\config.example.yaml` trỏ đúng `media_source_root: D:\TIKTOK-videonuoinick`, `runtime_root: D:\CodexRuntime\tiktok-video`, `workflow_workbook` và `adb_path`.

### 2. Cấu trúc Cột trong Tik Workbook (`Tik1..Tik4.xlsx`)
- Header chuẩn: `Máy` (Col 1), `device ID` (Col 2), `ID` (Col 3), `Folder Video` (Col 4), `video gốc` (Col 5), `Keyword Video` (Col 6), `Hashtag Pool` (Col 7), `Video Đã Đăng` (Col 8).
- `read_machine_row_from_tik_workbook()` đọc:
  - `account_id`: từ cột `ID` (Col 3)
  - `folder_video`: từ cột `Folder Video` (Col 4)
  - `posted_count`: từ cột `Video Đã Đăng` (Col 8)
- Video kế tiếp cần upload: `media_source_root / folder_video / f"{posted_count + 1}.mp4"`.

### 3. Phân biệt Alert Runtime vs Config Error
- Khi máy bị lỗi tiền kiểm tra `config-error` (như sai tham số `--max-swipes`, thiếu file cấu hình), hệ thống ngắt ngay trước khi mở thiết bị. Do đó không kích hoạt chụp ảnh banner đỏ gửi vào nhóm **Farm Alerts** (vốn chỉ kích hoạt trong vòng lặp thiết bị thật).
