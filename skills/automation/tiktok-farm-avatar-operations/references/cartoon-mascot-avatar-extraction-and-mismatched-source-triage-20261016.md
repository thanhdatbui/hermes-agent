# Cartoon Mascot Avatar Extraction & Mismatched Source Triage (2026-10-16)

## 1. Mismatched Source vs Render Folder Triage ($F_{src}$ vs $F_{out}$)
Khi nhận diện một tài khoản cần chuẩn hoá 3 món (Ava - Hashtag - Pin):
- **Hiện tượng lệch kho nguồn:**
  - `TaiKhoan` sheet trong workbook (ví dụ `Tik5.xlsx` dòng 59): $F_{out} = 461$, $F_{src} = 378$.
  - Cả `D:/video goc/378` (video xe tải) và `D:/video goc/461` (video Arduino / BánLinhKiện) đều không khớp với nội dung thực tế trên lưới TikTok.
  - Tuy nhiên, kho video render `D:/TIKTOK-videonuoinick/461` lại chứa chính xác các video hoạt hình cartoon 2D (series Bò và Gấu / Học Viện Bò và Gấu) đã được đăng tải lên nick.
- **Quy tắc trích xuất khi $F_{src}$ lệch:**
  - Khi $F_{src}$ không khớp với nội dung thực tế hiển thị trên kênh, BẮT BUỘC kiểm tra trực tiếp kho video render $F_{out}$ (`D:/TIKTOK-videonuoinick/<id>`).
  - Trích xuất nhân vật đại diện trực tiếp từ các file video trong $F_{out}$ để đảm bảo avatar đồng nhất 100% với video trên kênh.

## 2. Tiêu Chuẩn Trích Xuất Avatar Nhân Vật Hoạt Hình / Linh Vật (Cartoon / Mascot)
- **Bảo toàn Sừng & Tai tròn (Horns & Ears Invariant):**
  - Các nhân vật mascot (như Chú Bò có sừng, Chú Gấu có tai tròn vểnh) rất dễ bị crop lẹm sừng hoặc cụt tai khi người làm chỉ căn tâm mặt.
  - Vùng crop vuông ($512 \times 512$) bắt buộc phải có khoảng đệm an toàn (headroom) phía trên đỉnh đầu $\ge 15\%$ chiều cao khung hình để khi áp mask tròn TikTok, vành tròn không cắt phạm vào chóp sừng hay vành tai.
- **Lọc sạch nhân vật phụ (Single Subject Isolation):**
  - Trong các khung hình đối thoại 2 nhân vật (Bò & Gấu, Countryballs), việc crop cận mặt nhân vật chính dễ dính một phần sừng, tai, tay hoặc bóng của nhân vật phụ ở mép.
  - Phải kiểm định qua Vision / OCR để đảm bảo mép ảnh đã sạch hoàn toàn (clean background), không để sót bộ phận cơ thể của nhân vật thứ hai.

## 3. Coordinator Delegation & Guard Constraints
- **Ngân sách T1 Guard:**
  - Coordinator session có ngân sách ghi file nghiêm ngặt (tối đa 5 files, $\le 200$ dòng code cộng dồn). Vượt quá ngưỡng này sẽ bị `COORDINATOR WRITE DENIED`.
  - Khi hết ngân sách T1, BẮT BUỘC ủy quyền qua `delegate_task` cho worker.
- **Quy chuẩn `FOCUSED_TEST` trong `delegate_task`:**
  - Guard bắt buộc `FOCUSED_TEST` phải tuân thủ đúng định dạng:
    * `python -m py_compile <file.py>` (đối với script standalone hoặc syntax check)
    * `python -m pytest <file.py>::<test_node> -q` (đối với test logic)
  - CẤM truyền lệnh dạng `python <file.py>` vì sẽ bị `INVALID_FOCUSED_TEST_FORMAT` từ chối ngay lập tức.
- **Terminal Null Character Trap (MSYS / Git Bash):**
  - Trên Windows MSYS terminal, truyền các lệnh `python -c` chứa chuỗi nhiều dòng có ký tự đặc biệt có thể kích hoạt lỗi `ValueError: open: embedded null character in path` trong lifecycle guard.
  - Luôn sử dụng lệnh Python 1 dòng (one-liner) hoặc viết ra file script nhỏ để thực thi an toàn.
