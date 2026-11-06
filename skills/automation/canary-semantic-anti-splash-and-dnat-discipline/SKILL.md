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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
