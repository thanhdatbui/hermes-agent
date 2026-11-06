---
name: canary-semantic-anti-splash-and-dnat-discipline
description: "Kỷ luật gắn não LLM cho Canary Planner, chống fake canary splash screen, chuẩn hóa ánh xạ DNAT MobiProxy 32 cổng và phòng thủ rò rỉ IP TikTok QUIC/UDP."
version: 1.1.0
category: automation
tags: [canary, semantic-planner, anti-splash, mobiproxy, dnat, mikrotik, quic-leak]
---
# Canary Semantic Anti-Splash, MobiProxy DNAT & Anti-Leak Discipline

## 1. Kỷ luật Semantic Canary Planner (`canary_plan.py`)
- **Lỗ hổng phân loại UI:** Các file Python Android UI Automation (`*_adapter.py`, `selectors.py`, `touch`, `swipe`, `F2AScreen`) không chứa thẻ HTML/JSX nên dễ bị nhầm thành `backend`. Bắt buộc phân loại là `evidence_type = "hybrid"` hoặc `"ui"` và `requires_screencap = True`.
- **Ưu tiên diff uncommitted:** `get_repo_diff()` phải đọc `git diff HEAD` trước để LLM Canary Planner phân tích đúng bản vá vừa sửa tại bước S2 thay vì diff commit cũ.
- **CẤM Coordinator tự ý bypass:** Tuyệt đối cấm tự thêm `--no-canary` vào code UI/Device flow.

## 2. Kỷ luật Anti-Splash & Anti-Fake Evidence (`canary_runner.py`)
- **Xóa bỏ fallback đối phó:** Triệt tiêu hoàn toàn lệnh `am start SplashActivity` khi thiếu screencap.
- **Khóa OCR chống Splash/Launcher:**
  - `is_splash_screen(ocr_text)`: Nếu ảnh chỉ chứa chữ "TikTok" hoặc màn hình chờ ➔ `SPLASH_SCREEN_FAKE_EVIDENCE` (FAIL).
  - `is_launcher_screen(ocr_text)`: Nếu ảnh là màn hình chính Launcher ➔ FAIL.
  - Thực thi nghiêm ngặt `ocr_spec` từ Semantic LLM Plan: Bắt buộc khớp `required_terms` (màn hình nghiệp vụ đích) và cấm `forbidden_terms`.

## 3. Quy chuẩn ánh xạ DNAT MobiProxy 32 cổng trên MikroTik
- MobiProxy gồm 4 block ngắt quãng (Lan1: 5101..5108, Lan2: 5111..5118, Lan3: 5121..5128, Lan4: 5131..5138).
- **CẤM dùng công thức tuyến tính** `200xx - 14900` gây lệch cổng hàng loạt từ M9..M32 (Cascade Port Drift).
- **Ánh xạ chuẩn:**
  - M1..M8 ➔ 5101..5108
  - M9..M16 ➔ 5111..5118
  - M17..M24 ➔ 5121..5128
  - M25..M32 ➔ 5131..5138
- M33..M38 và M71..M80: Thuộc PPPoE / Sing-box, cấm gán DNAT đè lên.
- **Quy chuẩn xoay vòng IP sau khi sửa mapping:** Bắt buộc kích hoạt `/proxy_recreat?proxy=test.taadaa.click:{port}&token={token}` giãn cách 1-2s cho toàn bộ 32 modem 4G để đổi IP WAN sạch, triệt tiêu nguy cơ đụng IP chéo giữa các máy.
- **Bóc tách phần cứng MobiProxy (38 Slots vs 32 Modems):** Xem `references/mobiproxy-hardware-slots-and-mikrotik-dnat-parity.md` để nắm rõ cấu trúc khe cắm vật lý cố định `10-10-10-8`, lý do không được ép về `8-8-8-8` làm chết port, và giải pháp phẳng hóa cổng `192.168.110.2:200xx` trên Excel/SQLite SSOT.
- **Kỷ luật cấm ngắt WAN 1 & Cấm gỡ mạng từ xa:** Xem `references/mobiproxy-wan1-safety-and-anti-cut-discipline-20261105.md` quy định bất biến: WAN 1/PPPoE 1 là default gateway cấp Internet và DDNS duy nhất, CẤM TUYỆT ĐỐI gọi delete_lan hoặc gỡ kết nối cổng 1 từ xa gây cô lập box và làm phiền nhân sự tại trạm.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
