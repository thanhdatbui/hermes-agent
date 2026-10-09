# Gate 1 Mandatory Task Decomposition & Anti-Bundling Lessons

## Bối cảnh sự cố (Root Cause Incident - 2026-10-05)
Trong phiên điều phối xử lý lỗi phiên feed/follow TikTok, Coordinator đã vi phạm nghiêm trọng Gate 1 (Decomposition) bằng cách gộp 3 bài toán logic độc lập vào 1 lượt thi công:
1. Chặn follow dạo khi dính cooldown phiên trước (`multi_machine_feed_session.py`, `feed_swipe_smoke.py`).
2. Watchdog không nuốt cụm rỗng và parse `already_liked_counts` từ JSON (`feed_session_watchdog.py`).
3. Lọc SystemUI/Notification trong OCR/XML chống nuốt retry handler mạng (`feed_swipe_smoke.py`).

Hậu quả: 6 files bị sửa đổi, diff phình to hơn 40 KB (+566 / -64 lines), vượt trần 24 KB của Sol Web khiến `closeout_gate.py` tự động kích hoạt fallback sang Terra Codex (`cx/gpt-5.6-terra-high`). Diff quá lớn mở rộng bề mặt rủi ro, kéo theo 4 vòng remediation kéo dài (điểm dao động 73 - 81).

## Gốc rễ tư duy sai lầm của Coordinator
1. **Tâm lý "ngại chốt phiên nhiều lần":** Tưởng gộp việc vào sửa 1 lần rồi chốt cho nhanh, né chạy gate nhiều lần; thực tế làm diff quá tải, kẹt gate lâu gấp 5 lần.
2. **Đánh đồng "cùng một luồng nghiệp vụ" là "cùng một task":** Thấy đều liên quan đến ca chạy feed nên gom chung, vi phạm nguyên tắc phân rã theo vòng đời và component.
3. **Bỏ qua checklist Gate 5:** Lướt qua câu hỏi "Task đã phân rã tới đơn vị nhỏ nhất chưa?" vì tự tin bài toán không khó về thuật toán.

## Quy tắc bắt buộc đã được Claude CLI thẩm định và chuẩn hóa (In-Place tại Gate 1)
1. **Đúng 1 Component / Bài toán Logic cho 1 Task:** CẤM gom việc cross-component (như flow vs watchdog). Gặp nhiều lỗi độc lập bắt buộc phân rã tuần tự:
   `Task A -> Verify A -> Commit local A; sau đó mới tới Task B`. CẤM TUYỆT ĐỐI tự ý git push remote khi user chưa ra lệnh chốt phiên.
2. **Cấm scope creep dọc đường:** CẤM TUYỆT ĐỐI tự ý biến các lỗi tình cờ phát hiện dọc đường (ngoài yêu cầu của user) thành sub-task sửa chữa (chỉ ghi nhận vào báo cáo).
3. **Khung ngân sách Blast Radius thống nhất:**
   - **Tối đa <= 2 files sửa đổi (BẮT BUỘC TÍNH CẢ FILE TEST)** — đồng bộ với quy chuẩn L2 Emergency Surgery. Miễn trừ các file catalog/docs bắt buộc theo quy chuẩn repo như `docs/farm-automation-cases.md`.
   - **Tối đa <= 100 dòng diff** (theo `git diff --numstat`).
   - **Mục tiêu diff thô <= 15 KB** để tổng payload review không vượt 24 KB, giữ Sol Web đọc 100% không bị cúp xén hay nhảy fallback Terra.
4. **Fail-Fast tại Worker:** Worker nhận contract nếu thấy scope vượt quá 1 component hoặc > 2 files bắt buộc dừng ngay trong <= 3 iterations đầu.
5. **Cổng kiểm soát Fail-Fast DIFF_TOO_LARGE (Exit Code 3 tại > 30.000 bytes):**
   Khi diff tích tụ vượt quá 30.000 bytes, `closeout_gate.py` tự động chặn đứng với Exit Code 3. Coordinator bắt buộc phải phân rã thành các **Semantic Lanes** riêng biệt và chạy review qua `--files <lane_files>`, cấm cố gom toàn bộ diff 6 file vào một lệnh review.
