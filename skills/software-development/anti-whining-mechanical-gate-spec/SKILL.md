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

### Tiêu chuẩn 1: CẤM Veto Gate Câm (`exit 1` không lệnh hành động)
- **Sai:** `if error: print("Lỗi vi phạm invariant X") ; sys.exit(1)` (khiến Agent ở phiên sau bối rối và bắt đầu thanh minh).
- **Đúng:** Mọi thông báo `DENY` bắt buộc phải kèm theo block mệnh lệnh đóng `REQUIRED_NEXT_ACTION`:
  + Điền sẵn file path và lệnh cụ thể để copy-paste thực thi ngay (ví dụ: `git checkout -- "<file>"`).
  + Không để khoảng trống nhận thức để Agent viết văn giải thích hay xin lỗi.

### Tiêu chuẩn 2: Auto-Quarantine $O(1)$ Tự Động Dọn Hiện Trường
- Khi phát hiện vi phạm, Gate phải có cơ chế tự động cách ly hunk vi phạm (ưu tiên dùng `git stash push --keep-index -m "quarantine-<rule>-<ts>" -- <file>`).
- File mã nguồn lập tức được khôi phục về trạng thái sạch, không để working tree bẩn khiến các bước sau bị tắc nghẽn.

### Tiêu chuẩn 3: Strike 3 Chạm Trần Thẩm Quyền — Báo Cáo User Nhận Chỉ Thị
- Tuyệt đối không mở ticket vu vơ rồi ngồi chờ. CẤM đâm đầu vào tường đốt token.
- Vì Agent bị cấm tự sửa Guard, lúc này việc báo User là HỢP LỆ VÀ BẮT BUỘC:
  1. Tóm tắt 3 phương án đã thử và diff cụ thể bị Guard chặn.
  2. Nêu rõ điểm nghẽn để User phân xử:
     - (A) Nếu Guard chặn sai/quá đà: User can thiệp sửa Guard.
     - (B) Nếu Guard đúng: User ra lệnh định hướng nghiệp vụ mới ("User ra lệnh agent tìm cách").
  3. Giữ repo sạch sẽ ($O(1)$ Auto-quarantine) và sẵn sàng nhận lệnh thi công tiếp, cấm buông xuôi đóng phiên.

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
