# Dispatch Contract & Guard Format Reference

Khi điều phối Worker qua `delegate_task` với `TASK_KIND: EDIT`, Coordinator Guard (`guard_dispatch_contract.py`) kiểm tra định dạng cực kỳ nghiêm ngặt:

1. **Header định dạng:**
   - `TASK_KIND: EDIT` (hoặc `TASK_KIND: INVESTIGATE` nếu chỉ đọc/điều tra).
   - `FILE: <đường_dẫn_tuyệt_đối>` (CẤM dùng `TARGET_FILES:`, bắt buộc đúng token `FILE:`).

2. **Focused Test format:**
   - Bắt buộc theo mẫu: `FOCUSED_TEST: python -m pytest <path>::<node> -q` hoặc `python -m py_compile <path>`. Bất kỳ chuỗi test tự do nào khác đều bị chặn bởi `INVALID_FOCUSED_TEST_FORMAT`.

3. **Fail-Fast Instruction:**
   - Bắt buộc chứa câu lệnh Fail-Fast:
     `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về lý do.`

4. **Old String / New String Blocks:**
   - Bắt buộc bọc trong `<<< ... >>>`:
     ```text
     OLD_STRING: <<<
     old code here
     >>>

     NEW_STRING: <<<
     new code here
     >>>
     ```

5. **Sandbox & Sync giữa các máy Farm:**
   - Worker chạy trong sandbox không có quyền ghi ngoài thư mục được whitelist hoặc ghi vào `D:\OneDrive\TaadaaData`.
   - Để đồng bộ file code sang máy Admin (Admin-PC) khi Admin không git pull được: Sử dụng `D:\Taadaa\tools\sync_to_admin.py` qua SSH base64 chunking và đối soát bằng mã băm SHA256 hai đầu.
