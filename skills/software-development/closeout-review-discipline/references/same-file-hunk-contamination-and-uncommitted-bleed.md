# Same-File Hunk Contamination & Uncommitted Bleed in Closeout Gate

## Incident & Failure Signature (06/10/2026)
- **Triệu chứng:** Coordinator chạy `closeout_gate.py` với cờ scoped `--files` hoặc `--target-file` chỉ định đúng 2 file của task, nhưng Reviewer Sol Web / OmniRoute chấm điểm thấp bất ngờ (70/100, REJECTED).
- **Phản biện vô lý của Reviewer:** Nhận xét trừ điểm nặng nề về các hàm, kiến trúc, cấu hình hoặc hạ tầng (ví dụ: `admin_machine >= 200`, `config-admin.yaml`, `ssh admin-farm`, thiếu integration tests cho admin cluster) mà task hiện tại **hoàn toàn không đụng tới**.
- **Cạm bẫy:** Coordinator nhầm tưởng Reviewer "quét rác cả repo", nhưng thực chất diff gửi đi đã chứa toàn bộ các hunk đó.

## Root Cause Kỹ Thuật Trong `closeout_gate.py`
1. **File-Level vs Hunk-Level Extraction:**
   Hàm `targeted_candidate()` trong `closeout_gate.py` trích xuất diff uncommitted bằng lệnh:
   ```bash
   git diff HEAD -- <target_file_1> <target_file_2>
   ```
   Lệnh này cô lập theo **đường dẫn file (path-level)**, hoàn toàn **KHÔNG phân biệt hunk/ownership** bên trong cùng một file.
2. **Kế thừa dirty hunk từ phiên trước:**
   Nếu target file đã có sẵn các hunk sửa đổi dở dang từ worker/session trước (chưa commit), toàn bộ các hunk đó sẽ bị gom chung vào diff candidate (ví dụ đẩy diff từ 3KB lên 27.5KB), làm nhiễm độc payload gửi cho AI Reviewer.

## Quy Trình Xử Lý & Phòng Ngừa (Hygiene Protocol)
1. **Kiểm tra hunk trước khi Closeout:**
   Trước khi chạy gate trên working tree, bắt buộc kiểm tra xem target file có bị lẫn hunk lạ không:
   ```bash
   git diff HEAD -- <target_file> | grep -E '^\+[^+]|^\-[^-]'
   ```
   Nếu thấy các hunk không thuộc scope task hiện tại, TUYỆT ĐỐI CẤM chạy `closeout_gate.py` ở chế độ worktree.
2. **Cô lập bằng Focused Commit:**
   Khi target file bị nhiễm dirty hunk cũ mà không thể revert bừa (tránh vi phạm invariant bảo vệ dirty state của farm):
   - Commit riêng phần thay đổi sạch của task hiện tại với commit message chuẩn (`[L2-surgery]` hoặc semantic commit message).
   - Chạy `closeout_gate.py` ở chế độ committed diff:
     ```bash
     python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --target-file <file1> <file2> --json-output
     ```
   - Chế độ committed diff sẽ chỉ trích xuất đúng những gì thuộc commit vừa tạo (`git diff HEAD~1..HEAD -- <targets>`), triệt tiêu 100% rác uncommitted còn lại trong file.
3. **Cấm sửa code chiều theo nhận xét do nhiễm scope:**
   Khi Reviewer trừ điểm vì các hunk ngoài task, CẤM Coordinator vội vã thêm test hay sửa code production cho các hunk đó (làm phình to scope và sai lệch kiến trúc). Phải lập tức cô lập lại diff candidate về đúng contract của task.
