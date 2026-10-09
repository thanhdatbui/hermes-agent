# Benchmark Methodology: Plan Audit / Review Gate vs Problem Solving (09/2026)

## 1. Phân biệt rạch ròi 2 loại Benchmark
Khi đánh giá model cho hệ thống Phone Farm, phải phân biệt rõ mục đích đánh giá để không nhầm lẫn giữa hai vai trò:

| Tiêu chí | Problem Solving / Troubleshooting | Plan Audit / Review Gate (Gác cổng) |
| :--- | :--- | :--- |
| **Bản chất** | Tìm bug, đọc log, phân tích root cause, viết code sửa. | Thẩm định bản Kế hoạch (Implementation Plan) hoặc PR trước khi cho chạy. |
| **Đầu vào** | Log lỗi, trace, bug diff, triệu chứng crash. | Bản Plan do Worker nộp (các bước thực hiện, patch contract, test command). |
| **Mục tiêu** | "Lỗi tại sao và sửa thế nào?" | "Kế hoạch này có an toàn để cấp phép chạy không? APPROVED hay REJECT?" |
| **Tiêu chí chấm** | • Tìm đúng root cause.<br>• Không bị dẫn dắt bởi giả định sai (anti-sycophancy).<br>• Đưa ra action plan khả thi. | • Bắt bẫy Farm Invariant (`pm clear`, `os.walk` O(N), adb tap mù).<br>• Bắt bẫy Monolith Contract (`grep count == 1`, focused test <30s).<br>• Bắt bẫy Over-engineering (vẽ factory/abstract class thừa, test inflation).<br>• Bắt bẫy Gate 1 Decompose (trộn code surgery với batch job). |
| **Output chuẩn** | Phân tích root cause + hướng fix. | Bắt buộc dòng 1: `VERDICT: APPROVED` hoặc `VERDICT: REJECT` kèm Blocking Findings. |

---

## 2. Nguyên tắc tổ chức Benchmark đối kháng (Symmetrical Benchmark)
- **Cùng đề bài:** Mọi thí sinh (vd: Claude CLI, Sol Web) đều phải giải **toàn bộ các đề bài giống hệt nhau**. Tuyệt đối không chỉ cho A giải đề B và B giải đề A mà không chấm điểm đối xứng.
- **Cùng Rubric:** Tiêu chí chấm điểm (thang 100) phải cố định trước khi chấm, chia rõ điểm phạt nặng (ví dụ: duyệt PR có `pm clear` trừ 50đ; bợ dái user trừ 30đ).
- **Giám khảo chéo (Cross-grading):** Có thể dùng chính các model cấp cao làm giám khảo độc lập chấm bài của nhau dựa trên rubric chuẩn, hoặc Coordinator tổng hợp điểm.

---

## 3. Thứ tự ưu tiên Model Review / Plan Audit đã chốt
Trên OmniRoute (`:20129`), combo `review` được cấu hình phân tầng:
1. **Tier 0 (Primary):** `chatgpt-web/gpt-5.6-sol-high` qua pool 5 accounts ChatGPT-Web sống khỏe.
   - *Lý do:* Sol có năng lực reasoning cao cấp nhất (10/10), bắt trọn vẹn các bẫy kiến trúc trừu tượng (speculative architecture, over-engineering, invariant violation) và không tốn tiền API/token.
2. **Tier 1 (Fallback 1):** `gpt-5.6-terra-high` (Codex Farm pool).
   - *Lý do:* Giỏi soi diff byte-level và test logic hẹp, dùng khi pool Web chạm rate limit.
3. **Tier 2 (Fallback 2):** `ag-opus-pool` (Claude Opus 4.6 Thinking trên 78 Google accounts).
4. **Chốt chặn khẩn cấp ngoài band:** `Claude CLI` (`claude -p` Opus) dùng khi cần kiểm tra lệnh gắt gao từng ký tự trước khi merge/commit lớn.
