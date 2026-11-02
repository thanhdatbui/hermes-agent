# Council-All Default & Single-Advisor Bias Fallacy (2026-11-02)

## 1. Hiện Tượng & Sự Cố (Symptom)
- Trong các turn tư vấn kỹ thuật hoặc phân tích nguyên nhân lỗi, Coordinator chỉ gọi đơn độc 1 Advisor (thường là Sol qua option `-a sol` vì latency nhanh hơn), bỏ quên Claude CLI và Gemini Argon.
- User phản ánh gay gắt: *"Sao có mỗi advisor Sol vậy, mấy advisor khác đâu? Tôi nhớ là cài mặc định triệu hồi hội đồng advisor rồi mà?"*

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
- Mặc dù CLI `consult_advisor.py` có cờ `--advisor / -a` mặc định là `all`, nhưng trong thói quen gọi lệnh của Agent thường tiện tay gõ `-a sol` để tránh timeout hoặc tiết kiệm thời gian chờ.
- Việc này tạo ra hiện tượng **Single-Advisor Bias** (thiên kiến một chiều từ GPT-5.6), làm mất đi tính phản biện chéo khách quan của Claude Sonnet và Gemini Argon.
- Khi chỉ có Sol, các góc nhìn kỹ thuật sâu về rủi ro giấy phép (AGPL của YOLOv8), bẫy tính Laplacian trên cả frame hay bẫy cắt cụt mặt không được cảnh báo kịp thời.
- Điển hình trường hợp đánh giá thuật toán phân phối/cắn đề xuất: Sol phân tích định tính về sự khác nhau giữa tăng trưởng và đề xuất, Gemini Argon vạch trần định lượng False Positives của ngưỡng 50 tim/tuần, còn Claude CLI mổ xẻ rủi ro toán tử `OR` và điều kiện tĩnh `1000 fl & LIVE`. Sự phối hợp cả 3 mới tạo ra bức tranh toàn diện để ra quyết định chính xác.

## 3. Quy Tắc Điều Phối Bắt Buộc (Governance Invariant)
1. **Triệu Hồi Toàn Thể Hội Đồng Mặc Định (-a all):**
   - Mọi câu hỏi kiến trúc, tư vấn giải pháp kỹ thuật, phân tích nguyên nhân sự cố hoặc review kế hoạch bắt buộc gọi với cờ `-a all` (hoặc `-a both` đối với cặp Sol + Claude).
   - Tuyệt đối CẤM Coordinator tự ý ép gọi đơn độc `-a sol` trừ khi User có chỉ thị đích danh *"Hỏi riêng Sol"*.
2. **Xử Lý Timeout Bậc Thang:**
   - Khi gọi `-a all`, lệnh `consult_advisor.py` chạy đa luồng ThreadPoolExecutor song song.
   - Timeout subprocess của terminal bắt buộc đặt từ `90s - 120s` để đủ thời gian gom phản hồi từ cả Sol HTTP (:20129) lẫn Claude CLI subprocess.
3. **Hiển Thị Báo Cáo Hội Đồng Phân Tầng:**
   - Phản hồi trình bày cho User phải hiển thị đầy đủ các khối phân biện:
     - 🟢 `[ADVISOR SOL — GPT-5.6 / :20129]`
     - 🟣 `[ADVISOR CLAUDE — SONNET / CLI]`
     - 🔵 `[ADVISOR GEMINI — ARGON 4 / :20129]` (nếu có)
   - Nếu một trong các Advisor bị timeout/unavailable, hệ thống vẫn in rõ trạng thái của Advisor đó thay vì âm thầm giấu đi.
