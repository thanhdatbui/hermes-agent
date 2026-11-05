---
name: desktop-anti-focus-theft
description: Kỷ luật và giải pháp kỹ thuật ngăn chặn background browser (GPM, Chrome) và app tự động cướp focus / che màn hình khi User đang chơi game (TFT, LMHT) hoặc làm việc.
---
# Desktop Anti-Focus Theft & Gaming Coexistence

Kỹ thuật và kỷ luật bắt buộc khi chạy các tác vụ automation, browser ngầm (GPMLogin, Chromium, Playwright, Selenium) trên máy host mà không làm gián đoạn người dùng (đặc biệt khi đang chơi game TFT, LMHT, xem phim hoặc gõ phím).

## 1. Bản Chất Kỹ Thuật (Focus Stealing & Window Popping)
- Khi Windows khởi tạo cửa sổ GUI của một tiến trình mới (như `chrome.exe`), hệ điều hành mặc định cấp quyền Foreground (`SetForegroundWindow`), làm giật chuột, cướp focus phím khỏi game toàn màn hình / borderless.
- **Bẫy sót cửa sổ mồ côi (Orphan Window Trap):** Kể cả khi lệnh mở mới đã được sửa cờ, nếu trên desktop còn sót các cửa sổ trình duyệt mồ côi từ phiên trước, khi các tab này reload, điều hướng hoặc có alert, Windows sẽ giật focus về chúng.

## 2. Invariant Khởi Chạy Profile Trình Duyệt Ngầm (Offscreen Contract)
Mọi kịch bản mở profile Chromium / GPM trên máy host BẮT BUỘC phải truyền tọa độ âm ngoài tầm hiển thị:
- **GPM Local API parameters:**
  `win_pos=-2500,-2500&window_size=800,600&win_scale=0.5`
- **Chromium CLI arguments (vendor key `addination_args` cho GPM):**
  `--window-position=-2500,-2500 --window-size=800,600 --mute-audio --no-first-run`
- **Mẫu mã nguồn chuẩn:**
  ```python
  import urllib.parse, requests

  args = "--window-position=-2500,-2500 --window-size=800,600 --mute-audio --no-first-run"
  enc_args = urllib.parse.quote(args)
  url = (
      f"http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}"
      f"?win_scale=0.5&win_pos=-2500,-2500&window_size=800,600"
      f"&addination_args={enc_args}&addition_args={enc_args}"
  )
  res = requests.get(url, timeout=30).json()
  ```

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
