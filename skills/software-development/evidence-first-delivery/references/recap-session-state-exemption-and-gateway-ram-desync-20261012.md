# BÀI HỌC VỀ RECAP EXEMPTION TRONG EVIDENCE GATE & BẪY LỆCH PHA RAM GATEWAY (2026-10-12)

Tài liệu đúc kết từ sự cố người dùng bức xúc khi Evidence-First Gate spam cảnh báo đỏ vi phạm liên tục vào Telegram trên các câu hỏi thoại/recap thông thường, và sự cố lệch pha RAM khi sửa code plugin mà chưa restart Gateway.

---

## 1. BẪY SPAM TRÊN CÂU HỎI THOẠI & RECAP ĐÃ XÁC MINH TRONG PHIÊN (RECAP VS NEW CLAIM BLIND SPOT)

### Hiện tượng & Phản ứng của Người dùng:
- Sau khi Coordinator đã gửi ảnh nghiệm thu hợp lệ (`MEDIA:<path>`) và được kiểm chứng thành công ở lượt trước, Người dùng hỏi tiếp các câu hỏi trao đổi thông thường:
  * *"M làm xong hết r à"*
  * *"Thì để sẵn trên excel Máy 266 tới ca chạy máy đó tự nạp"*
- Khi Coordinator trả lời thoại để giải trình và tóm tắt lại hiện trạng (ví dụ: *"Dạ toàn bộ các đầu việc đã hoàn tất 100%: nick A đã login, nick B đã bật 2FA..."*), hệ thống kiểm tra cơ học (`_detect_completion_claims`) quét trúng các từ khóa *"hoàn tất"*, *"đã login"*, *"đã bật 2FA"*.
- Do ở lượt chat này Coordinator không đính kèm lại cái ảnh cũ lần thứ hai/thứ ba, Gate lập tức bắt nhầm thành vi phạm và chèn cả khối cảnh báo đỏ:
  `🛑 [EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION] Coordinator đã tuyên bố hoàn thành tác vụ nhưng KHÔNG ĐÍNH KÈM THẺ MEDIA:<path> bằng chứng thực tế!`
- Người dùng cực kỳ bức xúc và phản ứng gay gắt: *"Sửa luôn cái thông báo media này. Nó spam bất chấp liên tục k đúng ý tao"*, *"Vẫn báo tiếp nè mày ngay trc khi mày soạn tn bảo fix r luôn"*.

### Nguyên nhân kỹ thuật gốc rễ:
1. **Stateless Claim Detection:** Hàm `_detect_completion_claims` chỉ phân tích regex chuỗi văn bản của lượt hiện tại một cách cô lập (stateless), không có khái niệm lịch sử phiên.
2. **Nhầm lẫn giữa "Báo cáo nghiệm thu mới" và "Nhắc lại (Recap) kết quả đã có ảnh":** Mục đích ban đầu của Gate là chống **Zero-Image Text Report Trap** (hoàn thành cả một tác vụ farm mà từ đầu đến cuối không gửi bất kỳ ảnh nào). Một khi phiên làm việc đã gửi và thẩm định ảnh thành công (`sess_state["verified_media_paths"]` > 0), các câu trả lời tiếp theo chỉ mang tính chất đàm thoại, giải thích hoặc xác nhận tiến độ với người dùng, hoàn toàn không phải là báo cáo khống.
3. **Cơ chế so khớp từ khóa quá hẹp:** Nếu bản vá chỉ cho phép recap khi OCR text của ảnh cũ khớp 100% tất cả các từ khóa (ví dụ: đòi hỏi ảnh Switcher phải chứa cả chữ "xác minh 2 bước đang bật" của nick khác), recap đa tác vụ sẽ lập tức gãy và tiếp tục spam.

### Giải pháp cơ học chuẩn hóa:
Trong `_enforce_evidence_first_gate`, trước khi phạt vi phạm đòi thẻ `MEDIA:`:
1. **Kiểm tra Session State (`sess_state`):**
   - Nếu trong phiên làm việc hiện tại ĐÃ CÓ bằng chứng được kiểm chứng (`sess_state.get("verified_media_paths")` có chứa file hợp lệ), hệ thống xác nhận người dùng đã nhận được bằng chứng trực quan của ca làm việc.
   - Các câu trả lời tiếp theo không kèm thẻ `MEDIA:` được coi là đàm thoại tiếp nối / recap, Gate tự động trả về `None`, triệt tiêu hoàn toàn banner vi phạm thô.
2. **Chỉ phạt khi có Claim mới hoàn toàn chưa từng có bằng chứng:**
   - Gate chỉ bắt buộc đòi `MEDIA:` khi phiên làm việc CHƯA TỪNG có ảnh verified nào (`verified_media_paths` rỗng), hoặc khi có claim về một tài khoản/entity hoàn toàn mới chưa từng xuất hiện trong `sess_state`.

---

## 2. BẪY LỆCH PHA RAM GATEWAY (LONG-RUNNING PYTHON DAEMON VS ON-DISK CODE)

### Hiện tượng:
- Giao việc sửa file plugin evidence gate hook.
- Tool sửa xong, cú pháp kiểm tra sạch sẽ.
- Coordinator lập tức gửi tin nhắn báo User: *"Dạ em đã sửa xong rồi ạ"*.
- **Kết quả đau đớn:** Ngay trước tin nhắn đó, Telegram lại nhảy ra tiếp thông báo vi phạm đỏ! Người dùng chụp màn hình chất vấn: *"Vẫn báo tiếp nè mày ngay trc khi mày soạn tn bảo fix r luôn"*.

### Căn nguyên:
- Hermes Messaging Gateway chạy dưới dạng tiến trình nền daemon dài hạn (`pythonw.exe -m hermes_cli.main gateway run`).
- Python nạp module vào bộ nhớ (`sys.modules`) đúng MỘT LẦN duy nhất khi tiến trình khởi động.
- Mọi thao tác sửa đổi file `.py` trên ổ cứng HOÀN TOÀN KHÔNG CÓ HIỆU LỰC trong RAM của Gateway đang chạy! Tiến trình Gateway tiếp tục thực thi bytecode cũ trong bộ nhớ cho đến khi được restart.

### Quy tắc bất biến khi sửa đổi Plugin / Gateway Hook:
1. **CẤM TUYỆT ĐỐI** tuyên bố đã sửa xong plugin/gateway khi chưa thực hiện restart Gateway.
2. **Kích hoạt Delayed Restart Detached:**
   - Sử dụng script có sẵn: `powershell -ExecutionPolicy Bypass -File D:/Taadaa/Hermes/deploy/hermes-home/scripts/delayed-restart.ps1`.
   - Script này sẽ chờ 6 giây để Gateway hoàn tất gửi phản hồi của turn hiện tại về Telegram, sau đó dừng PID cũ và khởi động một tiến trình `pythonw.exe` mới hoàn toàn.
3. Khi Gateway mới khởi động, bytecode mới trên đĩa mới chính thức được nạp vào RAM.

---

## 3. KỶ LUẬT TUÂN THỦ: CẤM NÉM TEXT GATE RÁC VÀO CHAT

- User profile và memory quy định rõ:
  * *Cấm ném text gate rác vào chat.*
  * *Cấm trả câu cảnh báo gate thô vào chat.*
  * *Tuyệt đối KHÔNG xuất thông báo kiểm duyệt máy móc ra tin nhắn cho user.*
- Bất kỳ cơ chế bảo vệ nào khi can thiệp vào tầng tin nhắn gửi cho người dùng (`transform_llm_output`) đều phải ưu tiên tính trải nghiệm tự nhiên. Cảnh báo kỹ thuật nội bộ chỉ nên ghi vào file log (`logger.warning`), không được biến khung chat cá nhân của User thành bãi rác hiển thị mã lỗi và cảnh báo máy móc.
