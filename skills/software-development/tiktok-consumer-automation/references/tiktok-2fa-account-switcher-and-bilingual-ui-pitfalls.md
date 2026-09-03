# TikTok 2FA, Account Switcher & Bilingual UI Pitfalls

## 1. TikTok Account Switcher Profile Anchor Resolution
- **Resource ID Suffix `pcq`**: Một số bản build TikTok trên farm hiển thị username/display_name tại Profile header dưới resource-id `com.ss.android.ugc.trill:id/pcq` (thay vì các ID cũ như `rn8`, `rv5`, `p48`...). Cần đảm bảo `_SWITCH_ANCHOR_RESOURCE_SUFFIXES` trong `automation_core.tiktok.account_switcher` có `pcq` để `find_switcher_anchor` nhận diện đúng.
- **Truyền `pre_confirmed_xml` khi mở Switcher**: Khi gọi `account_switcher.open_switcher(adapter, pre_confirmed_xml=...)`, nếu đã ở Profile root, truyền `profile_xml` đã confirm để tránh việc core chạy lại vòng lặp `leave_profile_subpage` vô ích hoặc bị kẹt khi bottom tab chưa render kịp.

## 2. Bilingual UI: English vs Vietnamese Localization
- **Profile Menu / Drawer**:
  - Tiếng Việt: `Cài đặt và quyền riêng tư`
  - Tiếng Anh: `Settings and privacy` (như xuất hiện trên Máy 12/các máy đổi ngôn ngữ hoặc bản build hỗn hợp).
- **Classifier & Selectors**:
  - Cả `f2a_classifier.py` và `live_phase_b_adapter.py` / `selectors.py` PHẢI hỗ trợ song ngữ Anh - Việt cho các mục Menu:
    * Profile Menu: `Settings and privacy` / `Cài đặt và quyền riêng tư`
    * Security: `Security & permissions` / `Bảo mật & quyền` / `Bảo mật và quyền`
    * 2FA / Two-Step: `2-step verification` / `Xác minh 2 bước`
    * Authenticator: `Authenticator app` / `Trình xác thực`
    * Password: `Password` / `Mật khẩu`

## 3. Batch Target Selection (Farm 1-80)
- Runner batch 2FA (`run_batch_live_2fa.py`):
  - Giới hạn số máy farm là `1 <= number <= 80` (tránh bị hardcode `<= 20`).
  - Cột serial trong workbook có thể là `device ID`, `device_id`, `series model máy` (cần chuẩn hóa lowercase / casefold).
  - Ưu tiên chọn các acc slot 1 & 2 (acc cổ) chưa có 2FA và có sẵn Password hoặc sinh pass hợp lệ.
