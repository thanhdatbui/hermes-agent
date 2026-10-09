# Worker Tool Budget & Over-scoping Discipline (Anti-Insanity Lesson)

## Bối cảnh bài học (14/09/2026)
- Khi Coordinator dispatch một task sửa code (Code Surgery) gồm 4 file (trong đó có monolith > 1.500 dòng như `download_by_niche.py`) cho 1 Worker duy nhất với budget trần 15 tool calls:
- **Hiện tượng**: Worker dành toàn bộ 15 turn để dùng `read_file` và `search_files` kiểm tra AST, imports và các vị trí xung quanh. Hết 15 turn, worker dừng mà không ghi được thay đổi nào xuống đĩa (**0 files modified**).
- **Hệ quả**: Cháy budget thời gian (gần 10 phút) và cạn lượt gọi tool mà không sinh ra artifact thực tế.

## Nguyên tắc điều phối khắc phục (Enforcement)
1. **Phân rã phạm vi tối đa 2 file / worker**:
   - Khi có từ 3 file trở lên cần chỉnh sửa, Coordinator bắt buộc phải tách thành các sub-task độc lập theo cụm tính năng và chạy batch qua `tasks=[...]`.
2. **Cung cấp Exact Contract kèm Anchor duy nhất**:
   - Cung cấp chính xác `old_string` -> `new_string` đã được Coordinator xác minh O(1) từ trước.
3. **Cấm lặp lại Inspect không cần thiết**:
   - Ra lệnh dứt khoát cho Worker: "Dùng tool `patch` trực tiếp ngay ở call 1-2, cấm inspect toàn bộ file".
4. **Cảnh báo thiếu Import**:
   - Khi chèn các đoạn mã sử dụng `sys` hoặc `subprocess` trên Windows (ví dụ `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)`), Coordinator phải kiểm tra trước file mục tiêu đã import module đó chưa để đưa vào contract thay vì để worker tự mò.
