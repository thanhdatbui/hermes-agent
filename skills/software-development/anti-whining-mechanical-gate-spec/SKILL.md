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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
