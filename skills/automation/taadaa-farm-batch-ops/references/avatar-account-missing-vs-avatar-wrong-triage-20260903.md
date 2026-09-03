# Avatar Triage: ACCOUNT_MISSING vs Avatar Sai vs Multi-Tik Mapping (2026-09-03)

- Case 1 (Máy 76 - Row 3 `@ucloan7790`, Folder Video 603, video gốc 232): user báo "up ava sai".
  - Kết luận: avatar file KHÔNG sai — nick chưa login nên workflow dừng ở `ACCOUNT_SWITCHER`, chưa bao giờ tới bước up avatar.
- Case 2 (Máy 34 - Row 4 `@lethanh14375`, Folder Video 274, video gốc 268): user báo "acc này nữa" với ảnh profile 1 video, avatar camera mặc định.
  - Kết luận: Acc thuộc **Tik4.xlsx (Row 4)** (không phải Tik3). Đã đăng 1 video nhưng flow đăng video bình thường không gọi `ENSURE_AVATAR` (chuyển thẳng từ `UPDATE_WORKBOOK` sang `DELETE_REMOTE_MEDIA`). Avatar 512x512 JPEG trên đĩa đầy đủ cả 2 nơi; cần chạy bù bằng standalone launcher `run_tiktok_upload_avatar.ps1 -Tik 4 -ForceAvatarMachineList "34"`.

## Quy trình triage chuẩn (làm theo thứ tự)

1. **Tra cứu đối chiếu toàn bộ Tik1..Tik6.xlsx:**
   - Khi user gửi ảnh nick/máy mà không chỉ định rõ Tik/Row, đọc nhanh toàn bộ `D:\OneDrive\TaadaaData\kibe\Tik*.xlsx` (hoặc `D:\OneDrive\Tiktok\Tik*.xlsx`) để tìm đúng hàng theo `Máy` hoặc `ID / Username`.
   - Lấy: `Tik<N>`, `Máy`, `ID`, `Folder Video`, `video gốc`, `Video Đã Đăng`.
   - `Video Đã Đăng > 0` mà avatar vẫn là camera mặc định = do đợt post trước không kích hoạt avatar hoặc batch up avatar chỉ mới chạy trên Tik khác.

2. **Kiểm tra file avatar cả 2 nơi trên đĩa:**
   - `D:\video goc\<video gốc>\avatar.jpg`
   - `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - Chuẩn hợp lệ: file tồn tại, dung lượng 20-50KB, kích thước 512x512 JPEG RGB.
   - Nếu file avatar trên đĩa đã đúng chuẩn mà TikTok chưa có avatar -> Lỗi do chưa chạy standalone upload avatar, KHÔNG phải do tạo sai file avatar.

3. **Đọc log batch hoặc log run gần nhất của máy:**
   - Batch log: `D:\CodexRuntime\tiktok-video\batch-runs\<batch_id>\machine-<N>.out.log` (File là **UTF-16** — mở bằng `open(path,'rb').read().decode('utf-16')`).
   - Run log: `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<timestamp>\execution.log` và `report.json` (chỉ glob theo đúng serial máy `run_<serial>_*`, CẤM quét đĩa diện rộng).
   - Nếu log báo `ACCOUNT_MISSING`: nick chưa có trong switcher.
   - Nếu log kết thúc `SUCCESS` ở `UPDATE_WORKBOOK` mà không có bước `ENSURE_AVATAR`: do flow chạy ở chế độ post video thông thường.

4. **Xác minh hiện trường máy:**
   - `adb -s <serial> devices`: kiểm tra online.
   - `dumpsys window | grep -E "mCurrentFocus"`: kiểm tra app đang hiển thị.
   - `~/.codex/device-locks/machine_<N>.lock.json`: kiểm tra máy `NO-LOCK`.

5. **Khởi chạy standalone avatar upload cho máy mục tiêu:**
   - Cập nhật manifest `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json`:
     ```json
     {
       "schema_version": 1,
       "assignment_id": "avatar-retry-<timestamp>",
       "owner_id": "hermes-kibe-avatar",
       "resources": ["machine:<N>"],
       "reviewed_at": "<ISO timestamp>"
     }
     ```
   - Chạy lệnh standalone canonical:
     ```powershell
     echo 'RUN' | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" -Tik <N> -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json" -WorkerId hermes-kibe-avatar -ForceAvatarMachineList "<N>" -MaxParallel 40 -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
     ```

## Pitfall công cụ & An toàn farm

- `browser_vision` không phân tích được ảnh screencap local — gửi MEDIA path cho user xem trực tiếp thay vì cố phân tích qua vision tool.
- `computer_use capture mode=vision` trả về `0x0, 0 elements` trên môi trường này — không dùng để đọc ảnh farm.
- CẤM glob rộng `D:/CodexRuntime/tiktok-video/runs/run_*/report.json` (timeout 900s). Chỉ tìm theo prefix serial `run_<serial>_*` của máy cần triage.
