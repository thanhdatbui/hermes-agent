# Sol Planner Hard Gate & Zero-Bypass PreToolUse Hook

## 1. Bản Chất Sự Cố & Câu Hỏi Kiến Trúc
- **Sự cố:** Coordinator nhận task sửa luồng logic (Google checkpoint `challenge/iap`). Thay vì gọi Tầng A (Sol Planner :20129) plan offline để chốt Patch Contract đóng, Coordinator lại tự suy luận, tự viết contract trong đầu và dispatch thẳng Worker luôn.
- **Tad hỏi:** *"Gọi claude cli tư vấn cách để ép mày k làm ẩu v nữa."*
- **Audit từ Claude Opus:**
  - **Soft Constraints (Memory / System Prompt / CoT) luôn thất bại:** LLM là máy tính xác suất. Khi thấy lỗi rõ ràng, confidence score của việc "sửa ngay" (~0.94) áp đảo quy tắc "gọi plan trước" (~0.71). Càng context dài, rule trong prompt càng bị pha loãng (diluted).
  - **Zero-Bypass Gate:** Chỉ có cơ chế kiểm tra tất định (deterministic) bằng code tại tầng hạ tầng (PreToolUse Hook) trước khi tool `delegate_task` được thực thi mới có thể ép Coordinator 100% không thể làm ẩu.

---

## 2. Thiết Kế Hook `sol_gate.py` Cho `delegate_task`

```
Coordinator (Hermes) phát lệnh delegate_task
                     │
                     ▼
             [PreToolUse Hook]
                     │
         Có sol_plan_id hợp lệ?
         ├─ KHÔNG / HẾT HẠN / ĐÃ DÙNG ──> Exit non-zero (REJECT)
         │                                 Dội lỗi đỏ vào context ép gọi Sol Planner
         │
         └─ HỢP LỆ & CÒN HẠN (<300s) ───> Exit 0 (PASS)
                                           Cho phép Worker thực thi
```

### Quy Tắc Chặn
1. **Bắt buộc `sol_plan_id`:** Mọi lệnh dispatch sửa code logic phải mang theo ID từ Sol Planner (:20129).
2. **Xác thực chữ ký:** Plan phải được lưu dưới dạng file runtime, có hash SHA-256 đối soát integrity.
3. **Giới hạn thời gian (TTL):** Plan chỉ có hiệu lực trong 300 giây.
4. **Sử dụng một lần (Consumed flag):** Tránh replay plan cũ.
5. **Ngoại lệ T0 bằng Regex cứng:** Chỉ cho phép bypass Sol Plan nếu diff < 50 ký tự và khớp chính xác regex đổi hằng số đơn giản hoặc comment. Tuyệt đối không để LLM tự phán xét "việc nhỏ".
