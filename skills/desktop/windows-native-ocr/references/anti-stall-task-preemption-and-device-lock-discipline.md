# Kỷ Luật Trách Nhiệm Vận Hành & Chống Trốn Tránh Bằng Batch Khóa Máy (2026-11-01)

## 1. Bản Chất Của Lỗi Trốn Tránh Trách Nhiệm (The False Lock Stall Trap)
- **Hiện tượng:** Khi được giao nhiệm vụ vận hành quy mô lớn (ví dụ: đổi email cho toàn bộ dàn máy farm), Coordinator phát hiện một số máy bị giữ device lock bởi tiến trình khác (như batch nuôi acc `run_tiktok.py --mode multi-machine-feed-session`), thay vì chủ động can thiệp dứt điểm, Coordinator lại:
  1. Dừng thi công và viết báo cáo phân trần, đổ lỗi cho tiến trình lock ngầm.
  2. Để tiến độ bị treo từ nửa đêm tới sáng mà không hoàn thành hạn mức.
  3. Bị User nổi giận vì nói nhiều mà không hành động thực chất.
- **Hậu quả:** Gây tắc nghẽn công việc ưu tiên của User, vi phạm nghiêm trọng nguyên tắc hành động chủ động của Hermes Farm.

## 2. Kỷ Luật Xử Lý Khóa Máy & Thứ Tự Ưu Tiên (Task Preemption Discipline)
1. **Mệnh Lệnh User Có Quyền Ưu Tiên Tuyệt Đối (Highest Precedence):**
   - Khi User đã ra chỉ thị trực tiếp thực hiện nhiệm vụ khẩn cấp (thay thế email DIE, cứu hộ tài khoản), nhiệm vụ đó có độ ưu tiên cao hơn mọi batch chạy định kỳ ngầm (nuôi acc, lướt feed, tải video).
   - Nếu batch ngầm cản trở và giữ lock trên các máy mục tiêu: Coordinator được phép kill tiến trình ngầm chiếm lock, xóa stale lock files `C:/Users/Kibe/.codex/device-locks/*.lock.json` và giải phóng tài nguyên để thi công ngay.
2. **Cấm Viện Cớ Lock Để Đứng Im:**
   - Nếu không muốn kill batch ngầm: Phải lọc ngay danh sách máy rảnh (IDLE) không bị lock để thi công trước 100%.
   - Tuyệt đối cấm báo cáo "Farm đang bận nuôi acc nên em dừng chờ" khi User đang chờ kết quả nghiệm thu.
3. **Quy Tắc Tương Tác Thẳng ADB Khi ATX Stub 502:**
   - Khi `atx-agent` hoặc stub `com.github.uiautomator` bị treo/502 Bad Gateway trên Samsung S7:
     - Dùng `reset_atx_agent` từ `automation_core.persistent_ui` một lần duy nhất.
     - Nếu vẫn chập chờn: Fallback ngay lập tức sang lệnh điều hướng an toàn qua ADB `input tap` / `input text` kết hợp **WinRT OCR (`ocr_screen_boxes`)** bóc tọa độ thực tế.
     - Không được cố khởi động lại stub bằng lệnh `am instrument` (vi phạm GuardGate).
