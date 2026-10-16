# Strike 3 Reviewer Hand-off: Claude Turns Cap & Candidate Ranking Invariants (16/10/2026)

## 1. Bối cảnh Sự cố (Incident Context)
Khi Closeout Gate chạm mốc Strike 3 (3 lần REJECT liên tiếp trên cùng scope hash), cơ chế tự động kích hoạt chuyển giao quyền can thiệp cho Reviewer (`[REVIEWER_HANDOFF_TRIGGERED]`).
Coordinator dispatch `python D:/Taadaa/tools/claude_worker.py --role worker` mà không truyền cờ `--max-turns`.
- **Hậu quả:** `claude_worker.py` gán mặc định `default_turns = 8` cho role `worker`.
- Khi Claude Code CLI phải đồng thời refactor mã nguồn nghiệp vụ (`ocr.py`) và mở rộng test suite chuyên sâu (`tests/test_ocr.py`), chu trình gồm: đọc file hiện tại -> lập kế hoạch -> sửa file 1 -> sửa file 2 -> chạy pytest -> phân tích output.
- Quá trình chạm trần turn ở lượt 8 và dừng khẩn cấp: `Error: Reached max turns (8)`.

## 2. Quy Tắc Điều Phối Bắt Buộc (Dispatcher Invariants)
1. **Thiết lập Max Turns Đủ Ngân Sách Cho Strike 3:**
   - Với các tác vụ Strike 3 remediation đụng từ 2 file trở lên (1 file code + 1 file test), BẮT BUỘC truyền cờ `--max-turns 15` (chạm trần cứng `hard_cap_turns` của worker role).
   - Tuyệt đối không để mặc định 8 turns khi yêu cầu bao gồm cả việc viết thêm các integration/unit tests phức tạp.
2. **Quy Tắc Xếp Hạng Candidate Khi OCR Trả Về Nhiều Nút Bấm:**
   - Khi có nhiều box OCR cùng thỏa mãn nhãn `not_followed` (ví dụ `"Follow lại"` và `"Follow"` cùng xuất hiện do gợi ý hoặc danh sách):
     - **Ưu tiên 1:** Khoảng cách dọc tới tâm dải header (`anchor_y`).
     - **Ưu tiên 2:** Khi khoảng cách dọc bằng nhau, ưu tiên nhãn chính thức `"follow"` (priority 0) trước các nhãn thứ cấp `"follow lai"` / `"theo doi"` (priority 1).
