# Claude CLI Reviewer Primary, Sol Web Fallback & Payload Ceiling Bifurcation

## 1. Bối cảnh & Căn nguyên bài toán Quota Reviewer

Sau khi hoàn thiện **Hệ thống Gate 3 Tầng (`plan_exec_gate.py`)** và định tuyến **Agy CLI (`ag_cli.py fix`) làm Tier 1 Primary Worker**:
- **Khối lượng thi công sửa code (ngốn 80-90% turns/tokens)** đã được chuyển hoàn toàn sang pool Agy (21-25 accounts Google).
- **Claude Sonnet CLI** chỉ còn 2 nhiệm vụ chuyên biệt:
  1. **Planner (Gate B):** 1 call duy nhất đọc Evidence Pack từ Gate A, xuất `plan.json` O(1) (bị cấm tool Edit/Write).
  2. **Reviewer (Closeout Gate):** 1-2 calls khi chốt phiên, đọc diff O(1) và kết quả focused test.
- **Tổng ngân sách:** Mỗi phiên chỉ tiêu tốn 2-3 requests read-only. Hạn mức quota của Claude CLI hoàn toàn chịu tải an toàn và bền bỉ trong ngày.

---

## 2. Kiến trúc Reviewer 2 Tầng (Claude CLI Primary ➔ Sol Web Fallback)

Để triệt tiêu hiện tượng Reviewer chấm ngáo do bẫy `chatgpt-web/auto` (tài khoản Free bị OpenAI ngầm định tuyến về cụm Luna Free) mà vẫn bảo đảm tính liên tục (fail-safe):

1. **Primary Reviewer (Tier 0):** **Claude Sonnet CLI** (`claude_worker.py --role reviewer`).
   - Sắc bén, khách quan, không hallucination, đọc hiểu sâu logic đa luồng và edge-cases.
   - Nhận diện đúng chuẩn các vi phạm contract, race-condition, và assertion chất lượng.
2. **Fallback Reviewer (Tier 1):** **Sol Web (`gpt-web-sol` qua port 20129)**.
   - Tự động kích hoạt khi Claude CLI chạm trần Quota Guard (85%), dính lỗi mạng hoặc timeout.
3. **Fallback Reviewer (Tier 2):** **Agy Pool / OpenCode**.
   - Kích hoạt khi cả Claude CLI lẫn hạ tầng Web ChatGPT gặp sự cố nghiêm trọng.

---

## 3. Phân rã Ranh giới: Trần Payload 37KB vs Bất biến An toàn Farm

Khi chuyển đổi Reviewer sang Claude Sonnet, cần phân định rạch ròi giữa **giới hạn hạ tầng nhà cung cấp** và **luật an toàn nghiệp vụ Phone Farm**:

### A. Giới hạn hạ tầng Sol Web (CẦN BÃI BỎ HOẶC NỚI RỘNG CHO CLAUDE):
- **Trần 37KB (`sol_payload_guard.py` & `MAX_DIFF_BYTES_GATE = 30_000`):**
  - Sinh ra do OpenAI Web WAF chặn HTTP 413 khi payload vượt quá 40KB.
  - Gây ra bẫy `TRUNCATION_MANIFEST` và lỗi `NEED_CONTEXT` giả tạo khi diff test suite hoặc integration test hơi dài.
  - **Với Claude Sonnet (Context 200.000 tokens ~ 800KB):** Giới hạn 37KB này hoàn toàn vô nghĩa và trở thành vật cản. Khi chạy Claude Reviewer, trần payload được nới rộng (lên 200KB - 500KB) để Claude đọc trọn vẹn 100% diff và test log mà không bị cắt tỉa.

### B. Bất biến An toàn Farm (BẮT BUỘC GIỮ NGUYÊN 100%):
- **Ngân sách diff O(1) (≤ 30 dòng numstat):** Luôn áp dụng cho production code để ép Agent tập trung đúng mục tiêu, cấm refactor lan man.
- **Kiểm chứng Focused Test < 30s:** 100% test pass thật trước khi Reviewer chấm điểm; cấm dùng `--skip-test` trong repo mode.
- **Vùng cấm tuyệt đối:** Cấm can thiệp các module guard an toàn, tệp cấu hình bí mật, thông tin xác thực hay cơ sở dữ liệu farm.
- **Quy trình 3 Strike & Hand-off:** Trượt 3 lần bắt buộc dừng lại bàn giao cho Operator, cấm vòng lặp tự sửa vô tận.
