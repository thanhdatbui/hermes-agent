# Canary Verification & Account Switcher Observation (2026-09-11)

## Lệnh chạy Canary với Row & RecoveryTestSwipes
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <Row> -RecoveryTestSwipes <Swipes> -SkipAccountWorkbookSync -Run
```

## Theo dõi và phân tích Log thật (log.jsonl)
- Thư mục artifact mới nhất nằm tại: `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\<TIMESTAMP>\machines\machine_<N>\<TIMESTAMP>\log.jsonl`
- Phân biệt 2 tình huống khi đổi nick:
  1. **Profile switcher sheet (`profile_preflight_switch` -> `tap_expected_account`)**:
     - Khi nick mục tiêu đã có trong danh sách tài khoản đã đăng nhập trên ứng dụng TikTok.
     - Script sẽ tap nút switch account và chọn nick tương ứng (`action: tap_expected_account`).
     - **Không kích hoạt luồng `auto_login_recovery`**.
  2. **Auto login recovery**:
     - Chỉ được kích hoạt khi app switcher không có nick chỉ định hoặc không có account nào đăng nhập.
