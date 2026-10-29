---
name: captcha-automation-pipeline
description: "Use when automating captcha solving (offline or cloud API)."
---
# Captcha Automation Pipeline (Offline & Cloud Fallback)

Quy chuẩn xử lý Captcha trong toàn bộ hệ thống Taadaa Automation (Farm Android, Shopee, TikTok, GPM/Playwright, Meta OAuth): Phân loại chính xác giữa **Offline OCR / CV (0đ, <5ms)** và **Cloud Bypass API (bảo mật cao, tốn credit)**.

---

## 1. Phân loại Captcha & Chiến lược giải quyết

| Loại Captcha | Đặc điểm nhận dạng | Giải pháp tối ưu | Công cụ / Module | Chi phí |
| :--- | :--- | :--- | :--- | :--- |
| **Chữ / Số méo mó** | Text méo, nhiễu gạch ngang, phép tính cộng trừ | **Offline Deep Learning (ONNX)** | `ddddocr` (`text_ocr_solver.py`) | **0đ** (~2ms) |
| **Trượt mảnh ghép (Slide Puzzle)** | Ghép khuyết hình trên TikTok, Shopee, GeeTest | **Offline Computer Vision / Edge Detection** | OpenCV + `ddddocr.slide_match` (`slide_puzzle_solver.py`) | **0đ** (~2ms) |
| **Xoay hình / Chọn 2 vật thể** | Xoay góc thẳng, nhận diện 2 icon cùng loại | **Offline Template Match / YOLO** | `ddddocr` det/match | **0đ** (~5ms) |
| **reCAPTCHA v2 / Enterprise** | Hộp checkbox "I'm not a robot", ảnh 3x3/4x4, Risk Score Google | **Cloud Solver API** | OMOCaptcha / CapSolver | ~15đ - 40đ / lần |
| **Cloudflare Turnstile** | Checkbox Cloudflare challenge, browser fingerprint | **Cloud Solver API** | OMOCaptcha / CapSolver | ~20đ - 40đ / lần |
| **Arkose FunCaptcha** | Trò chơi xoay góc phức tạp, match hướng nhìn | **Cloud Solver API** | OMOCaptcha / CapSolver | ~25đ - 50đ / lần |

---

## 2. Thư viện Offline Captcha Sandbox (`D:/Taadaa/tools/captcha_offline_sandbox/`)

Sử dụng môi trường venv chung: `/d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe`.

### A. Giải Text / Số / Phép tính
```python
from D.Taadaa.tools.captcha_offline_sandbox.text_ocr_solver import solve_text_captcha

# solve_text_captcha chấp nhận filepath hoặc raw bytes
result = solve_text_captcha("path/to/captcha.png")
print("Captcha text:", result)
```

### B. Giải kéo trượt mảnh ghép (Slider Puzzle)
```python
from D.Taadaa.tools.captcha_offline_sandbox.slide_puzzle_solver import solve_slide_puzzle

# Trả về khoảng cách x (px) cần kéo swipe
offset_x, offset_y = solve_slide_puzzle("background.png", "piece.png")
# Thực hiện kéo qua adb hoặc playwright:
# adb shell input swipe x1 y1 (x1 + offset_x) y1 500
```

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
