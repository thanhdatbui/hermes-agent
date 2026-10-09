# Multi-Component Broad Reconnaissance Trap & Pipelined Slices Discipline

*(Đúc kết từ sự cố kiệt quệ 32 tool calls khi thực hiện task đa thành phần: Avatar tracking trên AccountSource, StateMachine, PowerShell launcher và Excel migration ngày 06/09/2026)*

---

## 1. Hiện Tượng & Cạm Bẫy (Broad Reconnaissance Trap)

Khi nhận một task gồm nhiều thành phần liên hoàn (ví dụ: 1. Sửa helper class trong `account_source.py`, 2. Hook vào `state_machine.py`, 3. Nâng cấp launcher `run_tiktok_upload_avatar.ps1`, 4. Migration dữ liệu Excel, 5. Viết unit test):
- **Cạm bẫy:** Agent theo thói quen khảo sát toàn diện (global survey):
  - Đọc 5-6 chunk quanh `account_source.py`.
  - Mở terminal chạy python probe kiểm tra cấu trúc 6 file Excel (`Tik1..Tik6.xlsx`).
  - Mở `state_machine.py`, grep tìm `_handle_ensure_avatar_impl`, đọc 4 chunk liên tiếp.
  - Grep tiếp tìm cách ghi log `idempotency` / `jsonl`, đọc thêm 3 chunk.
  - Mở `run_tiktok_upload_avatar.ps1` đọc toàn bộ script.
  - Viết tiếp 3-4 lệnh python test logic lọc máy trên terminal.
- **Hậu quả:** Sau 30-32 tool calls, agent mới chỉ patch được đúng 1 dòng trong file đầu tiên (`CANONICAL_HEADERS`) thì đã **chạm trần ngân sách tool calls** (`max_iterations` hoặc platform limit). Toàn bộ 4 thành phần còn lại chưa hề được ghi xuống đĩa, task bị gián đoạn dở dang.

---

## 2. Kỷ Luật Thực Thi: Cắt Lát Độc Lập (Pipelined Vertical Slices)

Thay vì khảo sát toàn bộ trước khi bắt tay làm, BẮT BUỘC thực thi theo nguyên tắc **Hoàn tất dứt điểm từng thành phần (Pipelined Vertical Slice)**:

```
[Thành phần 1] Đọc hẹp (1 call) -> Patch (1 call) -> py_compile (1 call) -> XONG
       ↓
[Thành phần 2] Đọc hẹp (1 call) -> Patch (1 call) -> py_compile (1 call) -> XONG
       ↓
[Thành phần 3] Đọc/Patch script launcher -> verify cú pháp -> XONG
       ↓
[Thành phần 4] Chạy migration / focused unit test -> BÁO CÁO KẾT THÚC
```

### Nguyên tắc cụ thể:
1. **CẤM đọc trước thành phần B khi thành phần A chưa được patch & verify:**
   - Không mở `state_machine.py` hay launcher PowerShell khi `account_source.py` chưa ghi đĩa xong.
2. **Ngân sách tối đa cho mỗi thành phần: <= 3 tool calls:**
   - Call 1: `read_file` đúng 20-30 dòng nơi cần chèn code.
   - Call 2: `patch` ghi bản vá vật lý xuống đĩa.
   - Call 3: `py_compile` xác nhận không lỗi cú pháp.
3. **CẤM chạy probe simulation rộng trên terminal:**
   - Không viết các đoạn script python terminal lặp qua hàng loạt file dữ liệu để khảo sát khi thông số đã rõ ràng.
   - Chỉ test cục bộ trên 1 dữ liệu mẫu đại diện sau khi code đã được ghi đĩa.
