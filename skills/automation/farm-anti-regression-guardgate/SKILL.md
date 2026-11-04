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

## 3. Quy Trình Sửa Code Tránh Bị Người Dùng Nhắc Nhở
- Trước khi thực hiện Emergency Surgery (L2) hay áp dụng bản vá:
  1. Chủ động đối soát `git log -S "<target_func>" -n 5` để nắm bối cảnh lịch sử commit cũ (đã từng fix case gì, yêu cầu gì).
  2. Bổ sung test assertion bảo vệ case cũ + case mới vào test contract.
  3. Đăng ký invariant rule vào GuardGate để khóa chặt vĩnh viễn, ngăn mọi agent tương lai sửa lùi.

## 4. Tận Dụng Comment Định Danh (Banner Bước) Làm Anchor Bất Biến
- **Không over-engineer đẻ thêm gate:** Loại bỏ các danh xưng chồng chéo (Protection Gate, Regression Gate...). Hệ thống thống nhất đúng **2 trụ cột**:
  * **Trụ 1: GuardGate (`rules.json`):** Kiểm tra tĩnh diff < 0.05s trước commit.
  * **Trụ 2: Pytest Suite:** Kiểm thử hành vi động logic nghiệp vụ.
  * **Điểm kiểm duyệt duy nhất:** `closeout_gate.py`.
- **Comment Định Danh làm Anchor Scoped:**
  * Mỗi khối logic nghiệp vụ hoặc đoạn fix bug hiểm bắt buộc có banner định danh: `# [INVARIANT: <TEN_BUG>]` hoặc `# ── BƯỚC X: ...`.
  * Rule trong `rules.json` gắn matcher theo anchor này, đảm bảo regex kiểm tra tập trung, không bị vỡ do format hay khoảng trắng ở các phần code khác.
  * Test case tương ứng trong `tests/` mock và assert đúng hành vi của bước đó.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
