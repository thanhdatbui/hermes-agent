# Nghiệm Thu Độc Lập File Mục Tiêu & Chống Bại Liệt Khi Repo Dirty (Target-File Closeout & Dirty-Repo Unblock)

**Ngày cập nhật:** 2026-10-04  
**Chỉ thị từ Sếp (Operator Mandate):** "Là sao t điên lắm r đó sao cứ blocked suốt ngày v" / "gọi claude cli thiết kế lại gate để k bị blocked nữa, xong xuôi mày vào làm nốt task".

---

## 1. Bản Chất Vấn Đề: Bẫy "Binding Mismatch" & Tê Liệt Do Repo Dirty
- **Hiện tượng:** Trong môi trường Farm hoặc các repo chạy tự động đa phiên (như `D:/Taadaa/GPM auto`, `register gmail`), thường xuyên tồn đọng các file dirty (`M scripts/...`, `?? checkmail_...`) từ các phiên làm việc trước đó chưa được commit.
- **Hậu quả:** Khi chạy Closeout Gate mặc định (`python D:/Taadaa/tools/closeout_gate.py --repo <path>`), gate gom toàn bộ working tree:
  1. Gây lỗi `binding mismatch: staged/working-tree candidate overlaps committed HEAD`.
  2. Diff phình to hàng trăm nghìn ký tự, vượt hạn mức nén của `SolPayloadGuard`.
  3. Coordinator bị rơi vào trạng thái tê liệt (Luna/Gemini freeze), liên tục báo "BLOCKED" làm User cực kỳ ức chế.

---

## 2. Giải Pháp Chuẩn Hóa: Cơ Chế `--target-file` / `--files` Trong `closeout_gate.py`
Đã nâng cấp `D:/Taadaa/tools/closeout_gate.py` hỗ trợ trích xuất diff cô lập theo danh sách file mục tiêu:
```bash
python D:/Taadaa/tools/closeout_gate.py --repo "D:/Taadaa/GPM auto" --files scripts/preflight_s7_rolling_cleanup.py tests/test_closeout_gates.py --json-output
```
- **Nguyên lý hoạt động:**
  1. Chuyển đổi toàn bộ đường dẫn sang relative path chuẩn trong repo.
  2. Bỏ qua hoàn toàn các file dirty và untracked khác trong working tree.
  3. Chỉ trích xuất diff của các file được liệt kê:
     - Nếu có staged: chỉ chấp nhận khi các staged file trùng khớp với danh sách file chỉ định.
     - Nếu chưa staged: trích xuất diff giữa working tree và HEAD của riêng các file đó.
  4. Tính toán và lưu trữ `staged_diff_sha256` chính xác cho diff cô lập để vượt qua Commit Guard downstream.

---

## 3. Bẫy Line Endings (CRLF vs LF) Làm Phình To Git Diff
- **Hiện tượng:** Trên Windows, khi tool chỉnh sửa file vô tình chuyển đổi line endings từ LF sang CRLF (hoặc ngược lại):
  - Lệnh `git diff` sẽ coi toàn bộ file (ví dụ 467 dòng) là bị xóa và tạo lại (+467/-466 dòng).
  - Sol Reviewer nhìn thấy toàn bộ file bị thay đổi sẽ đánh giá là "thiếu an toàn, rủi ro regression cao, monolith rewrite" và trừ điểm nặng (điểm < 85/100).
- **Cách khắc phục bắt buộc:**
  - Kiểm tra `git diff --numstat` trước khi chạy Gate. Nếu một sửa đổi nhỏ vài dòng lại báo hàng trăm dòng, chắc chắn bị lệch line endings.
  - Chuyển đổi định dạng file về đúng chuẩn LF gốc của repo trước khi kích hoạt `closeout_gate.py`.

---

## 4. Chiến Lược Đạt Điểm Cao Rubric Sol Reviewer (>= 85/100)
- **Điểm Test Evidence (25đ):**
  - Chạy regression test pass 100% chỉ là điều kiện cần (chứng minh hệ thống không vỡ).
  - Để đạt điểm tối đa ($\ge 23/25$), BẮT BUỘC phải có **focused mock unit test** kiểm tra trực diện tính năng mới:
    - Giá trị mặc định (Default fallback).
    - Biến môi trường ghi đè động (Dynamic env override).
    - Các ca kiểm thử biên (Boundary conditions: dưới ngưỡng $\rightarrow$ OK; tại ngưỡng $\rightarrow$ kích hoạt Safety Gates).
    - Các nhánh bảo vệ an toàn (Ưu tiên tài khoản GPM Live, bảo vệ TikTok-bound).
- **Tự động điều phối Claude Code CLI:** Khi cần thiết kế lại tool gate hoặc bổ sung nhanh bộ test mock bao phủ các biên phức tạp, Coordinator chủ động gọi `claude -p "..."` thực thi dứt điểm thay vì dừng lại báo BLOCKED.
