# AI Chấm Điểm Chốt Phiên — Scorecard Protocol (Zero-Cost Sol Web & Quota Protection)

## 1. Bối cảnh & Nguyên lý (2026-09-16)
- **Vấn đề của "hỏi xong chưa" thông thường**: AI có xu hướng chiều lòng người dùng (sycophancy), dễ tự xưng hoàn thành, tự báo pass test dù chưa chạy lệnh thật trên đĩa (hallucination).
- **Nguyên lý Giám khảo Chấm điểm (Scorecard Persona Shift)**: Đặt AI vào vai trò giám khảo độc lập khó tính chấm theo thang điểm 100 với Rubric khắt khe. AI bắt buộc phải phân tích từng con số và đối soát bằng chứng sống (git diff, pytest output, file hash).
- **Quota Protection cho Claude CLI Opus**: Chạy Claude Opus CLI `--effort high` cho mọi ca chốt phiên hàng ngày sẽ đốt cạn quota 5h/tuần. Vì vậy, chuyển giao vai trò Giám khảo Chốt phiên mặc định sang **GPT-5.6 Sol Web qua OmniRoute :20129** (hoàn toàn miễn phí 0đ, high-reasoning 60-120s).

---

## 2. Công cụ thực thi: `D:/Taadaa/tools/sol_auditor.py`

### Quy trình 3 bước tự động:
1. **Coordinator thu thập bằng chứng sống O(1)**:
   - `git status -s` & `git show/diff` (xác nhận file thật trên đĩa và commit hash).
   - Chạy `pytest` thực tế trong môi trường isolated, bắt log output thật (`X passed in Y.YYs`).
   - Tóm tắt logic thay đổi và danh sách artifacts.
2. **Gửi sang Sol Web (:20129)**:
   - Endpoint: `http://127.0.0.1:20129/v1/chat/completions` (model `chatgpt-web/gpt-5.6-sol-high`).
   - Prompt format chuẩn schema JSON, ép buộc trừ điểm nếu thiếu benchmark, thiếu integration test hoặc rủi ro regression.
3. **Phán quyết đóng phiên**:
   - `overall_score >= 85` VÀ `verdict == "APPROVED"`: Cho phép hoàn tất chốt phiên.
   - `overall_score < 85` HOẶC `verdict == "CHANGES_REQUESTED"`: Coordinator dừng lại, thông báo rõ các điểm bị trừ và sửa đổi trước khi chốt.

---

## 3. Rubric Chấm Điểm 100

| Tiêu chí | Trọng số | Nội dung kiểm tra |
| :--- | :---: | :--- |
| **Logic Correctness & Chống phát hiện** | 35đ | Logic chặt chẽ, fail-closed, không dead-swipe, xử lý edge cases đa ngôn ngữ. |
| **Test Evidence & Phủ định regression** | 25đ | Có pytest thực tế chạy pass 100%, không chấp nhận self-report không lệnh chạy. |
| **Telemetry & Observability** | 15đ | Dữ liệu được ghi nhận vào summary, log và hiển thị trên Telegram watchdog report. |
| **Farm Safety & Invariant** | 15đ | Không vi phạm 5 Gates, không deadlock, không giữ lock máy Android khi planning. |
| **Code Architecture & Cleanliness** | 10đ | Code sạch, atomicity, xử lý EOL CRLF/LF Windows chuẩn mực. |

---

## 4. Phân định vai trò Reviewer

- **Mặc định mọi phiên**: Dùng `sol_auditor.py` (GPT-5.6 Sol Web :20129) — Zero-Cost, khách quan, không chạm quota.
- **Ngoại lệ duy nhất cho Claude Opus High CLI**: Chỉ kích hoạt khi gặp sự cố P0 tê liệt toàn farm, tranh chấp kiến trúc nghiêm trọng hoặc khi người dùng ra lệnh đích danh *"gọi claude cli kiểm tra"*.
