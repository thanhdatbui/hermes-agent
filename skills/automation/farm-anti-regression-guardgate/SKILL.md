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

### 3.1. Bẫy Test Assertion Sửa Lùi (Weak Contract Regression Trap - Vụ Án Commit 82d50a4)
- **Triệu chứng nhận diện:** Một invariant đã từng được chốt (như quy tắc trừ nhả follow ngày 03/10/2026: nhả liền `cnt == 0` thì trừ sạch follow tự nhiên `reported = 0`, nhưng đã có `cnt > 0` thì giữ nguyên các lượt thành công `reported = cnt + natural_cnt`) bị Agent ở session sau sửa lùi vì Agent đó chỉ tập trung vào một ca lẻ phát sinh (như M41 `cnt == 1`), tự tiện đổi thành `reset = failed` rồi **sửa đè cả assert trong file test** để test xanh.
- **Kỷ luật phòng chống:**
  * **Test Contract 2 Nhánh Bắt Buộc:** Mọi logic phân nhánh điều kiện biên (`cnt == 0` vs `cnt > 0`) BẮT BUỘC phải có đồng thời 2 test cases đối trọng trong test suite:
    1. Nhánh Nhả Liền: `failed=True, cnt=0, natural_cnt=2` ➔ `assert reported == 0`.
    2. Nhánh Thành Công Trước Nhả: `failed=True, cnt=3, natural_cnt=2` ➔ `assert reported == 5`.
  * **Cấm Sửa Lùi Test Assertion:** Khi viết/sửa code, nếu thấy test contract cũ FAIL, Agent BẮT BUỘC phải tra cứu lại commit history (`git log -S`) để hiểu vì sao test đó tồn tại trước khi tự ý sửa assert của test. Sửa assert để test pass mù quáng là hành vi phá vỡ invariant nghiêm trọng.

## 4. Bãi Bỏ Đánh Giá Cảm Tính & Quy Chuẩn Đóng Phiên Closeout v2
- Xem chi tiết tại [Closeout v2 Mechanical Enforcement & Zero-Score-Chasing](references/closeout-v2-mechanical-enforcement.md).
- **CẤM TUYỆT ĐỐI đòi điểm reviewer >= 85 hoặc in mẫu báo cáo điểm số**: Cơ chế thẩm định cảm tính điểm số đã bãi bỏ 100%, người gác cổng duy nhất là `closeout_v2.py` (GuardGate + Pytest Exit 0 = APPROVED 100/100).
- **Khai tử thói quen rập khuôn**: Khi chốt phiên (`done`, `chốt phiên`), chỉ báo cáo kết quả kiểm định máy `closeout_v2.py` (Exit code 0, GuardGate PASS, Pytest PASS), cấm lôi các câu chữ di tích cũ về "Reviewer chấm >= 85" làm phiền User.
- **Zero Artifacts & Memory Hygiene**: Dọn sạch file rác qua `safe_recycle.py`, cấm đẻ persistent memory bừa bãi khi được bảo dọn dẹp.
- **Smart Action Mandate vs Regex Trap**: Quy chuẩn cơ giới hóa O(1) tách bạch Execution Signals vs Consultative Markers trong `conversation_loop.py`, triệt tiêu bẫy regex chặn họng khi đối thoại/tư vấn xem tại `references/smart-action-mandate-and-consultative-bypass-20261104.md`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
