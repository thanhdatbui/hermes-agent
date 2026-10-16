# Zero-Token Offline State-Machine Farm Automation Pattern

**Date:** 2026-10-16  
**Context:** User observed 160+ phones running multi-threaded parallel rename & verification without burning LLM quota, and directed: *"Ơ cơ chế này hay v. Bth hiện tại workflow có áp dụng chưa? Có ưu tiên áp dụng khi viết script chưa! Còn repo nào khả thi chưa áp dụng k... rồi thực thi đi, h tái cấu trúc mấy script nhỏ là workflow lớn đúng k"*.

---

## 1. Core Architecture: The Two-Tier Paradigm

A large-scale automation farm (160+ devices, 80 Kibe + 80 Admin) CANNOT rely on cloud LLMs or vision APIs for real-time runner loops. That exhausts rate limits, inflates costs, and introduces latency and network points of failure.

Instead, the system enforces a strict two-tier separation:

```
[ TẦNG NÃO BỘ: LLM Coordinator / Compiler ]
  - Triển khai khi: Tiếp nhận yêu cầu mới, triage sự cố, vá lỗi code, thiết kế State-Machine.
  - Nhiệm vụ: Phân tích hiện trường, code script runner canonical, chạy Canary test trên 1 máy thật.
  - Sau khi code hoàn thiện: RÚT LUI HOÀN TOÀN, không tham gia vào vòng lặp thực thi hàng loạt.
                                 │
                                 ▼ (Đóng gói thành Canonical Script)
[ TẦNG THỰC THI: Zero-Token Offline Runner + Cron `no_agent=True` ]
  - Chạy 100% ngầm bằng CPU máy tính qua WinRT OCR native (`Windows.Media.Ocr`).
  - Tốc độ: 0.2s - 0.5s / lần quét màn hình (nhanh gấp 10-50x so với XML dump hay API vision).
  - Tốn: ĐÚNG 0 TOKEN, 0 ĐỒNG API, KHÔNG BAO GIỜ BỊ RATE-LIMIT.
  - Cơ chế báo cáo: In ra stdout chuỗi `\nMEDIA:{p_posix}`. Hermes cronjob (`no_agent=True`)
    chuyển tiếp thẳng đến Telegram Gateway, tự động gửi ảnh photo native mà KHÔNG gọi LLM.
```

---

## 2. Why WinRT OCR Beats `uiautomator dump` & Cloud Vision

| Đặc tính | `uiautomator dump` (XML) | Cloud Vision API | WinRT OCR Native (Offline) |
|---|---|---|---|
| **Chi phí / Quota** | 0đ | Tốn tiền / tốn quota LLM | **0đ (hoàn toàn miễn phí)** |
| **Tốc độ** | 3s – 30s (hay bị freeze) | 2s – 10s (chờ mạng) | **0.2s – 0.5s (ngay trên CPU)** |
| **Độ ổn định** | Hay văng `null root node`, exit 137 | Dễ rớt mạng, lỗi 429/5xx | **100% ổn định, không rớt mạng** |
| **App bảo mật (Web3/Ví)** | Bị chặn, trả về XML trắng | Đọc được | **Đọc thẳng framebuffer `screencap`** |
| **Định vị tọa độ** | Parse bounds XML phức tạp | Ước lượng % màn hình | **Trả về bounding box `[x1,y1,x2,y2]` chuẩn pixel** |

---

## 3. "Tái Cấu Trúc Mấy Script Nhỏ Là Workflow Lớn"

Mọi workflow phức tạp trên farm (Đăng ký tài khoản, Đổi biệt danh, Nuôi feed, Follow, Bật 2FA, Đổi avatar) về bản chất đều là chuỗi ghép nối của các **micro-actions** nguyên tử theo mô hình State-Machine:

1. **Capture Framebuffer O(1):** `shell screencap -p /sdcard/s.png` -> `adb pull`.
2. **WinRT OCR Detection:** Gọi `ocr_boxes.ps1` lấy danh sách `(text, [x1, y1, x2, y2])`.
3. **State Classification:** Phân loại màn hình hiện tại (ví dụ: `PROFILE`, `SWITCHER`, `NAME_EDIT`, `POPUP_DISMISS`, `UNKNOWN`).
4. **Mechanical Action:**
   - Tap vào tâm bounding box của nút mục tiêu: `tap(cx, cy)` (TUYỆT ĐỐI CẤM tap mù tọa độ cứng).
   - Lùi màn hình: Dùng phím cứng vật lý `shell input keyevent 4` (KEYCODE_BACK).
   - Nhập liệu: Bơm text UTF-8 qua `AdbKeyboard` broadcast.
5. **Readback Assertion:** Chụp ảnh màn hình kết quả và dùng WinRT OCR đọc đối soát lại (ví dụ: tên mới, trạng thái "Đã follow", "Xác minh 2 bước đang bật").
6. **Delivery:** Xuất file ảnh nghiệm thu và in `\nMEDIA:{p_posix}` ra stdout.

---

## 4. Target Repositories for Migration / Refactoring

1. **`D:/Taadaa/Tiktok_Reg` (`social_reg_v1.py`):**
   - **Vấn đề cũ:** Lạm dụng `get_ui_xml()` và retry atx-agent 3 lần rất dễ timeout và nghẽn tiến trình.
   - **Refactoring:** Chuyển các bước onboarding ("Chọn sở thích", "Lưu thông tin đăng nhập", "Sử dụng email") sang WinRT OCR Fast-Path.
2. **`D:/Taadaa/tiktok-follow`:**
   - **Vấn đề cũ:** Dùng tọa độ tương đối để bấm nút Follow, dễ bấm trượt trên các máy có tỉ lệ màn hình/font khác nhau.
   - **Refactoring:** WinRT OCR tìm chính xác box chữ `"Follow"` / `"Follow lại"` và tap vào tâm; readback chữ `"Đang follow"` để xác nhận thành công.
3. **`D:/Taadaa/tiktok-log-in`:**
   - **Vấn đề cũ:** Kẹt form login, không phân biệt được captcha mảnh ghép puzzle với lỗi mật khẩu.
   - **Refactoring:** Xây dựng State-Machine 15 bước nhận diện từng trạng thái màn hình bằng WinRT OCR.
4. **`D:/Taadaa/airdrop-automation`:**
   - **Vấn đề cũ:** Các app Web3/Privy chặn accessibility khiến XML rỗng.
   - **Refactoring:** Đọc framebuffer trực tiếp bằng WinRT OCR, hoàn toàn miễn nhiễm với accessibility blocking.

---

## 5. Cron Configuration Golden Rules

- **`no_agent: True` Bắt buộc:** Đối với mọi cronjob watchdog định kỳ chạy script có sẵn (watchdog, sync, health check, batch runner). LLM chỉ được bật (`no_agent: False`) cho tác vụ cần suy luận ngôn ngữ tự nhiên.
- **`deliver: "origin"`:** Để tin nhắn tự động chuyển tiếp về đúng thread Telegram đang làm việc.
- **In POSIX Media:** Đường dẫn ảnh in ra stdout BẮT BUỘC dùng gạch xuôi:
  ```python
  p_posix = str(proof_path).replace("\\", "/")
  print(f"✅ [{task_name}] Máy {m:02d}: @{username} -> '{new_name}'\nMEDIA:{p_posix}", flush=True)
  ```
- **Silent Watchdog:** Khi không có việc hoặc ca đang bận (`is_feed_active()`), script phải thoát `sys.exit(0)` mà không in gì ra stdout để giữ im lặng hoàn toàn.
