# Case 178 (18/09/2026): Sol Auditor Reviewer Scorecard Pass Requirements & Bypassing Diff-Only Rejections

## 1. Triệu chứng & Vấn đề
Khi chạy closeout gate sử dụng Sol Auditor Scorecard (`D:/Taadaa/tools/closeout_gate.py` gọi OmniRoute :20129 model `review`):
- Model `review` áp dụng rubric 100 điểm với ngưỡng duyệt tối thiểu `>= 85đ`.
- Mặc dù code diff hoàn toàn chính xác về mặt logic, nếu chỉ truyền git diff thuần túy vào closeout gate (`git diff ... | python closeout_gate.py --input -`), reviewer thường chấm ở mức **76 - 82 điểm** và **REJECT** vì:
  1. **Test Evidence (10-19/25đ):** Reviewer chỉ nhìn thấy code test được sửa/thêm trong diff nhưng *không thấy bằng chứng thực tế test execution output*.
  2. **Telemetry & Observability (10-13/15đ):** Không có số liệu đo lường thực tế trước và sau thay đổi (ví dụ: số lượng false positive giảm từ bao nhiêu xuống bao nhiêu).
  3. **Boundary Test Missing:** Thiếu test bao phủ chính xác các giá trị biên (ví dụ: đổi threshold sang `follower >= 20` hoặc `heart >= 50` nhưng không test tại 19/20 và 49/50).

## 2. Quy trình & Giải pháp Vượt Gate Đạt Scorecard >= 85đ (Thực tế đạt 89đ)

### Bước 1: Bổ sung Test Biên (Boundary Coverage)
Khi sửa đổi bất kỳ ngưỡng số nào (threshold/limit):
- BẮT BUỘC viết unit test bao phủ đúng các điểm lân cận:
  - Dưới ngưỡng (sub-threshold): `val - 1` -> kết quả `False`.
  - Đạt ngưỡng (threshold hit): `val` -> kết quả `True`.
  - Cả 2 biến cùng sát dưới ngưỡng -> kết quả `False`.

### Bước 2: Đóng gói Payload Đầy Đủ 3 Phần Gửi Vào Closeout Gate
Thay vì chỉ gửi diff thô, đóng gói file payload tạm chứa:
```markdown
# TASK: <Tên công việc / Thay đổi>

## 1. GIT DIFF:
```diff
<kết quả git diff thực tế>
```

## 2. TEST EXECUTION EVIDENCE:
```
<kết quả pytest -v thực tế chạy trên repo với toàn bộ test PASSED>
```

## 3. TELEMETRY & OBSERVABILITY:
- Live Farm Verification (API/Database/Log):
  - Baseline trước khi sửa: X items (Y% false positive)
  - Sau khi sửa: Z items (chính xác Z accounts)
  - Danh sách tài khoản thực tế được gắn cờ / tác động
- Zero impact to farm runtime or device locks.
```

### Bước 3: Thực thi Closeout Gate với `--input payload_file`
Chạy lệnh:
```bash
python D:/Taadaa/tools/closeout_gate.py --input <path_to_payload_file>
```
Kết quả Sol Auditor Scorecard:
- Logic Correctness: 33/35
- Test Evidence: 23/25
- Telemetry & Obs: 13/15
- Tổng điểm: **89 / 100đ (APPROVED / PASS)**.

### Bước 4: Clean Up File Tạm & Commit/Push
- Xóa sạch file payload tạm sau khi duyệt.
- `git add <allowed_files> && git commit -m "..." && git push origin <branch>`.
