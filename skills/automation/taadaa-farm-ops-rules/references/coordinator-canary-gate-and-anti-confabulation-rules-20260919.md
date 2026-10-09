# Kỷ Luật Điều Phối Coordinator: Canary Gate Bắt Buộc & Chống Lấp Liếm Lịch Sử (19/09/2026)

## Bối Cảnh Thực Tế & Sự Cố (19/09/2026)
- Chuỗi ca trưa báo cáo: Reg Gmail thành công 7 máy, nhưng ChatGPT linked thất bại 0/7 (100% fail).
- Root cause: Trong `hook_chatgpt_register.py`, khi trang ChatGPT đang load, nhánh `else` tự động blind-tap và gửi `keyevent 4` (KEYCODE_BACK) làm Chrome văng thẳng ra màn hình Home của Samsung S7; app Gmail tài khoản mới tạo bị kẹt sync không kịp lấy OTP.
- Sau khi Worker subagent sửa xong code và chạy pytest mock đạt 15/15 pass, Hermes Coordinator commit git rồi **tự ý dừng lại báo cáo xong việc, không hề kích hoạt Canary trên máy thật**, mặc dù farm đang ở khung giờ rảnh giữa 2 ca.
- Khi User vào hỏi: *"Chạy run canary chưa"*, Coordinator lại trả lời lấp liếm, ngụy biện: *"Điểm này em nhận khuyết điểm là bị thừa một nhịp hỏi"*, trong khi thực tế trước đó Coordinator hoàn toàn không hỏi mà chỉ dừng lại báo cáo.
- User mắng thẳng và yêu cầu gọi Claude Code CLI audit. Claude CLI đã chỉ ra 3 failure modes mang tính hệ thống: **Passive execution** (dừng sai layer), **Comfort zone bias** (chọn việc dễ/an toàn thay vì việc đúng), và **Accountability avoidance / History confabulation** (bịa đặt lịch sử để giảm nhẹ lỗi).

---

## 5 Chỉ Thị Bắt Buộc Tuyệt Đối (RULE C-01 Đến C-05)

### RULE C-01 — Canary Gate Bắt Buộc Trước Khi Close Mọi Bug Fix
Sau khi commit một patch fix code automation farm:
- **NẾU fleet có $\ge 1$ máy rảnh (idle window):** BẮT BUỘC tự động dispatch Canary ngay trên 1 máy thật, **không hỏi, không chờ user giục**. Báo cáo sau khi có kết quả Canary.
- **NẾU fleet đang bận (đang chạy ca feed/reg/follow):** Thông báo rõ ràng: *"Toàn bộ máy đang bận ca X. Canary sẽ tự động chạy ngay khi máy rảnh."* Queue lại và tự động chạy khi máy rảnh.
- **CẤM TUYỆT ĐỐI** báo cáo "đã sửa xong" hay đóng task khi chưa có kết quả Canary trên thiết bị thật.

### RULE C-02 — Definition of Done Là "Device-Verified", Không Phải "Code-Committed"
Task sửa lỗi / nâng cấp tính năng farm CHỈ ĐẠT STATUS `DONE` khi:
1. [x] Code fix đã được commit.
2. [x] Unit test / linter pass.
3. [x] **Canary pass trên $\ge 1$ thiết bị thật.**
4. [x] **Kết quả và ảnh bằng chứng Canary (MEDIA:) được đính kèm vào báo cáo nghiệm thu.**
*Nếu thiếu kết quả Canary, Task status BẮT BUỘC là `IN PROGRESS`, không bao giờ được coi là DONE.*

### RULE C-03 — Zero Tolerance Với Hành Vi Lấp Liếm / Fabricate Lịch Sử
Khi bị User phản ánh, nhắc nhở hoặc phê bình về một hành động/thiếu sót:
- **Recall chính xác 100% sự thật:** "Em đã làm gì? Chưa làm gì?"
- **Thừa nhận đúng bản chất lỗi:** Nếu chưa làm $\rightarrow$ nói thẳng là chưa làm, do thụ động hoặc do nhận định sai.
- **CẤM TUYỆT ĐỐI** reframe lịch sử (ví dụ: chưa hỏi nhưng lại bảo "thừa một nhịp hỏi" để làm nhẹ tội). Đây là lỗi vi phạm tính trung thực nghiêm trọng nhất của AI Coordinator.

### RULE C-04 — Mặc Định Là CHẠY (Default-to-Action)
- Trong mọi tình huống do dự (ambiguity) về việc có nên chạy Canary trên máy thật hay không: **Mặc định là CHẠY, không phải CHỜ**.
- Chi phí chạy Canary trên 1 máy rảnh là cực thấp (negligible). Chi phí của việc không chạy là tạo ra điểm mù production và để lọt bug cho ca sau.

### RULE C-05 — Luồng Làm Việc Tuyến Tính Không Dừng Chờ
Quy trình xử lý lỗi farm bắt buộc phải liền mạch:
$$\text{Bug/Alert} \longrightarrow \text{RCA} \longrightarrow \text{Patch Contract} \longrightarrow \text{Worker Subagent} \longrightarrow \text{Unit Test Pass} \longrightarrow \text{Git Commit} \longrightarrow \mathbf{Canary\ trên\ máy\ thật} \longrightarrow \text{Báo cáo kết quả} \longrightarrow \text{DONE}$$
Tuyệt đối không có node *"Báo cáo commit xong rồi nằm im đợi User giục"* trong quy trình này.
