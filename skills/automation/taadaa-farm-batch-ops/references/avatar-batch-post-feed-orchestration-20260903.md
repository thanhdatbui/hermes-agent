# Avatar Batch Post-Feed Orchestration (2026-09-03)

## 1. Yêu cầu & Bối cảnh
Khi user yêu cầu: *"sau khi cron nuôi ca tối nay (hoặc ca N) kết thúc, chạy batch upload ava cho các acc ca đó luôn"*:
- Không được chạy đè batch upload trong khi phiên nuôi đang diễn ra (tránh xung đột UI, Focus loss, mở nhầm camera và kích hoạt device-lock).
- Bắt buộc kiểm tra và chuẩn bị dữ liệu (avatar đĩa 2 bên, assignment-manifest) TRƯỚC khi phiên nuôi kết thúc để khi vừa dứt điểm là kích hoạt ngay lập tức.

## 2. Các bước chuẩn bị dữ liệu (Pre-run Verification)
1. **Kiểm tra File Avatar trên Đĩa 2 Bên:**
   - Đối soát toàn bộ danh sách máy có tài khoản hợp lệ trong `TikN.xlsx` (Tik1 cho Ca 1, Tik3 cho Ca 2, Tik5 cho Ca 3 hoặc theo Row tương ứng).
   - Đảm bảo `avatar.jpg` tồn tại ở cả 2 thư mục:
     - Nguồn gốc: `D:\video goc\<video gốc>\avatar.jpg`
     - Nguồn render: `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - Nếu thiếu bên nào, trích xuất frame đầu/tạo từ video nguồn và đồng bộ sang cả 2 bên trước khi chạy.
2. **Đồng bộ Assignment Manifest:**
   - Cập nhật `D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json`:
     ```json
     {
       "schema_version": 1,
       "assignment_id": "avatar-tikN-all-<timestamp>",
       "owner_id": "hermes-kibe-avatar",
       "resources": ["machine:1", "machine:2", ...],
       "reviewed_at": "<ISO_TIMESTAMP>"
     }
     ```

## 3. Cơ chế Chờ & Kích hoạt Tự động (Feed Idle Detection)
- Giám sát tiến trình feed runner qua `is_feed_runner_active()`:
  - Quét danh sách process hệ thống: `multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`.
  - Thiết lập điều kiện idle liên tiếp (streak >= 3 checks cách nhau 15s) để chắc chắn không còn worker hay nhịp vét nào đang hoạt động.
- Kích hoạt canonical launcher:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1" `
    -Tik <N> `
    -AssignmentManifest "D:\CodexRuntime\tiktok-video\assignment-manifest-avatar.json" `
    -WorkerId hermes-kibe-avatar `
    -ForceAvatarMachineList "<danh sách máy>" `
    -MaxParallel 40 `
    -HostConfigPath "D:\Taadaa\machine-config\kibe.yaml"
  ```
- Khởi chạy dưới dạng background process với `notify_on_complete=True` và tổng kết báo cáo định dạng chuẩn:
  • **Tổng máy:** <Số lượng>
  • **Success (<Số lượng>):** <Danh sách máy>
  • **Fail (<Số lượng>):** <Danh sách máy kèm mã lỗi nếu có>

## 4. Quy chuẩn Watcher Ca cuối ngày (End-of-Day Row 5 & Row 6 Watchdog)
- **Ánh xạ Ca 3 cuối ngày:**
  - **Ngày Lẻ (Lane B):** Ca 3 chạy **Row 5** (`Tik5.xlsx`).
  - **Ngày Chẵn (Lane A):** Ca 3 chạy **Row 6** (`Tik6.xlsx`).
  - Khung giờ Ca 3 Phiên 3: ~21:45 - 23:59.
- **Điều kiện kích hoạt:**
  - Chỉ kích hoạt sau 22:30 khi feed runner của phiên 3 đã dừng hoàn toàn (`is_feed_runner_active() == False`).
  - Kết thúc trước 00:30 để cách ly an toàn với pipeline Reg ban đêm (`night-chain-reg-pipeline` lúc 01:00).

## 5. Idempotency Ledger ("Mỗi row nick 1 lần duy nhất")
- **File ledger theo dõi vĩnh viễn:** `D:\Taadaa\runtime\kibe\cron-state\avatar_upload_history.json`.
- **Cấu trúc lưu:**
  ```json
  {
    "<machine>_<row>": {
      "machine": 10,
      "row": 5,
      "account_id": "username_tiktok",
      "status": "success",
      "updated_at": "2026-09-06 23:40:15"
    }
  }
  ```
- **Lọc trước khi dispatch:**
  - Watchdog đọc danh sách máy của Row hôm đó (Row 5 hoặc Row 6), đối soát với ledger và CHỈ bốc các máy chưa có trạng thái `success` đưa vào `-ForceAvatarMachineList`.
  - Nếu toàn bộ nick của Row đã hoàn tất avatar -> Watchdog im lặng, không khởi chạy batch thừa.
