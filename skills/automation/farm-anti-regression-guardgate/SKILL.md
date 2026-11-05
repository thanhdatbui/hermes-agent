---
name: farm-anti-regression-guardgate
description: "Kỷ luật đóng băng bất biến (Invariant Freeze) bằng GuardGate và chống regression commit history trên toàn farm Taadaa."
---
# Farm Anti-Regression & GuardGate Invariant Discipline

## 1. Nguyên Tắc Cốt Lõi: Hàng Rào Cơ Học Thay Vì Trí Nhớ Bằng Lời
- **Không trông chờ trí nhớ văn bản:** Không thể kỳ vọng Agent "đọc git log rồi tự nhớ để không sửa ngược". Mọi bản vá sửa chữa lỗi hệ thống/layout cũ bắt buộc phải được đóng băng cơ học qua **GuardGate (`rules.json`)** và **Focused Contract Tests (pytest)**.
- **Tiêu chuẩn $O(1)$:** Cấm quét toàn bộ cây git log / blame thời gian thực trong runtime vì $O(C \times L)$ gây phình context và timeout phiên. GuardGate chỉ đối soát regex trên chính file diff thay đổi ($< 0.1\text{s}$).

## 2. Quy Chuẩn Đóng Băng Rule Vào GuardGate
Khi một lỗi lặp lại hoặc lỗi bẫy selector/fallback được sửa xong (ví dụ Bento Switcher):
1. **Khóa Regex Bất Biến:** Thêm rule vào `rules.json` của repo tương ứng (hoặc `tools/guardgate/rules.json` nếu dùng chung toàn farm):
   - Scope: Đúng repo và file mục tiêu (`paths: ["gmail_reg_v10.py"]`).
   - Match: `{"tool_class": "code_edit", "op": "commit"}`.
   - Vectors: Cung cấp cặp vector kiểm chứng mẫu (`ALLOW` vs `DENY`).
   - On-deny: Chuyển hướng `sol_repair` với `strike_class: "regression_known_incident"`.
2. **Kiểm Tra Ký Số Receipt:**
   - Chạy `python D:/Taadaa/tools/guardgate/runner.py --repo <repo> --base HEAD~1` để kiểm tra diff hiện tại.
   - Bắt buộc trả về `[GuardEngine ALLOW]` và cấp signed receipt mới được phép đóng phiên / push code qua `safe_push.py`.
3. **Chống Thao Túng Test (Specification Tampering):**
   - Xem chi tiết tại [Test Mutation & Dual-Run Baseline Check](references/test-mutation-tampering-and-dual-run-baseline-check.md).
   - Agent cấm sửa dòng assert có sẵn trong unit test cũ để đối phó; Closeout Gate cơ giới hóa chạy Dual-Run test suite từ `base` commit trước khi cho phép merge.

- Kỷ luật cấu trúc Step-by-step & Khắc phục bẫy bại liệt báo pin %: `skill_view(name='farm-anti-regression-guardgate', file_path='references/guardgate-step-by-step-structure-and-closeout-discipline-20261105.md')`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
