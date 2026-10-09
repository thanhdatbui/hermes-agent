# Case 178 (18/09/2026): Bổ Sung Test Evidence & Telemetry Kèm Git Diff Cho Sol Auditor Scorecard

## 1. Bối cảnh & Vấn đề (Sol Auditor Scorecard REJECT Vòng 1)
Trong phiên chốt thay đổi logic nghiệp vụ (điều chỉnh ngưỡng cắn đề xuất và avatar filter trên `D:/Taadaa/tools`):
- Khi gửi diff qua `python D:/Taadaa/tools/closeout_gate.py --input <diff_file>`, Sol Auditor Scorecard chấm được **76 - 82 / 100 điểm** (Threshold: >= 85) và trả về `Status: ❌ FAIL / REJECTED`.
- **Nguyên nhân chính từ Score Breakdown & Judge Notes:**
  - `Test Evidence` bị trừ nặng (10/25 -> 19/25 điểm) vì chỉ có mã nguồn test trong diff, Reviewer không thể biết test đã thực sự chạy pass hay chưa.
  - `Telemetry & Observability` thấp (10/15 điểm) do thiếu số liệu đo đạc thực tế trước và sau thay đổi để chứng minh tác động.
  - Thiếu test kiểm tra giá trị biên (boundary test) tại các ngưỡng chuyển tiếp (ví dụ: 19 vs 20 followers, 49 vs 50 hearts).

## 2. Quy chuẩn Soạn Payload Review Đạt Chuẩn Sol Scorecard (>=85đ Pass Ngay Vòng 1)
Thay vì chỉ pipe mỗi `git diff`, Coordinator cần đóng gói payload review vào một file tạm và truyền vào `closeout_gate.py --input <file>` gồm 3 phần bắt buộc:

```markdown
# TASK: <Tên tính năng / Thay đổi nghiệp vụ>

## 1. GIT DIFF:
```diff
<Toàn bộ git diff của các file liên quan>
```

## 2. TEST EXECUTION EVIDENCE:
```
<Toàn bộ output thực tế từ pytest -v, ví dụ: 11 passed in 2.21s (100% PASS)>
```

## 3. TELEMETRY & OBSERVABILITY:
- Bằng chứng kiểm chứng thực tế trên môi trường live / API / database:
  - Số liệu baseline trước khi sửa: (ví dụ: 121 / 600 nick bị false positive).
  - Số liệu thực tế sau khi sửa: (ví dụ: giảm xuống đúng 4 / 600 nick bùng nổ tương tác).
  - Kết quả curl test trực tiếp endpoint API (ví dụ: GET /api/data trên port dashboard).
  - Trạng thái các dịch vụ nền liên quan (ví dụ: service reload cleanly, 0 ảnh hưởng lock thiết bị).
```

## 3. Bài học về Unit Test Biên (Boundary Testing)
- Khi thay đổi ngưỡng điều kiện (Thresholds: `>=`, `>`, `<=`, `<`):
  - Luôn bổ sung test case riêng biệt kiểm tra đúng các cặp giá trị sát biên:
    * `threshold - 1` -> kỳ vọng `False`.
    * `threshold` -> kỳ vọng `True` (hit lower boundary).
    * Kết hợp 2 điều kiện OR: cả hai cùng dưới ngưỡng -> kỳ vọng `False`.
- Việc bổ sung test biên đẩy điểm `Logic Correctness` từ 28/35 lên 33/35 và `Test Evidence` từ 10/25 lên 23/25, giúp tổng điểm đạt **89/100 (APPROVED)** ngay lập tức.
