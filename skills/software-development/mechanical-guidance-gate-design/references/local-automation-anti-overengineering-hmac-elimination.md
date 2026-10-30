# Local Automation Anti-Overengineering: HMAC Debt Elimination & Reviewer Threat Model Alignment

## 1. Context & Anti-Pattern (The HMAC Illusion on Single-Host Automation)
Trong các quy trình tự động hóa cục bộ (Hermes Coordinator, Workers, Scripts cùng chạy trên một máy tính Windows dưới cùng một user OS `Kibe`):
- **Triệu chứng Over-Engineering:** Tự sinh key bí mật trên đĩa (`pipeline.key`, `hmac.key`, `vision_guard.key`), dùng `hmac.new(..., hashlib.sha256)` để ký `state.json` hoặc receipts, rồi từ chối chạy khi chữ ký không khớp.
- **Bản chất sai lầm (Security Theater):**
  > "HMAC không phải là bảo mật nếu người tạo chữ ký, người giữ key và người có quyền sửa dữ liệu đều nằm trong cùng một trust boundary (cùng user Kibe, cùng process space)."
  - Nếu một tiến trình/worker có quyền sửa file thì cũng có toàn quyền đọc key hoặc ghi đè chữ ký mới.
  - Hậu quả: Code phình to hàng trăm dòng, dễ đứt gãy do mất key/lệch encoding/CRLF trên Windows, tạo ra các điểm nghẽn giả tạo.

## 2. Chuẩn Thay Thế Thực Chiến: TLIS v1 (Taadaa Local Integrity Standard)
Thay vì dùng HMAC/chữ ký nhị phân, bảo vệ toàn vẹn local bằng 4 cơ chế cơ học chuẩn xác:
1. **Plain JSON minh bạch:** Lưu state rõ ràng (`run_id`, `status`, `target_files`), người và bot đều đọc/debug được bằng mắt thường.
2. **Atomic Write (`os.replace`):** Ghi nội dung ra file tạm `<name>.tmp.<pid>` cùng thư mục rồi gọi `os.replace` sang file đích. Chống hỏng state khi tiến trình crash hay mất điện.
3. **OS-Level Locking (`msvcrt.locking` trên Windows / `fcntl.flock` trên POSIX):** Chống 2 tiến trình worker/pipeline chạy đồng thời ghi đè lên cùng repo (`RepoLock`).
4. **Git Tracking & Index Hygiene:**
   - Dùng `git status --porcelain` và snapshot SHA256 content thật của file baseline ngoài scope để phát hiện sửa lén.
   - Khi rollback (`full_rollback`): bắt buộc unstage Git index (`git reset HEAD --`) để dọn sạch nếu worker lỡ `git add`, bảo đảm không để lại repo dirty.

## 3. Khắc Phục Lệch Pha Đánh Giá Của Reviewer (LLM Threat Model Drift)
Khi dùng LLM độc lập (Claude CLI / Sol High) để review/chấm điểm code (`run_claude_oneshot.py` / `closeout_gate.py`):
- **Hiện tượng:** Reviewer trừ điểm nặng (kẹt ở 50–70 điểm) vì đòi hỏi các biện pháp phòng thủ cấp Enterprise chống hacker có chủ đích (vd: đòi quét cả file trong `.gitignore`, kiểm tra nhị phân ảnh, cấm decode UTF-8 lỗi, nghi ngờ chính Planner sửa trộm file).
- **Kỷ luật xử lý:**
  1. Phân biệt rõ **Lỗi logic thực tế** (vd: thiếu unstage git index khi rollback, thiếu kiểm tra magic bytes khiến file rác giả ảnh vượt Gate 6) $\rightarrow$ BẮT BUỘC SỬA TRIỆT ĐỂ.
  2. Các yêu cầu **Paranoid Threat Model** không thuộc ngữ cảnh Phone Farm (vd: đòi HMAC bí mật trên máy local) $\rightarrow$ CƯƠNG QUYẾT BÁC BỎ, giải trình minh bạch cho Operator thay vì lén nhét lại over-engineering vào code để "lấy điểm đối phó".
