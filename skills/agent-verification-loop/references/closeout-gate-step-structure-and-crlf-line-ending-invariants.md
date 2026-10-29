# Closeout Gate Step Structure & Windows CRLF Invariants

## 1. Quy tắc `case_invariant_require_step_by_step_structure`
- **Predicate Trigger:** Trong git diff của bất kỳ file `.py` nào có `code_lines >= 15` (không tính comment, import, docstring), GuardEngine bắt buộc phải tìm thấy comment định danh bước khớp với regex:
  `#.*(buoc|bước|step|phase|stage|checkpoint)|#\s*={3,}` (không phân biệt hoa thường).
- **Hành vi thất bại:** Nếu vi phạm, GuardGate chặn Closeout Pipeline với mã lỗi `predicate_failed:check_step_by_step_structure` và từ chối merge.
- **Biện pháp khắc phục O(1):**
  * Trong mọi file Python mới hoặc được sửa đổi có khối lệnh dài hơn 15 dòng, luôn chèn comment định danh bước rõ ràng trước các khối logic chính, ví dụ:
    ```python
    # Bước 1: Khởi tạo dữ liệu và đọc cấu hình
    ...
    # Bước 2: Thực thi kiểm tra hoặc biến đổi logic
    ...
    # Bước 3: Ghi nhận kết quả và xác nhận nghiệm thu
    ```

## 2. Kỷ Luật Line Ending (CRLF vs LF) Trên Windows Chống `DIFF_TOO_LARGE`
- **Nguyên nhân cốt lõi:**
  * Trên Windows, `git config core.autocrlf` thường được đặt là `true`.
  * Nếu một file trong repo ban đầu có line ending CRLF (`\r\n`), nhưng qua quá trình sửa bằng tool hoặc script Python nó bị ghi đè thành LF (`\n`) (hoặc ngược lại), Git sẽ coi *toàn bộ file* (hàng nghìn dòng) là bị thay đổi.
  * Hậu quả: `git diff --cached` phình to bất thường (> 100KB), kích hoạt Fail-Fast Gate:
    `[Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (> 30000 bytes)`.
- **Kỹ thuật chẩn đoán & khắc phục O(1):**
  1. **Chẩn đoán:** Chạy `git diff --cached -w --stat` (bỏ qua whitespace/EOL) so sánh với `git diff --cached --stat`. Nếu phiên bản `-w` chỉ đổi 5-10 dòng nhưng bản thường đổi 1000+ dòng, chắc chắn do lệch CRLF/LF.
  2. **Khắc phục:** Đọc line ending gốc từ Git HEAD (`git show HEAD:<path>`) và chuẩn hóa file trên disk về cùng kiểu kết thúc dòng trước khi `git add`.
