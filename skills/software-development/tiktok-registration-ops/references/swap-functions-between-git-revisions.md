# Swap functions between git revisions (giữ fix, bỏ phần hỏng)

## Tình huống
Một commit "gói" nhiều thay đổi (commit 1328de2 "UI capture timeout 60s" thay đổi
2377 dòng: timeout + DOB wheel mới + fail-cứng + overlay). Revert cả commit sẽ mất
cả fix tốt. User yêu cầu: "bản mới kéo DOB ngu thì dùng lại bản cũ đi" — chỉ hoán
đổi phần hỏng về bản cũ, giữ nguyên các fix khác (vd fix CDP OTP order).

## Cách làm (AST-based, an toàn với file lớn ~11k dòng)

Dùng `python` + `ast` để:
1. Parse `current file` và bản cũ `git show <rev>:<file>`.
2. Liệt kê top-level functions theo predicate (vd tên chứa "dob"/"birthday").
3. Xóa các hàm top-level hiện tại theo dòng (xóa từ cuối file ngược lên để không
   lệch line number).
4. Chèn khối hàm bản cũ (theo thứ tự dòng trong bản cũ) trước 1 marker function
   còn tồn tại (vd `def extract_otp_from_xml`) hoặc cuối file.
5. `ast.parse` verify syntax; `grep` verify không còn tham chiếu hàm bị xóa;
   chạy pytest cho test liên quan.

## Pitfalls
- Chỉ thay **top-level** functions: `ast.walk` bắt cả hàm lồng (vd
  `_read_dob_parsed` nằm trong `fill_birthday` cũ) — lọc bằng `tree.body` chỉ,
  hoặc hàm lồng sẽ `KeyError` khi tìm theo top-level. Bỏ qua helper lồng (chúng
  đi kèm parent function).
- Hàm chỉ tồn tại ở bản MỚI nhưng được dùng ở **chỗ khác** (vd
  `_is_tiktok_dob_picker_surface_xml` dùng ở recovery path dòng ~11661) → phải
  khôi phục lại, đừng xóa theo predicate mù.
- Test đang kỳ vọng API mới sẽ fail sau khi swap — đó là dấu hiệu đúng hướng
  (test mô tả cơ chế cũ giờ đã hết), kiểm tra test đó có tồn tại ở bản cũ không:
  `git show <rev>:tests/<file>`.
- Dùng `git checkout <rev> -- <file>` để revert cả file nếu cách swap AST quá
  rủi ro — nhưng sẽ mất fix khác; chỉ khi user chấp nhận.

## Verify sau khi swap
```bash
python -c "import ast; ast.parse(open('social_reg_v1.py', encoding='utf-8').read())"
grep -c '<func_moi>' social_reg_v1.py   # 0 tham chiếu còn sót
grep -n 'for code in candidates:' social_reg_v1.py  # fix CDP còn nguyên
```