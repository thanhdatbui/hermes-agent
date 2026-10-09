# Dashboard Delta UI Formatting & Monolith Worker Dispatch Discipline (2026-09-24)

## 1. UI Formatting Pitfall: Tránh Ghép Chuỗi Thủ Công Dấu "+" với Giá Trị Âm
- **Bối cảnh:** Khi hiển thị delta chỉ số thay đổi (`delta_following`, `delta_follower`, `delta_heart`):
  * Nếu delta âm (`delta = -85`), việc ghép chuỗi cứng `+${delta}` hoặc `+str(delta)` sẽ sinh ra hiển thị dị tật: `+-85` hoặc `📈 Tổng tăng: +-85`.
- **Giải pháp chuẩn:**
  * Luôn kiểm tra dấu:
    ```python
    if tot_delta < 0:
        label = "📉 Tổng giảm:"
        color = "#ef4444"
        val_str = str(tot_delta)  # Đã có sẵn dấu trừ
    else:
        label = "📈 Tổng tăng:"
        color = "#22c55e"
        val_str = f"+{tot_delta}"
    ```
  * Cần đồng bộ 100% logic này giữa:
    1. Python initial HTML render (`render_html_page`).
    2. Client-side JS real-time refresh function (`setInterval` / `updateKpiDelta`).

## 2. Worker Dispatch Pitfall trên Monolith File (>1500 dòng)
- **Vấn đề:** Khi dispatch subagent sửa monolith file (`tiktok_dashboard.py`), nếu prompt không khóa chặt thao tác mà để worker tự do `search_files` / `read_file`, worker dễ bị lãng phí API call dẫn đến timeout 600s.
- **Kỷ luật Dispatch thành công (0-timeout):**
  * Coordinator dùng `read_file` / script kiểm tra trước tại chỗ, tìm đúng **exact anchor** và số lượng match (`count == 1`).
  * Chỉ thị rõ ràng trong worker context: **CẤM TUYỆT ĐỐI gọi search_files/read_file**, đi thẳng vào `patch(mode="replace")` cho từng anchor và chạy focused unit test (`pytest -k`).
  * Đảm bảo subagent hoàn thành chỉ trong ≤ 5 tool calls và < 3 phút.
