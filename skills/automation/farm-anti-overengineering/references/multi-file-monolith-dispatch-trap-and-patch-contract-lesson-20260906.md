# Multi-File Monolith Dispatch Trap & Mandatory Patch Contract Lesson (06/09/2026)

## 1. Sự Cố Hiện Trường (Máy 27 - Alert VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)
- **Bối cảnh:** Nhận Farm Alert Máy 27 (`ce031823912ae0d20c`) lỗi `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.
- **Hành vi ban đầu:** Coordinator phân tích sơ bộ và dispatch Worker 1 với goal mở trên 2 file lớn:
  `D:/Taadaa/Tiktok-video/scripts/tiktok_workflow/run_post.py` (~1.500 dòng) và `state_machine.py` (~13.000 dòng).
- **Hậu quả:** Worker 1 rơi vào vòng lặp đọc XML dump, tìm kiếm selector, sửa `state_machine.py` và cập nhật `test_tiktok_workflow.py`. Sau 35 tool calls (1.493 giây ~ 25 phút), worker chạm trần `max_iterations = 35` mà CHƯA HỀ sửa `run_post.py` và CHƯA HỀ chạy Canary!
- **Phát hiện khi đối chiếu:** Worker báo cáo tóm tắt "kế hoạch patch" nhưng khi Coordinator kiểm tra `git diff run_post.py`, file hoàn toàn trống (chưa ghi đĩa).

---

## 2. Bài Học Rút Ra & Nguyên Tắc Khắc Phục

### A. Cấm Dispatch Worker Với Dual Scope / Goal Mở Trên Monolith
- Khi sự cố liên quan đến monolith file (>5.000 dòng như `state_machine.py` 13k dòng) hoặc nhiều file cùng lúc:
  - **CẤM TUYỆT ĐỐI** giao worker vừa "phân tích log/root cause", vừa "sửa file A", vừa "sửa file B", vừa "chạy test".
  - Worker sẽ dùng hết 35 lượt gọi chỉ để đọc hiểu context và chỉnh sửa file đầu tiên, bỏ quên file thứ hai và canary test.

### B. Quy Trình 2 Pha Cho Sự Cố Đa File (Two-Phase Resolution)
1. **Pha 1 - Khóa mã nguồn & Soạn Patch Contract (Coordinator):**
   - Coordinator tra cứu chính xác dòng lỗi O(1) qua log run cụ thể (ví dụ `D:/CodexRuntime/.../execution.log`).
   - Định vị đoạn code cũ (`old_string`) và kiểm tra tính duy nhất: `text.count(old1) == 1`.
   - Soạn sẵn `new_string` chính xác tuyệt đối.
2. **Pha 2 - Dispatch Worker Thực Thi Hẹp (Strict Execution Worker):**
   - Goal: *"Áp Patch Contract cho file X, kiểm tra py_compile và chạy canary test trên máy N."*
   - Cung cấp sẵn `old_string` và `new_string`.
   - Giới hạn budget: <= 8 tool calls, hoàn thành dưới 5 phút.
   - Worker áp patch bằng 1 script Python find-and-replace, `py_compile`, và kích hoạt Canary ngay lập tức.
