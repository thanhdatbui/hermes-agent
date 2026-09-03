# Chained Cron Pipeline Debugging: Gmail -> TikTok

## 1. Cơ chế hoạt động của chuỗi đêm `night-chain-reg-gmail-tiktok`
- Script điều phối: `D:\Taadaa\Tiktok_Reg\scripts\run_night_chain_pipeline.py`.
- **Phase 1: Reg Gmail** qua PowerShell canonical launcher `D:\Taadaa\register gmail\run_all.ps1`.
- **Phase 2: Reg TikTok** qua `D:\Taadaa\Tiktok_Reg\_run_all_targets.py`.

## 2. Các điểm kiểm tra khi batch fail
1. **Lỗi `[BLOCKED][PRE_GMAIL][APP_STARTUP]`:**
   - App Gmail không thể lên foreground hoặc không capture được UI hierarchy trong thời gian timeout preflight.
2. **Lỗi `VPN_PREFLIGHT_BLOCKED`:**
   - App ViChanger broadcast `GET_IP` thất bại 3 lần -> Proxy dead/unreachable. Hệ thống fail-closed chặn máy ngay lập tức để bảo vệ farm.
3. **Lỗi `UI_XML_TIMEOUT` / `atx-exhausted`:**
   - Mất kết nối ADB tới thiết bị hoặc atx-agent bị treo không thể dump XML cây giao diện.
4. **Lưu kết quả & Tracking:**
   - Kết quả thành công được ghi tạm ra các file `tracking_result_sttXX_*.json` trong thư mục batch artifacts runtime (`D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\...`).
   - Pass để trống khi tài khoản đi qua flow OTP không yêu cầu mật khẩu.
5. **Cơ chế thoát Exit Code 0 & Delivery Telegram:**
   - `run_night_chain_pipeline.py` và wrapper launcher phải kết thúc với `return 0` sau khi in báo cáo ra `stdout`.
   - Nếu trả về `return 1`, Hermes `no_agent` cron scheduler sẽ chặn không gửi stdout và phát cảnh báo nhầm `provider timeout...`. Toàn bộ log debug phải đi qua `sys.stderr`.
