# Cross-Session Dirty Bleeding & Scope Isolation Lessons (06/10/2026)

## 1. Vấn đề thực tế (Problem Statement)
Khi nhiều phiên làm việc (sessions) hoạt động trên cùng một hệ thống repo farm (`D:/Taadaa/*`):
- Một phiên trước bị lỗi hoặc bị hủy ngang thường bỏ lại các file uncommitted dirty trong working tree.
- Ví dụ cụ thể ngày 06/10/2026:
  - File `docs/uiautomator.md` bị xóa 967 dòng (~40KB diff) trên toàn bộ 16 repo nhưng chưa từng được commit.
  - Thư mục rác tạm bợ từ mock test: `MagicMock/`, `debug_*.py`.
  - Repo `tiktok-luot nuoi acc` ngậm tới 196KB diff dồn tích từ 8 file khác nhau.
- Khi người dùng vào phiên sau gõ "chốt phiên", lệnh Closeout Gate mặc định quét toàn bộ repo và gom sạch 196KB rác này vào diff review.

## 2. Hậu quả
1. Vượt trần 24KB của Sol Web 0đ $\to$ kích hoạt fallback sang Terra Codex (`cx/gpt-5.6-terra-high`).
2. Terra Codex review chậm, trừ điểm nặng vì thấy code rác và file xóa khổng lồ $\to$ điểm chỉ đạt 57–77.
3. Quy chế remediation tiếp tục sinh task sửa chữa, kéo dài kẹt nửa ngày.
4. Với cơ chế Fail-Fast 24KB mới, lệnh sẽ văng ngay Exit Code 3 (`DIFF_TOO_LARGE`).

## 3. Quy chuẩn xử lý dứt điểm (Standard Operating Procedure)

### Quy tắc 1: Luôn dùng `--files` khi repo có dirty files
Trước khi chạy `closeout_gate.py`, Coordinator phải inspect `git status --short`.
- Nếu repo có bất kỳ file dirty nào không thuộc phạm vi task hiện tại:
  **BẮT BUỘC** gọi gate với danh sách file mục tiêu:
  ```bash
  python D:/Taadaa/tools/closeout_gate.py --repo <repo_path> --files <target_file1> <target_file2> --json-output
  ```
- Cổng sẽ cô lập hoàn toàn scope, chỉ bóc đúng 10–20 dòng diff của task, bỏ qua 196KB rác xung quanh $\to$ giữ diff trong ngưỡng Sol Web 0đ (15–20s) và pass ngay vòng 1.

### Quy tắc 2: Phân loại Exit Code 3 (`DIFF_TOO_LARGE`)
Khi `closeout_gate.py` trả về exit code 3:
- Đây là lỗi vi phạm phân rã tác vụ (Task Decomposition Violation), KHÔNG phải lỗi logic code hay syntax.
- **CẤM TUYỆT ĐỐI** tiếp tục đẻ remediation task để sửa code.
- Hành động đúng:
  1. Kiểm tra lại danh sách `--files`.
  2. Bóc tách và hoàn tác (checkout/restore) các file rác không liên quan.
  3. Hoặc tách task lớn thành chuỗi các micro-tasks O(1) nhỏ hơn.

### Quy tắc 3: Dọn dẹp nợ kỹ thuật toàn cục (Global Debt Cleanup)
Các thay đổi mang tính toàn cục (như xóa `docs/uiautomator.md` trên toàn farm):
- Phải được commit riêng trong một phiên dọn dẹp chuyên trách (`chore: cleanup legacy docs`).
- Tuyệt đối không để nằm trôi nổi trong working tree làm ô nhiễm diff của các tính năng và bản vá lỗi tiếp theo.
