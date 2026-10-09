# Pitfall: Account Switcher Anchor Misidentification & 8-Account Off-screen

## Vấn đề
Khi chạy workflow chuyển đổi tài khoản (account switcher) trên máy farm Samsung Galaxy S7 (1080x1920) nạp 8 tài khoản:
1. Viewport đầu tiên chỉ hiển thị 4 nick; nick đích (ví dụ Tik4 - Tik8) bị khuất phía dưới. Cần cuộn `input swipe 540 1536 540 960 450` tối đa 3 lần.
2. TikTok bổ sung icon `Số lượt xem hồ sơ` và prompt `Tám chuyện nào` ở header khiến `find_switcher_anchor` nhận nhầm, hoặc `coordinate_fallback` trả về sai tọa độ giữa màn hình `(540, 552)`.
3. Switcher dropdown thực tế nằm ở đỉnh thanh header: `(539, 140)`. Bắt buộc blacklist các header control marker trong `automation_core/tiktok/account_switcher.py`.
