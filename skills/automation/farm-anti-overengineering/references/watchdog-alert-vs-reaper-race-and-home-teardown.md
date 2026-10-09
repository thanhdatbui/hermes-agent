# Kỷ Luật Thiết Kế Watchdog Alert vs Tự Động Hóa Teardown

## 1. Tránh Báo Động Thừa Thãi (Watchdog Race Condition)
- Khi hệ thống đã có cơ chế tự động dọn dẹp / tự lành (Self-healing Reaper), việc tài nguyên chạm ngưỡng TTL bình thường là hành vi dự kiến, KHÔNG phải lỗi khẩn cấp.
- **Quy tắc phân tầng:**
  - Auto-Reaper: TTL 60 phút, chạy mỗi 5 phút (`*/5 * * * *`).
  - Watchdog Alert: Ngưỡng cảnh báo Telegram BẮT BUỘC >= 90 phút (Fail-safe alert).
  - Mục tiêu: 99% ca treo tự dọn âm thầm mà không spam tin nhắn làm phiền operator. Chỉ cảnh báo khi Reaper đã chạy nhiều chu kỳ mà lock vẫn kẹt.

## 2. Quy Chuẩn Hiện Trường Lỗi & Teardown Về HOME
- **Không ngâm màn hình máy thật để debug:**
  - Màn hình máy thật để lâu sẽ tự khóa, tự sleep, hoặc app tự reload làm mất hiện trường.
  - Ngâm máy gây nghẽn tài nguyên cho các nick/batch kế tiếp.
  - Hiện trường số hóa chuẩn gồm 3 artifact: `dump.xml` (tọa độ, id, class) + `screenshot.png` (giao diện thực) + log traceback. Bộ ba này là đủ 100% để debug và viết unit test mà không cần giữ màn hình live.
- **Teardown bắt buộc trong khối `finally:` cho mọi script:**
  - Mọi runner (Feed, Reg, Follow, Upload, 2FA) khi kết thúc (dù thành công hay exception/failure) BẮT BUỘC gọi `am force-stop` và `input keyevent 3` (KEYCODE_HOME) đưa máy về màn hình chính sạch sẽ trước khi nhả lock.
