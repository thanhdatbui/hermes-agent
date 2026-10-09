# Closeout Gate Binding Mismatch and Diff Extraction Pitfalls

## 1. Nguyên nhân lỗi `Diff is empty` & `binding mismatch` khi chạy `closeout_gate.py`

Khi thực hiện thẩm định `closeout_gate.py --repo <path>`, có 2 chế độ trích xuất diff:
1. **Chế độ Staged (trước khi commit):**
   - Áp dụng khi có file trong `git diff --cached` (staged).
   - Yêu cầu: Không được có file vừa staged vừa có unstaged edits (`set(staged) & set(dirty) == empty`).
2. **Chế độ Committed (sau khi commit):**
   - Áp dụng khi chỉ định `--base HEAD~1` (hoặc `--base <ref>`).
   - Yêu cầu nghiêm ngặt: Working tree đối với các file nằm trong commit `HEAD` **bắt buộc phải sạch 100%**!
   - Nếu bất kỳ file nào thuộc commit `HEAD` có chỉnh sửa dở dang trong working tree, `resolve_audit_binding` sẽ báo lỗi:
     `binding mismatch: staged/working-tree candidate overlaps committed HEAD`

## 2. Quy trình xử lý tự động khi gặp lỗi binding

1. **Kiểm tra trạng thái Working Tree:**
   - Chạy `git status -s` để xem các file dirty.
   - Nếu file dirty trùng với file trong `HEAD`:
     * Hoặc commit/amend toàn bộ thay đổi vào commit hiện tại.
     * Hoặc revert phần thay đổi working tree về đúng trạng thái của `HEAD` trước khi chạy gate.
2. **CẤM hỏi User chọn phương án kỹ thuật qua `clarify`:**
   - User yêu cầu chốt phiên là mong đợi tự động giải quyết dứt điểm.
   - Cấm xuất hiện hộp thoại `clarify` đề xuất user gõ lệnh tay (`git config --unset`, `git checkout`...).
   - Nếu Claude CLI rảnh, ủy quyền cho Claude CLI chạy tự động. Nếu Claude CLI bị lockout/rate limit 5h, Coordinator tự điều phối worker qua Scope Lock chuẩn để làm sạch working tree rồi chạy lại gate.
