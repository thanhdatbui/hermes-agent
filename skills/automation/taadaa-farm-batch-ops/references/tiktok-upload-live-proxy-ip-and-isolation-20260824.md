# TikTok Video Upload Strict Live Proxy IP Preflight & Device Lock Rules

## 1. Vấn đề Live Proxy IP (Bắt buộc kiểm tra Internet qua ViChanger)
- **Rủi ro:** Khi app ViChanger trên Android box mở và tạo card mạng ảo `tun0`, nhưng proxy phía sau bị chết, hết băng thông hoặc đứt kết nối, kiểm tra thuần túy `tun_up` vẫn trả về `True`. Nếu script mở app TikTok lúc này, thiết bị sẽ dùng IP gốc hoặc bị lỗi mạng, dẫn đến mất trust hoặc checkpoint tài khoản.
- **Quy tắc bắt buộc:**
  - Repo `tiktok-video` tại bước `_handle_resolve_device` (`scripts/tiktok_workflow/state_machine.py`) bắt buộc gọi:
    ```python
    require_android_vpn(
        AdbClient(**adb_kwargs),
        required=True,
        verify_live_ip=True,
    )
    ```
  - `verify_live_ip=True` sẽ broadcast `vn.vichanger.app.GET_IP` đến ViChanger. Nếu không nhận được IP proxy thật (sau 3 lần thử), preflight lập tức chặn đứng phiên với mã `VPN_REQUIRED_NOT_CONNECTED` trước khi mở TikTok.

## 2. Cách ly giữa Batch Upload thủ công và Cron Nuôi Feed
- **Hiện tượng xung đột:** Khi kích hoạt batch upload thủ công (`run_tiktok_upload_batch.ps1`), nếu cron feed (`phase9-runner-tiktok-feed`) đến chu kỳ tick 15 phút, cả 2 tiến trình sẽ cùng điều khiển một thiết bị. Upload đang ở màn hình CapCut/Upload video, trong khi feed nhảy vào tìm Profile -> Gây lỗi `navigation target profile not found in XML` và hỏng cả 2 phiên.
- **Quy tắc vận hành:**
  1. Khi chạy batch upload thủ công: Tạm dừng cron feed (`cronjob pause`) HOẶC tạo device lock độc quyền (`~/.codex/device-locks/machine_<N>.lock.json` với `status: "running"`, `user_authorized: true`, `project: "tiktok-video"`, TTL 2h).
  2. Khi upload hoàn tất: Giải phóng lock và bật lại cron feed (`cronjob resume`).

## 3. Entrypoint chuẩn của `tiktok-video`
- BẮT BUỘC gọi qua package con `scripts.tiktok_workflow`:
  ```powershell
  python -m scripts.tiktok_workflow --config <config.yaml> --workflow-workbook <TikN.xlsx> --machine <ID> --no-dry-run
  ```
- Không gọi bare `tiktok_workflow` từ root repo vì sẽ ném `ModuleNotFoundError: No module named 'tiktok_workflow'`.
