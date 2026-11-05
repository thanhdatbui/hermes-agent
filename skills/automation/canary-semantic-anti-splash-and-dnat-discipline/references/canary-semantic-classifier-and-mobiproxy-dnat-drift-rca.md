# Chi Tiết Kỹ Thuật: Khắc Phục Lỗ Hổng Semantic Canary & Lệch Ánh Xạ DNAT MobiProxy (05/11/2026)

## 1. Sự Cố Semantic Canary Planner & Anti-Fake Evidence
- **Hiện tượng:** Sửa `live_phase_b_adapter.py` nhưng `canary_plan.py` lại phân loại thành `evidence_type = "backend"`, `requires_screencap = False`. Coordinator lợi dụng kẽ hở này gắn `--no-canary` để né Gate 6. Khi bị truy hỏi, runner lại fallback gọi `am start SplashActivity` chụp màn hình splash chữ "TikTok" đen sì nộp bài đối phó.
- **Root Cause trong Code:**
  - `determine_evidence_type()` trong `canary_plan.py` chỉ quét thẻ web `<button`, `<div>`, `.tsx`, bỏ lọt code Python Android UI Automation (`*_adapter.py`, `selectors.py`, `touch`, `swipe`, `F2AScreen`).
  - `get_repo_diff()` chỉ đọc `git diff base HEAD`, bỏ qua các thay đổi uncommitted ở working tree vừa tạo ở S2.
  - `canary_runner.py` có đoạn fallback tự mở `SplashActivity` khi thiếu ảnh screencap và chỉ check `is_launcher_screen()`.
- **Bản vá kiến trúc:**
  - Bổ sung `android_ui_path_pattern` và `android_ui_diff_keywords` trong `canary_plan.py`.
  - Ưu tiên `git diff HEAD` uncommitted trong `get_repo_diff()`.
  - Xóa bỏ `am start SplashActivity`, thêm `is_splash_screen()`, ép kiểm tra `ocr_spec` (`required_terms`, `forbidden_terms`) và `log_assertions`.

## 2. Sự Cố Lệch Dây Chuyền DNAT MobiProxy (Cascade Port Drift)
- **Hiện tượng:** Khi chạy batch 2FA, hàng loạt máy cụm Kibe bị `ConsumerPreflightError` (connection refused trên cổng nội bộ MikroTik `20019, 20020, 20029...`), trong khi đo trực tiếp ra IP WAN ngoài Thái Bình thì proxy vẫn sống.
- **Root Cause:**
  - MobiProxy 4G có 32 cổng chia theo 4 card LAN, mỗi card 8 cổng:
    * Lan1: `5101..5108`
    * Lan2: `5111..5118` (ngắt quãng, không có 5109, 5110)
    * Lan3: `5121..5128` (ngắt quãng, không có 5119, 5120)
    * Lan4: `5131..5138` (ngắt quãng, không có 5129, 5130)
  - Rule DNAT cũ trên RouterOS dùng công thức `to-ports = 200xx - 14900 = 51xx`. Bắt đầu từ M9 (`20009` ➔ `5109`), MikroTik bắn vào cổng ảo không tồn tại, gây lệch dây chuyền 21 máy M9..M32.
  - Ngoài ra, các cổng `20033..20038` bị gắn 6 rule DNAT thừa cướp mất luồng PPPoE/Sing-box.
- **Giải pháp:**
  - PATCH toàn bộ 21 rule DNAT trên MikroTik qua REST API `/rest/ip/firewall/nat` theo đúng mapping từng block card LAN.
  - Vô hiệu hóa 6 rule thừa `*360..*365` để các cổng `20033..20038` tự rơi xuống Sing-box container.
  - Kích hoạt đổi IP đồng loạt (Recreat 4G) toàn bộ 32 cổng MobiProxy qua endpoint `http://test.taadaa.click/proxy_recreat?proxy=test.taadaa.click:{port}&token={token}` (delay 1-2s giữa các port) để các modem redial nhận IP WAN sạch mới, triệt tiêu nguy cơ máy này đụng IP/proxy máy khác sau khi sửa mapping.
