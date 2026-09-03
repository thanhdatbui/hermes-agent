# Fix Máy Farm - Nguyên Tắc Bắt Buộc: Sửa Codebase Thay Vì Thao Tác Tay

## User Invariant
Khi user yêu cầu: *"Fix máy XX"*, điều đó có nghĩa là:
1. **Tìm nguyên nhân gốc (Root Cause)**: Không chỉ nhìn bề nổi (vd kẹt lock, timeout) mà phải truy ra lỗi logic trong script (vd bug parse index dynamic forward port, timeout ngắn, thiếu retry/reset stub, handler popup chưa khớp...).
2. **Sửa trực tiếp vào Codebase / Script**:
   - Patch code vào `automation-core` hoặc consumer repo (`python_runner`, flows, helpers...).
   - Nếu sửa `automation-core`, phải copy vào site-packages của farm venv (`D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core`).
3. **Cập nhật Tài liệu Case Fix (Gate 0.5)**:
   - Thêm case vào `docs/farm-automation-cases.md` (`docs/uiautomator.md`).
4. **Kiểm thử & Bằng chứng (Live Canary)**:
   - Chạy regression test suite của repo.
   - Chạy live canary chính thức trên đúng máy mục tiêu chứng minh runner tự động xử lý thành công.
5. **CẤM**: Tuyệt đối không chỉ thao tác ad-hoc bằng tay (vd chạy reset một lần rồi bấm lướt tay hoặc không lưu code) rồi kết luận "đã fix".
