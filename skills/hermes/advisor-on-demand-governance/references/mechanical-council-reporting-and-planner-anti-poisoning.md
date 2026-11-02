# Quy Chuẩn Cơ Giới Hóa Báo Cáo Hội Đồng & Chống Đầu Độc Planner 100%

## 1. Cố Vấn Chính Là Planner (Hợp Nhất Guard Chống Đầu Độc)
- Trong pipeline sửa code (`unified_patch_pipeline.py`), bước S1 lên plan (`gate_b_planner.py`) triệu tập Hội đồng 3 Cố vấn (Gemini Argon + Claude Sonnet + Sol Web).
- **Lỗ hổng cũ:** Chỉ có lệnh gọi độc lập (`consult_advisor.py`) mới bọc hàm chống đầu độc `sanitize_advisor_prompt`, còn `gate_b_planner.py` lại nhận raw task prompt mà không qua lọc.
- **Quy chuẩn bắt buộc:**
  - `gate_b_planner.py` bắt buộc import `sanitize_advisor_prompt` từ `consult_advisor.py`.
  - Tại `run_council_planner`, mọi prompt gửi đến 3 Cố vấn (`ask_gemini_web`, `ask_claude_cli`, `ask_sol_worker`) BẮT BUỘC phải bọc qua `sanitize_advisor_prompt`.
  - Triệt tiêu hoàn toàn các câu hỏi dẫn dắt ("có phải do...", "chắc chắn tại...", "đúng không?"), giữ vững vai trò phản biện độc lập (Devil's Advocate).

## 2. Cơ Giới Hóa Báo Cáo Biểu Quyết Hội Đồng (Cấm Nói Quên Mồm)
- **Quy tắc bắt buộc:** Output của `unified_patch_pipeline.py` không được chỉ in dòng tóm tắt `PLAN: OK (Council...)`, mà BẮT BUỘC phải in chi tiết biểu quyết cơ học:
  ```text
  COUNCIL VOTES:
    - gemini: OK (latency: 72.5s, edits: 1)
    - claude: OK (latency: 72.5s, edits: 1)
    - sol: OK (latency: 72.5s, edits: 1)
  CONSENSUS: 3/3 (100.0%) -> Đồng thuận toàn bộ 3/3 cùng vị trí -> Chọn claude
  ```
- Dữ liệu được trích xuất trực tiếp từ `council_details` trong `plan.json`, loại bỏ hoàn toàn việc Coordinator tự ý tóm tắt giấu kết quả.

## 3. Cấm Tự Ý Thao Tác Ngoài Pipeline Sau Khi AWAITING_USER
- Khi pipeline đạt trạng thái `AWAITING_USER` (S5), Coordinator **TUYỆT ĐỐI CẤM** tự ý chạy thêm các lệnh ngoài pipeline như:
  - `npm run build` / `npm run build:backend` với timeout ngắn.
  - Kill hoặc terminate các tiến trình daemon/gateway (`node.exe`, `next start`).
- Mọi thao tác build dang dở sẽ làm hỏng artifact (`BUILD_ID`) và khiến watchdog rơi vào crash loop sập hệ thống.
