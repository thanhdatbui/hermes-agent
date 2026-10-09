# QUY TẮC WORKER BUDGET & CHỐNG DÔNG DÀI (ANTI-OVERENGINEERING)

## 1. Bối cảnh & Nguyên nhân cốt lõi
- Worker subagent khi được dispatch qua `delegate_task` có xu hướng mở rộng phạm vi (Scope Creep): tự động đào sâu log hệ thống, reverse-engineer PID, tự ý sửa code ngoài phạm vi được giao, và tự chạy pytest trên toàn bộ monorepo (2000+ tests gây timeout 15 phút).
- Điều này từng khiến subagent đốt 115 tool calls và chạy gần 2 tiếng mà không hoàn thành đúng trọng tâm.

## 2. Các tầng khóa bảo vệ (Enforcement Layers)

### Lớp 1: Khóa cứng nền tảng (Platform Hard Ceiling)
- Trong `C:/Users/Kibe/AppData/Local/hermes/config.yaml`:
  ```yaml
  delegation:
    model: ag-gemini-pool-3
    provider: omni
    max_iterations: 35
  ```
- Trần cứng 35 iterations chặn đứng mọi worker không thể chạy dông dài vượt quá 35 lượt gọi tool.

### Lớp 2: Phân loại Task & Ngân sách bắt buộc (Task Budgets)
1. **Task Read-only / Inspect / OCR / Log analysis:**
   - Ngân sách: Tối đa $\le 10$ tool calls, thời gian $< 10$ phút.
   - Giới hạn cứng: CẤM TUYỆT ĐỐI sửa code, CẤM chạy test suite pytest, CẤM commit.
   - Chỉ đọc log, OCR ảnh, tóm tắt hiện trường và trả kết quả ngay cho Coordinator.
2. **Task Sửa Code (Bug Fix / Recovery):**
   - Ngân sách: Tối đa $\le 20$ tool calls, thời gian $< 15$ phút.
   - **Scope Lock:** Chỉ sửa ĐÚNG file flow / module được chỉ định (ở core sửa core, ở flow sửa flow, cấm sửa lan man).
   - **Test Lock:** CHỈ chạy focused test (`pytest [test_file] -k [test_name]`), thời gian chạy test $< 30$ giây. CẤM TUYỆT ĐỐI chạy bare `pytest` trên toàn bộ monorepo.

### Lớp 3: Điều phối tại Coordinator
- Khi dispatch worker: bắt buộc truyền cờ Scope Lock, Test Lock và budget vào trường `context` của `delegate_task`.
- Tránh phản hồi trùng lặp (Duplicate message): Không gửi tin nhắn dông dài báo cáo nửa chừng trước khi worker hoàn tất. Đợi kết quả thống nhất để phản hồi 1 lần súc tích cho người dùng.

## 3. Telegram Farm Alert Photo Caption Budget
- Telegram API `sendPhoto` giới hạn trần cứng caption $\le 1024$ ký tự.
- CẤM gửi caption vượt quá 1024 ký tự dẫn đến lỗi `MEDIA_CAPTION_TOO_LONG` (Telegram từ chối nhận ảnh có banner đỏ số máy).
- Mọi trường dữ liệu động (`serial`, `account`, `error_reason`, `status_text`) BẮT BUỘC dùng `html.escape()` trước khi nhúng vào HTML caption để tránh văng lỗi parser.
- Nội dung 5 bước recovery phải được tinh gọn súc tích và cắt bằng `_safe_truncate_html(caption, 1024)` để đảm bảo 100% alert đều gửi thành công kèm ảnh banner đỏ.
