# Bẫy Cưỡng Chế Tóm Tắt Khi Chạm Trần Vòng Lặp (Max Iteration Summary Trap) & Cơ Chế Khóa Cứng Timeout Worker

## 1. Hiện tượng & Vụ việc thực tế (Sự cố Máy 41 ngâm 3 tiếng — 07/09/2026)
- **Sự cố:** Farm alert Máy 41 dừng phiên do ADB timeout khi launch TikTok bằng monkey.
- **Diễn biến:** 
  + Worker 1 (`deleg_8cdc61eb`): Chạy 75 phút (4.486s), cắn đúng 35 API calls. Đưa ra phân tích root cause cực dài, đề xuất diff nhưng không hề gọi tool sửa file.
  + Worker 2 (`deleg_ee9a1003`): Giao việc áp patch, chạy 54 phút (3.266s), cắn đúng 35 API calls. Báo cáo "Sau khi áp dụng diff... 9/9 tests passed", nhưng thực tế `git status` clean 100%, không có file nào được sửa.
  + Worker 3 (`deleg_c36fc5df`): Ép sửa bằng tool patch, chạy 27 phút, áp patch nhưng chèn logic thừa làm gãy 5 unit test downstream.
  + Tổng thời gian mất 161 phút (~3 tiếng) cho 1 dòng patch code.

## 2. Bản chất kỹ thuật & Cơ chế bên trong Hermes Runtime
1. **Trần vòng lặp và bẫy `handle_max_iterations`:**
   - Trong `chat_completion_helpers.py`, khi subagent gọi đến vòng lặp thứ `delegation.max_iterations` (cũ là 35), hàm `handle_max_iterations` sẽ cưỡng chế ngắt quyền gọi tool:
     > *"⚠️ Reached maximum iterations (35). Requesting summary... Please provide a final response summarizing what you've found... without calling any more tools."*
   - Model bị buộc phải viết báo cáo tổng kết. Model không tự hoàn thành công việc, nó chỉ đang viết bản tường trình khi bị hệ thống cắt quyền.
2. **Ảo giác hành động (Confabulation) của model reasoning:**
   - Khi chạy model như `ag-gemini-pool-3` với `reasoning_effort: high`, model dễ rơi vào analysis paralysis (đọc log, lần mò code qua 20-30 tool calls).
   - Khi bị ép tóm tắt ở turn cuối, model sinh ra ảo giác "tôi đã áp patch và kiểm tra test xanh" mà thực chất chưa hề gọi tool `patch` hay `write_file`.
3. **Tháo sạch phanh thời gian (No Wall-clock Timeout):**
   - Trong `delegate_tool.py`, hàm `_get_child_timeout()` mặc định trả về `None` nếu không có `delegation.child_timeout_seconds`.
   - Nếu mỗi turn mất 1.5 - 2 phút (do thinking high + nghẽn proxy), 35 turns sẽ kéo dài 60 - 75 phút mà không có bất kỳ bộ đếm thời gian nào cắt child.

## 3. Quy tắc & Cấu hình chuẩn hóa (Khóa 4 tầng)
1. **Cấu hình `config.yaml` bắt buộc:**
   - `delegation.model: ag-claude`: Chuyển sang Claude cho worker code để đảm bảo kỷ luật instruction-following và triệt tiêu ảo giác sửa code mồm.
   - `delegation.max_iterations: 15`: Giảm trần từ 35 xuống 15 để ép dừng sớm nếu worker bắt đầu lượn vòng.
   - `delegation.reasoning_effort: medium`: Giảm từ high xuống medium (cắt 50% độ trễ mỗi turn).
   - `delegation.child_timeout_seconds: 600`: Hard cap đúng 10 phút. Quá 600s runtime tự động kill worker.
   - `agent.gateway_timeout: 3600`: Hạ từ 14400s (4h) xuống 3600s (1h).
2. **Quy tắc Zero-Trust đối với báo cáo của Worker:**
   - Coordinator TUYỆT ĐỐI KHÔNG tin vào báo cáo văn bản ("đã sửa xong", "tests passed").
   - Ngay sau khi worker kết thúc, Coordinator PHẢI kiểm tra bằng lệnh thực tế: `git status --porcelain` và `git diff`.
   - Nếu git status clean mà worker báo done: Khẳng định ngay worker bị dính bẫy max-iterations summary trap. Dừng ngay, không để trôi 54 phút.
3. **Definition of Done (DoD) trong Dispatch Prompt:**
   - Trong context giao việc cho worker, bắt buộc yêu cầu:
     > *"BẮT BUỘC: (1) Dùng tool patch sửa file. (2) Chạy `git --no-pager diff --stat` và dán nguyên văn output vào cuối báo cáo. Báo cáo KHÔNG có git diff thật = TASK FAILED."*
