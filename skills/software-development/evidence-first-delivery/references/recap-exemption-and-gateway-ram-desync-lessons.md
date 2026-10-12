# BÀI HỌC VÁ EVIDENCE-FIRST GATE: RECAP EXEMPTION & BẪY LỆCH PHA RAM GATEWAY

## 1. Cạm Bẫy Spam Cảnh Báo Đỏ Trên Lượt Hội Thoại Tiếp Nối (Conversational Recap Trap)
- **Hiện tượng**: User hỏi tiếp sau khi đã xem ảnh (ví dụ: *"M làm xong hết r à"*), Coordinator trả lời giải trình/nhắc lại kết quả cũ (*"đã out sạch nick X, đã login chuẩn nick Y, đã gán vào Excel..."*). Ngay lập tức gate chèn đè hoặc append cảnh báo đỏ: `🛑 [EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]`.
- **Nguyên nhân gốc rễ**:
  1. Hook `transform_llm_output` quét regex từng mệnh đề trên MỌI turn một cách độc lập.
  2. Gate không tra cứu lịch sử phiên (`sess_state["verified_media_details"]`), coi mọi câu nói chứa từ khóa nghiệp vụ là một tuyên bố hoàn thành mới chưa có bằng chứng (khi turn đó không đính kèm lại thẻ `MEDIA:` cũ).
  3. Bắt nhầm các hành động backend/sổ sách: các câu nói về Excel, TOTP secret, script runner, kịch bản farm bị quét trúng từ khóa `2FA` hoặc `đổi pass` dù đây không phải thao tác UI trên thiết bị.
- **Giải pháp chuẩn hóa**:
  - **Mở rộng regex loại trừ trong `_detect_completion_claims`**: Bỏ qua các mệnh đề liên quan đến backend, sổ sách, Excel, TOTP, CLI, terminal, và từ khóa tường thuật (`excel`, `sổ sách`, `totp`, `cli`, `terminal`, `kịch bản`, `tới ca`, `lúc nãy`, `trước đó`, `nhắc lại`, `thu dọn`).
  - **Session-State Recap Exemption trong `_enforce_evidence_first_gate`**: Trước khi kết luận vi phạm vì thiếu `MEDIA:`, gate đối soát các entity/username trong câu trả lời với `sess_state["verified_media_details"]`. Nếu tất cả tài khoản đã có bằng chứng hợp lệ trong phiên, tự động coi là recap và suppress banner vi phạm.

## 2. Bẫy Lệch Pha RAM Gateway & Tái Phát Cảnh Báo Sau Khi Vá Đĩa (Gateway RAM Desync Trap)
- **Hiện tượng**: Coordinator đã sửa code plugin trên đĩa, tự tin báo "đã fix rồi", nhưng ngay tin nhắn đó User vẫn nhận được cảnh báo đỏ cũ! User bức xúc: *"Vẫn báo tiếp nè mày ngay trc khi mày soạn tn bảo fix r luôn"*.
- **Căn nguyên kỹ thuật**: Tiến trình nền Hermes Gateway (`pythonw.exe gateway run`) là long-running daemon. Python chỉ load module vào RAM lúc khởi động. Mọi thay đổi trong plugin `.py` trên đĩa hoàn toàn vô hiệu hóa trong RAM cho đến khi tiến trình Gateway được restart.
- **Quy tắc bắt buộc**:
  - Khi sửa plugin runtime điều phối, **BẮT BUỘC** phải kích hoạt restart Gateway detached (ví dụ qua script `restart_gw_detached.py` đếm lùi 5s để turn hiện tại gửi xong rồi mới hạ PID cũ và spawn PID mới qua `Hermes_Gateway.vbs`).
  - Tuyệt đối không tuyên bố "đã fix xong" khi chưa khởi động lại tiến trình Gateway và kiểm tra PID mới qua `psutil`!
