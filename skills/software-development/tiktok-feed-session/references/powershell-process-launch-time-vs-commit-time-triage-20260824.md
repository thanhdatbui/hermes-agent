# PowerShell Process Launch Time vs Git Commit Chronology Triage

## Bối cảnh & Hiện tượng
Khi operator chụp ảnh màn hình terminal (PowerShell / CMD) và hỏi "sao vừa sửa code / config xong mà vẫn thấy bắn lỗi cũ hàng loạt":
- Console hiển thị lỗi config validation cũ (ví dụ: `[ALERT] [MÁY ##] Dừng: config-error | Lý do: feed-session-smoke requires 1 <= --max-swipes <= 15`).
- Operator ngỡ rằng bản fix chưa có tác dụng hoặc code bị rollback.

## Quy trình đối soát thời gian 3 lớp (Evidence-First Chronology)
1. **Kiểm tra System Tray Clock / Terminal Timestamp:**
   - Đọc đồng hồ hệ thống trên thanh Taskbar Windows trong ảnh chụp màn hình (ví dụ: `8:09:22 CH` -> `20:09:22`).
2. **Kiểm tra Git Commit Log Timestamp:**
   - Chạy `git log -n 5 --format="%h %cd %s"` để lấy thời điểm commit bản vá thật sự vào repo (ví dụ: commit `0785a38` lúc `20:28:21`).
3. **Đối chiếu mốc thời gian:**
   - Nếu `Thời điểm tiến trình chạy (20:09) < Thời điểm commit bản fix (20:28)`: Khẳng định tiến trình đang chạy trong ảnh là **tiến trình cũ khởi động trước khi fix**, đang giữ bytecode/module cũ trong RAM.
   - Giải thích ngắn gọn nguyên nhân cho operator và hướng dẫn tắt cửa sổ cũ, chạy batch mới.

## Nguyên tắc kết luận
- Không suy đoán code bị hỏng tiếp khi chưa đối chiếu timestamp của process với git log.
- Không sửa thêm code hay thay đổi config khi git HEAD đã chứa bản fix chuẩn.
