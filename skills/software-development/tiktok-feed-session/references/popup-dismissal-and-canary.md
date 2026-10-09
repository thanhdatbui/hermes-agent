# TikTok Popup Dismissal & Canary Invariants

## 1. Xử Lý Modal Xin Quyền Danh Bạ / Kết Nối Bạn Bè
- **Vấn đề:** Popup *"Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị"* chặn `KEYCODE_BACK`.
- **Logic xử lý trong `benign_popup_registry.py`:**
  - Gọi `dump_current_ui(ctx.adb)` trích xuất XML hierarchy.
  - Tìm node text `"Không cho phép"` / `"Don't allow"` / `"Từ chối"` / `"Hủy"` và lấy tọa độ `[bounds]` để tap.
  - Fallback theo tỷ lệ: `(int(w * 0.305), int(h * 0.639))` cho nút từ chối bên trái.

## 2. Invariant Canary Test Bắt Buộc
- Bất kỳ subagent nào phụ trách fix lỗi flow nuôi acc / feed session đều phải chạy lệnh canary test và đọc file `.ai-runs/latest/summary.txt` xác nhận `SUCCESS` trước khi kết thúc task.
