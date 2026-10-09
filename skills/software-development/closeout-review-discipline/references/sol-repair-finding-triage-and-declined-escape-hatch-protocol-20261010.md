# Quy Chuẩn Triage Findings & Cơ Chế Thoát Declined Cho Sol Repair (10/10/2026)

Tài liệu đúc kết từ phiên giải quyết điểm nghẽn Closeout Gate và Sol Repair ngày 10/10/2026 với sự tham vấn kiến trúc từ Claude Code CLI.

---

## 1. Điểm nghẽn kiến trúc (Architectural Bottleneck)
Khi Closeout Gate REJECT (< 85đ), Reviewer (Sol High :20129) đóng vai trò Auditor lý tưởng hóa, thường đưa ra cả các nhận xét mang tính kiến trúc vĩ mô (thiếu metrics/alerting, thiếu config injection) hoặc đòi hỏi môi trường thực tế (phải kiểm thử trên thiết bị thật / ADB).

Trong khi đó, Sol Repair (`sol_repair.py`) đóng vai trò thợ vá O(1):
- Ngân sách cứng: `<= 30 dòng diff`.
- Kiểm thử Closeout bắt buộc chạy offline, cấm chạm thiết bị thật hay ADB.
- Cấm tạo class, module, cấu hình mới hoặc refactor diện rộng.

Nếu Coordinator chuyển tiếp thô (passthrough) 100% nhận xét của Reviewer vào Sol Repair:
1. **Bẫy vỡ ngân sách (Strike 1):** Sol cố gắng sửa hết các yêu cầu kiến trúc ➔ Sinh ra bản vá 150+ dòng (thêm class, hàm telemetry) ➔ Vi phạm trần O(1) numstat <= 30 dòng.
2. **Bẫy patch rỗng / Validation Fail (Strike 2):** Sol bị ép sửa các finding đòi test farm thật ➔ Sinh ra no-op patch (`old_snippet == new_snippet`) ➔ Kích hoạt bộ lọc an toàn `no-op patch rejected` và văng lỗi exit code 1.

---

## 2. Quy trình 4 Lớp Triage bắt buộc cho Coordinator
Trước khi tạo `scorecard.json` nạp vào `sol_repair.py`, Coordinator bắt buộc phải phân loại findings:

| Lớp finding | Định nghĩa & Nhận diện | Hành động điều phối |
|---|---|---|
| **Lớp A (Actionable O(1))** | Lỗi logic cụ thể, lỗi cú pháp, return code sai, edge case kiểm chứng được bằng focused test offline < 30s. Ước tính <= 15 dòng. | **CHỈ nạp nhóm này vào Sol Repair.** Ưu tiên theo severity và deduction. |
| **Lớp B (Vượt ngân sách O(1))** | Đòi hỏi thêm class mới, tái cấu trúc config, logging pipeline rộng. | Không nạp vào Sol Repair. Chuyển Worker lớn nếu thực sự chặn điểm. |
| **Lớp C (Bị môi trường chặn)** | Đòi hỏi chạy trên máy thật, ADB thật, E2E farm. Trái với invariant test offline của Closeout. | Không nạp vào Sol Repair. Ghi nhận là residual risk / waiver. |
| **Lớp D (Định tính / Khuyến nghị)** | "Nên có alerting", "chưa thấy metrics". | Không nạp vào Sol Repair. |

---

## 3. Cải tiến Kỹ thuật trong `sol_repair.py`

### a. Bộ tiền lọc xác định (Deterministic Pre-filter) có VETO chống False-Positive
Tự động lọc bỏ các finding vi phạm nguyên tắc offline của Closeout ngay tại `extract_findings_from_scorecard(scorecard, filter_non_actionable=True)`:
```python
NON_ACTIONABLE_PATTERNS = [
    re.compile(r"(?:chưa\s+(?:chứng\s+minh|kiểm\s+thử|chạy\s+thử)[^.;\n]{0,40}?(?:farm\s+thật|thiết\s+bị\s+thật|máy\s+thật))", re.I),
    re.compile(r"(?:cần\s+(?:kiểm\s+thử|chạy\s+thử)[^.;\n]{0,40}?(?:farm\s+thật|thiết\s+bị\s+thật|máy\s+thật))", re.I),
    re.compile(r"(?:chưa\s+thấy\s+cơ\s+chế\s+alerting|thiếu\s+cơ\s+chế\s+alerting)", re.I),
]
```
**Chốt chặn VETO bảo vệ lỗi code thật:**
Nếu finding chứa vị trí file/dòng (`foo.py:123`), chữ ký hàm/class (`def / class`), hoặc từ khóa lỗi runtime/logic (`crash`, `exception`, `lỗi logic`, `return code`), **tuyệt đối KHÔNG BAO GIỜ bị lọc**, kể cả khi câu có chứa từ "farm thật" hay "thiết bị thật".

### b. Schema lối thoát `declined_findings`
Nâng cấp prompt và schema đầu ra cho Sol High:
- Cho phép Sol từ chối minh bạch các finding không thể xử lý trong O(1) thay vì bịa patch no-op:
  ```json
  {
    "addressed_findings": ["F1"],
    "declined_findings": [
      {"id": "F2", "reason": "needs_device|exceeds_budget|qualitative"}
    ],
    "patches": [...]
  }
  ```

### c. Phân biệt Exit Code rõ ràng
- `exit 0`: Có patch code hợp lệ (đã kiểm tra syntax và anchor duy nhất).
- `exit 3`: Tất cả findings bị DECLINED (out-of-scope / environment / waiver) ➔ Coordinator ghi nhận waiver, **không nhầm là Sol bị lỗi** và không fallback sai mục đích sang Worker.
- `exit 1`: Lỗi cú pháp hoặc crash thực sự (điều kiện fallback sang Worker hợp lệ).
