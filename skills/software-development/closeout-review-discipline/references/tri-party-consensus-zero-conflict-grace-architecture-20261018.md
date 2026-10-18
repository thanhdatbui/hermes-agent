# Tri-Party Consensus: Zero-Conflict Grace Band Architecture (2026-10-18)

## 1. Bối Cảnh Lịch Sử & Xung Đột
- **Sự cố:** Khi cố gắng loại bỏ hiện tượng Coordinator "báo DONE ảo / trốn việc" bằng cách xóa bỏ hoàn toàn Grace Band (ép cứng `strict >= 85`), hệ thống lập tức rơi vào bệnh lý đối nghịch: Sol Auditor sa đà vào các nhận xét trừu tượng về AST/Scope để trừ điểm lặt vặt (82-83 điểm), giam lỏng Agent trong vòng lặp sửa code vô tận dù 35/35 test đã xanh 100%.
- **Bản chất xung đột:** Các thành phần trong hệ sinh thái (`closeout_gate.py`, `safe_push.py`, `pre-push.sh`, `guard_closeout_discipline.py`) mỗi nơi tự viết lại logic kiểm tra số `85` hay `80` bằng regex/if-else riêng, dẫn đến tình trạng "cổng trước cho qua, cổng sau chặn đứng" hoặc gãy toàn bộ bộ test cũ.

## 2. Ba Nguyên Tắc Đồng Thuận (Consensus Principles)
1. **Strict 85 Là Quality Gate Mặc Định:** Điểm 80-84 không tự động trở thành đạt chuẩn; nó thuộc nhánh `CONDITIONAL_PASS` (Grace), chỉ mở khi hội đủ 5 điều kiện cơ học.
2. **Đơn Nguồn Chân Lý (Single Source of Truth):**
   - **DUY NHẤT** `gate_common.py` và `closeout_policy.json` được quyền chứa các con số 85, 80 và logic so sánh ngưỡng.
   - `safe_push.py`, `pre-push.sh`, và `guard_closeout_discipline.py` bị CẤM so sánh số hoặc regex thủ công; bắt buộc gọi `gate_common.verify(head, caller=...)`.
3. **Bảo Toàn Tương Thích Ngược & Chống DONE Ảo Bằng Token Ký Số:**
   - Trong `gate_audit.jsonl`, giữ nguyên `verdict: "APPROVED"` để downstream tools không bị sập.
   - Phân tầng được lưu trong `approval_tier: "strict" | "grace"` và token HMAC ký số gắn chặt với `git patch-id`.
   - Coordinator chỉ được báo `DONE` khi có token `strict`; nếu token là `grace`, bắt buộc báo cáo minh bạch `DONE_WITH_GRACE`.

## 3. Khóa Chặn Sol Bắt Bẻ Vụn Vặt (Anti-Nitpicking Invariant)
- **Capped Deductions:** Nhận xét về style hoặc AST pedantry chỉ được trừ tối đa 3 điểm, không được phép kéo patch test xanh xuống dưới 80.
- **No Goalpost Moving:** Sau vòng 1, Sol cấm bắt lỗi mới trên code không đổi trừ khi là lỗi Critical/Major do remediation gây ra.
- **Round Cap = 3:** Sau 3 vòng không có critical finding và điểm ổn định 80-84, Gate tự động thẩm định 5 điều kiện cơ học để cấp `GRACE_APPROVED`, cấm giam lỏng Agent.
