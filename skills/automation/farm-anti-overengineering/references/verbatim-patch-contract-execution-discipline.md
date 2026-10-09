# Verbatim Patch Contract Execution Discipline & Budget Conservation

## 1. Bối cảnh & Trigger
Khi nhận yêu cầu có đặc điểm:
- User cung cấp **sẵn toàn bộ patch contract chính xác** (cặp `old_string` và `new_string` cụ thể, không cần suy diễn).
- User cung cấp **sẵn mã nguồn unit test**, lệnh test cụ thể, và lệnh git commit.
- Yêu cầu kèm theo giới hạn ngân sách chặt chẽ (ví dụ: `Budget <= 10 calls, hoàn thành dưới 5 phút` hoặc `Fail-Fast Gate 4 <= 15 calls`).

## 2. Anti-Pattern: Pre-Patch Paralysis (Khảo sát thừa thãi làm cạn kiệt budget)
Trong nhiều phiên làm việc, agent mắc lỗi phân tích lan man trước khi áp dụng patch:
1. Chạy hàng loạt lệnh thăm dò hệ thống: `ls /d`, `ls /d/Taadaa`, `ls /d/Taadaa/Tiktok_Reg`, `pwd`, `df -h`.
2. Kiểm tra `git status`, `git diff` toàn diện khi chưa bắt đầu làm việc.
3. Đọc lại từng file đầy đủ hoặc grep từng vị trí một cách tuần tự (17 tool calls chỉ để xác nhận vị trí chuỗi có tồn tại không).
4. **Hậu quả**: Chạm trần số lần gọi công cụ (iteration limit / budget exhaustion) TRƯỚC KHI thực hiện bất kỳ sửa đổi nào, khiến tác vụ thất bại dù lời giải đã nằm 100% trong prompt.

## 3. Quy trình thực thi tinh gọn (Zero-Exploration Direct Execution)

Khi prompt đã chứa đầy đủ verbatim patch contract:

### Bước 1: Áp dụng trực tiếp bằng `patch` tool (Không đọc/grep trước)
- Gọi trực tiếp `patch(path=..., old_string=..., new_string=...)` cho từng vị trí.
- Tool `patch` có sẵn cơ chế so khớp (exact & fuzzy matching). Nếu chuỗi khớp, patch thành công ngay lập tức (1 call).
- CHỈ KHI `patch` trả về lỗi không tìm thấy `old_string`, mới dùng `grep -n` hoặc `read_file` nhắm mục tiêu vào duy nhất vị trí đó.

### Bước 2: Ghi file test trực tiếp bằng `write_file`
- Ghi thẳng nội dung test được cung cấp vào đường dẫn test bằng `write_file`. Không cần `ls tests/` hay kiểm tra thư mục cha (tool tự tạo parent directory).

### Bước 3: Chạy test kiểm chứng (1 terminal call)
- Chạy đúng lệnh test được chỉ định (ví dụ: `pytest path/to/test.py -v`).

### Bước 4: Git commit (1 terminal call)
- Chạy đúng lệnh git add & git commit được chỉ định.

## 4. Ngân sách chuẩn cho tác vụ Verbatim Patch
- File 1 (2 vị trí): 2 tool calls `patch`.
- File 2 (3 vị trí): 3 tool calls `patch`.
- Tạo file test: 1 tool call `write_file`.
- Chạy pytest: 1 tool call `terminal`.
- Git commit: 1 tool call `terminal`.
**Tổng cộng: 8 tool calls.** Hoàn thành trong vòng 1-2 turn, hoàn toàn nằm trong ngân sách <= 10 calls mà không vi phạm Gate 4.
