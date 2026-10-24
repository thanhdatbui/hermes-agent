---
name: anti-whining-mechanical-gate-spec
description: Use when designing mechanical gates to prevent whining.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gate-design, anti-whining, mechanical-enforcement, invariants, closeout]
    related_skills: [farm-agent-governance, closeout-review-discipline, requesting-code-review]
---

# Anti-Whining Mechanical Gate Specification

## 1. Overview & Triết Lý Cốt Lõi

Khi một hệ thống kiểm soát (Gate/Guard) được dựng lên, nó thường mắc phải căn bệnh: **"Biến Gate thành nơi khóc lóc và trốn tránh trách nhiệm của Agent"**.
- **Khóc lóc trẻ con:** Gặp lỗi thì dừng lại, xin lỗi, viết sớ giải trình dài dòng.
- **Khóc lóc quan liêu (Nguy hiểm hơn):** Gặp lỗi thì tự gắn mác `BLOCKED`, tự mở ticket vào file json rồi báo User: *"Em đã mở ticket chờ duyệt, em dừng phiên"*.

**Nguyên tắc tối cao:**
1. Gate sinh ra là **LAN CAN BẢO VỆ (Guardrail)** trên đường cao tốc, không phải bức tường cụt. Khi xe đâm vào lan can (bị Gate chặn), điều đó có nghĩa là **HƯỚNG ĐI ĐÓ SAI**, bắt buộc phải bẻ lái quay xe (Pivot) tìm nguyên nhân gốc để sửa cho xong, CẤM tắt máy ngồi khóc.
2. CẤM TUYỆT ĐỐI viện cớ `BLOCKED` do Gate chặn để dừng việc. `BLOCKED` chỉ hợp lệ khi gặp giới hạn vật lý bất khả kháng (mất điện, cháy máy, đứt mạng, thiếu tiền tài khoản). Mọi vấn đề code, logic, timeout, regex đều BẮT BUỘC phải tự động giải quyết đến khi **DONE có bằng chứng thật**.

---

## 2. 4 Tiêu Chuẩn Bắt Buộc Khi Thiết Kế Gate Mới

Mọi Gate cơ học (pre-commit, pre-push, closeout gate, preflight runner) bắt buộc phải đáp ứng 4 tiêu chuẩn sau:

### Tiêu chuẩn 1: CẤM Veto Gate Câm — Bắt Buộc Kèm Guidance Hướng Dẫn Sửa
- Sai: Chỉ ném `exit 1` và in dòng lỗi chung chung khiến Agent không biết đi đường nào, dẫn đến đâm đầu mò mẫm.
- Đúng: Mọi Rule trong Gate bắt buộc phải có trường `guidance` (hướng dẫn kiến trúc đúng):
  + Khi DENY: In ra dòng vi phạm kèm block `HƯỚNG DẪN KIẾN TRÚC` chỉ đường cụ thể (ví dụ: *"Khi feed bị treo, kiểm tra device liveness nội bộ, TUYỆT ĐỐI KHÔNG hạ timeout micro-drop USB"*).
  + Kèm `REQUIRED_NEXT_ACTION` và lệnh `REVERT_EXACT` có sẵn file path để Agent hoàn tác ngay và bẻ lái theo hướng dẫn.

### Tiêu chuẩn 2: Auto-Quarantine O(1) Tự Động Dọn Hiện Trường
- Khi phát hiện vi phạm, Gate phải tự động cách ly hunk vi phạm qua `git stash push --keep-index -m "quarantine-<rule>-<ts>" -- <file>`.
- File mã nguồn lập tức được khôi phục về trạng thái sạch, không để working tree bẩn.

### Tiêu chuẩn 3: Strike 3 Guidance Gap — Báo Cáo Để User Chỉ Đạo Bổ Sung Guard
- Nếu Agent đã thử 3 lần mà vẫn bị chặn: Điều này chứng minh **HƯỚNG DẪN CỦA GUARD CHƯA ĐỦ ĐẦY ĐỦ/RÕ RÀNG**, khiến Agent đâm đầu vào đường cụt.
- Mục đích báo cáo User:
  1. Báo cáo cụ thể: Vấn đề cần giải quyết là gì, 3 cách Agent đã thử bị Guard chặn, và Guard đang thiếu chỉ dẫn cho kịch bản nào.
  2. Để User phân xử và ra lệnh: User chỉ đạo hướng đi mới hoặc ra lệnh cho Agent cách sửa/bổ sung lại rule và hướng dẫn trong Guard.
  3. Tư thế: Giữ repo sạch, sẵn sàng nhận lệnh mới của User để tiếp tục thi công, cấm buông xuôi đóng phiên.

### Tiêu chuẩn 4: Bộ Kiểm Thử Đối Kháng Tĩnh (Adversarial Unit Tests)
- Mọi Gate cơ giới mới bắt buộc phải có test suite đối kháng:
  + Test nhánh vi phạm: Đưa diff hạ timeout/bật tính năng cấm $\rightarrow$ Assert Gate ném lỗi DENY dứt khoát.
  + Test nhánh hợp lệ: Đưa diff an toàn $\rightarrow$ Assert Gate trả về ALLOW và cấp chữ ký HMAC/receipt.
  + Test chống lách luật: Đưa các biến thể whitespace, comment, format khác nhau $\rightarrow$ Assert Gate không bị mù hay bị lách qua mặt.

---

## 3. Checklist Nghiệm Thu Khi Tạo Gate Cơ Giới

Trước khi merge bất kỳ Gate mới nào vào codebase, bắt buộc kiểm tra:
- [ ] Gate có ném `exit 1` trần trụi không? (Nếu có $\rightarrow$ REJECT, phải bổ sung `REQUIRED_NEXT_ACTION`).
- [ ] Gate có kẽ hở nào cho phép Agent dừng lại báo `BLOCKED` không? (Nếu có $\rightarrow$ REJECT, phải chuyển thành lệnh Pivot tiếp tục thi công).
- [ ] Gate có cơ chế Auto-Quarantine dọn sạch file vi phạm chưa?
- [ ] Đã có test đối kháng chứng minh Gate chặn đứng vi phạm chưa?
- [ ] Gate đã được cắm cơ học vào pipeline thực thi (`safe_push.py` hoặc pre-push hook) chưa?
