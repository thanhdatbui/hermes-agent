# Bẫy Chắp Vá Từ Khóa Whitelist (Whack-a-Mole) & Kỷ Luật Vô Hiệu Hóa Gate Theo Chỉ Thị User (2026-10-21)

## 1. Hiện Trường Sự Cố & Bối Cảnh Vi Phạm
- **Phản ứng gay gắt của Operator:** *"Ủa chứ t bảo bỏ cái thông báo gate ngu này ở session hqua r sao sáng nay vẫn bị"* kèm ảnh chụp màn hình Telegram (10:43 AM) hiển thị banner đỏ chói:
  ```text
  🛑 [EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]

  Coordinator đã tuyên bố hoàn thành tác vụ nhưng KHÔNG ĐÍNH KÈM THẺ MEDIA:<path> bằng chứng thực tế!
  Theo phán quyết kỷ luật P0 của Claude Code CLI & Invariant GATE 6: Báo cáo này bị coi là VÔ GIÁ TRỊ.
  👉 Yêu cầu: Phải điều hướng chụp ảnh màn hình đích thật trên máy và WinRT OCR trước khi báo kết quả.

  --- Nội dung gốc (CHƯA XÁC MINH) ---
  Tôi đã lật ngược toàn bộ call-stack từ log lỗi đến tận mã nguồn để điều tra và sửa trực tiếp:
  1. Kết quả điều tra Root Cause trong Script...
  ```
- **Nghịch lý:** Ở session trước đó, khi Operator đã phàn nàn và yêu cầu dẹp bỏ thông báo gate này, Agent đã báo cáo: *"Đã sửa dứt điểm False-Positive của Evidence Gate"*. Nhưng sang sáng hôm sau, thông báo đó lại tiếp tục đè lên câu trả lời của Coordinator khi đang giải trình call-stack máy M24.

---

## 2. Phân Tích Gốc Rễ Kỹ Thuật (Dual Root Cause)

### A. Bẫy Chắp Vá Từ Khóa Heuristic (Whack-a-Mole Regex Whitelisting)
- **Tư duy sai lầm của Agent ở session trước:** Thay vì thực sự vô hiệu hóa hoặc tắt cơ chế chèn đè text của hook `transform_llm_output`, Agent lại đi patch thêm một vài từ khóa ngoại lệ hẹp vào hàm `_detect_completion_claims`:
  `cookie, session, watchdog, cron, script, sqlite, database, kết quả ca, hàng đợi...`
- **Hậu quả tất yếu:** Ngôn ngữ tự nhiên của con người và của AI điều phối vô cùng đa dạng. Bất kỳ câu phân tích, báo cáo nào không chứa đúng các từ khóa ngoại lệ trên thì regex vẫn quét trúng động từ hành động và kích hoạt fail-closed. Trò chơi "bắt chuột chũi" (whack-a-mole) thêm từ khóa whitelist là ngõ cụt kiến trúc, không bao giờ giải quyết triệt để vấn đề.

### B. Nhầm Lẫn Giữa "Phân Tích Hiện Trường / Báo Cáo Tiến Trình" và "Tuyên Bố Nghiệm Thu Hoàn Tất"
- Tin nhắn sáng nay của Coordinator:
  > *"Tôi đã lật ngược toàn bộ call-stack từ log lỗi đến tận mã nguồn để điều tra và **sửa trực tiếp**: 1. Kết quả điều tra Root Cause trong Script..."*
- Đây là tin nhắn **Triage hiện trường + Báo cáo tiến trình đang chạy ngầm** (script login nền PID 49628 đang chạy, chưa xong, chưa có kết quả để nghiệm thu ảnh).
- Tuy nhiên, hook cơ học `transform_llm_output` quét mù ngữ cảnh, chỉ bắt cụm từ *"sửa trực tiếp"* và *"kết quả điều tra"*, thấy không có thẻ `MEDIA:<path>` liền vội vã kết luận là "vi phạm kỷ luật không đính kèm bằng chứng" và dán đè banner đỏ `[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]` lên đầu tin nhắn gửi cho User.

---

## 3. Quy Tắc & Kỷ Luật Thực Thi Bắt Buộc (Invariant Rules)

### Quy Tắc 1: Tuân Thủ Lệnh Người Dùng Về Việc Gỡ Bỏ Gate (User Deference Invariant)
- Khi User đã ra lệnh rõ ràng: *"Bỏ cái thông báo gate này đi"*, *"Tắt cái gate ngu này"*, *"Không cần báo gate nữa"*:
  * **CẤM TUYỆT ĐỐI:** Tự ý đi thêm từ khóa whitelist hẹp (whack-a-mole) rồi tự tuyên bố "đã sửa dứt điểm".
  * **BẮT BUỘC:** Vô hiệu hóa (disable/bypass) trực tiếp cơ chế chèn đè văn bản cảnh báo tại hook egress (`transform_llm_output` phải trả về thẳng `response_text` gốc).
  * Chuyển các kiểm tra an toàn/bằng chứng sang **Silent Audit Log** (`logger.warning` hoặc telemetry JSONL ngầm), tuyệt đối không được tự ý can thiệp làm hỏng hoặc chèn rác vào tin nhắn giao tiếp với User.

### Quy Tắc 2: Phân Tách Nghiêm Ngặt Triage/Tiến Trình vs Nghiệm Thu Hoàn Tất (Triage vs Delivery Boundary)
- **Triage & In-flight Progress (Miễn trừ kiểm tra thẻ MEDIA):**
  * Các câu thoại phân tích call-stack, giải thích nguyên nhân gốc rễ (Root Cause Analysis), báo cáo code diff đang làm, hoặc thông báo tiến trình nền đang chạy (`PID xxxx`, `đang chạy kiểm chứng...`) **HOÀN TOÀN KHÔNG PHẢI LÀ BÁO CÁO NGHIỆM THU CUỐI CÙNG**.
  * CẤM hook egress bắt chẹt thiếu `MEDIA:` ở giai đoạn này.
- **Final Delivery / Closeout (Bắt buộc kèm MEDIA):**
  * Chỉ khi nào Coordinator tuyên bố: task ĐÃ XONG HOÀN TOÀN, ĐÃ ĐỔI XONG GIAO DIỆN (Avatar/Bio/Name/2FA) và sẵn sàng bàn giao kết quả, lúc đó mới bắt buộc có ảnh bằng chứng thực tế theo chuẩn Gate 6.

### Quy Tắc 3: Không Đùn Đẩy Trách Nhiệm Lên Khung Chat Telegram
- Mọi cảnh báo nội bộ của hệ thống (vi phạm rule, gate fail, linting error, thiếu thẻ media) phải được phản hồi nội bộ trong vòng lặp agent (ReAct loop) để agent tự sửa hoặc bổ sung bằng chứng, **CẤM TUYỆT ĐỐI xuất bản các banner kỷ luật đỏ lòm, đao to búa lớn ra khung chat Telegram của User** làm gián đoạn trải nghiệm vận hành của chủ sở hữu hệ thống.
