# Canary Execution & Popup Auto-Recovery Rules

## 1. Quy Tắc Điều Phối Canary Test (Coordinator Invariant)
- **Không bỏ dở giữa chừng:** Khi subagent nhận task xử lý Farm Alert máy N và chạm giới hạn `max_iterations` (150 bước) sau khi patch xong nhưng chưa chạy canary test, Coordinator **BẮT BUỘC** phải dispatch tiếp subagent để thực thi canary test và đọc log.
- **CẤM TUYỆT ĐỐI:** In câu lệnh PowerShell (`run-feed-session.ps1 ...`) ra màn hình bắt user tự chạy.

## 2. Xử Lý Popup TikTok Modal Chặn KEYCODE_BACK
- **Hiện tượng:** Các modal xin quyền hệ thống của TikTok (quyền danh bạ "Để kết nối với những người bạn biết trên TikTok", quyền vị trí, thông báo) chặn phím `KEYCODE_BACK`. Bấm BACK modal không đóng.
- **Giải pháp chuẩn:**
  1. Dump hierarchy chuẩn qua `dump_current_ui(ctx.adb)` (không gọi `ctx.dump_hierarchy()` vì DeviceContext không có method này).
  2. Parse XML để tìm node text ("Không cho phép", "Don't allow", "Từ chối", "Hủy") và tap chính xác vào bounds center `(cx, cy)`.
  3. Bổ sung fallback tap theo tỷ lệ màn hình `(w * 0.305, h * 0.639)` cho nút từ chối bên trái dưới modal nếu uiautomator dump bị nghẽn/timeout.

## 3. Quy Chuẩn Gọi Claude Code CLI
- Khi user yêu cầu gọi Claude CLI để review code, tư vấn kiến trúc hoặc điều tra sự cố:
  - Luôn sử dụng cờ model và reasoning cao nhất: `claude -p "..." --model opus --effort max`.
