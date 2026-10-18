# Kiến Trúc Thống Nhất Closeout Gate, Grace Band 80-84 & Hóa Giải Xung Đột Hệ Thống (2026-10-18)

## 1. Bản Chất 2 Căn Bệnh Đối Nghịch
1. **Bệnh Cũ (Báo DONE Láo / Fake-DONE):**
   - Trước đây `closeout_gate.py` cho điểm 80-84 in ra `[GRACE BAND APPROVED]` vô điều kiện.
   - Coordinator bám vào chữ "APPROVED" để báo DONE bừa bãi khi diff còn lớn hoặc chưa test kỹ.
2. **Bệnh Mới (Tự Ý Xóa Grace Band -> Kẹt Vòng Lặp Vô Tận):**
   - Agent tự tiện xóa bỏ ngưỡng 80đ để ép strict >= 85.
   - Hậu quả: Sol Auditor sa đà vào các nhận xét trừu tượng về AST/style/scope để trừ 1-2 điểm, khiến bài thi dù 35/35 test xanh vẫn kẹt ở 82-83 điểm, làm tê liệt toàn bộ quy trình chốt phiên.
   - User phản ứng gay gắt: Cơ chế 80đ sinh ra là để chống việc Sol đòi hỏi linh tinh khi test cơ học đã xanh.

## 2. Kiến Trúc 3 Trạng Thái Cơ Học (Mechanical State Machine)
- **STRICT_APPROVED (Score >= 85):**
  - Cấp token HMAC loại `approval_tier: strict`.
  - Coordinator được báo cáo `DONE`.
- **GRACE_APPROVED (80 <= Score < 85):**
  - BẮT BUỘC hội tụ ĐỦ 5 điều kiện cơ học cứng do Gate tự chạy:
    1. Focused test 100% PASS (0 fail, 0 error).
    2. Diff budget <= 30 dòng tổng cộng & <= 2 files (chuẩn O(1)).
    3. Không đụng Vùng cấm (hooks, closeout gate, policy files).
    4. Không có lỗi Critical / Major chưa giải quyết.
    5. Không có cờ gian lận / bypass env.
  - Cấp token HMAC loại `approval_tier: grace`.
  - Báo cáo: `DONE_WITH_GRACE` (ghi rõ điểm, test xanh, diff trong budget).
- **REJECTED (Score < 80 hoặc 80-84 nhưng thiếu điều kiện Grace):**
  - KHÔNG CẤP TOKEN.
  - Bắt buộc remediate tự động (Sol Repair -> Worker -> Strike 3 Handoff), CẤM báo DONE, CẤM dừng lại hỏi menu lựa chọn Phương án 1/2.

## 3. Bản Đồ 4 Điểm Xung Đột Đã Được Giải Quyết
1. **Tên gọi Verdict trong Audit Log:**
   - Trong `gate_audit.jsonl`, `verdict` bắt buộc giữ `"APPROVED"` để tương thích 100% với `safe_push.py`, `guard_closeout_discipline.py`, và `pre-push.sh`. Phân tầng strict/grace được lưu ở `details.grace_band` và payload token HMAC.
2. **Ngưỡng điểm Pre-push:**
   - `pre-push.sh` chuẩn hóa ngưỡng `THRESHOLD=80` để khớp với Grace Band, tránh xung đột "gate cho qua nhưng git chặn push".
3. **Chống Sol Bắt Bẻ Vụn Vặt (Anti-Nitpicking):**
   - Nhận xét AST cosmetic/style bị khống chế trần trừ điểm tối đa 3 điểm, không được phép kéo patch test xanh xuống dưới 80.
4. **Cấm Dừng Lại Khóc Lóc (Anti-Surrender):**
   - Thiếu điểm là trách nhiệm của Agent, cấm dừng lại đùn đẩy trách nhiệm cho User bằng câu hỏi menu.
