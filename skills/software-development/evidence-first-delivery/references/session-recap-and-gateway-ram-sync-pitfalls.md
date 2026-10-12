# BÀI HỌC VẬN HÀNH EVIDENCE GATE & CHỐNG SPAM VI PHẠM TRÊN TIN NHẮN RECAP

Tài liệu đúc kết từ sự cố người dùng bức xúc khi bị spam liên tục cảnh báo vi phạm đỏ `[EVIDENCE FIRST GATE — FAIL-CLOSED VIOLATION]` trên các lượt trả lời thoại và recap kết quả đã hoàn thành.

---

## 1. CẠM BẪY LỆCH PHA GIỮA ĐĨA VÀ RAM (GATEWAY LONG-RUNNING DAEMON)

### Hiện tượng:
- Coordinator đã phát hiện nguyên nhân, dispatch sửa xong code trong plugin guard trên ổ đĩa.
- Tuy nhiên ở lượt trả lời tiếp theo, tin nhắn vừa gửi ra vẫn bị chèn đè cảnh báo vi phạm cũ. Người dùng lập tức bức xúc: *"Vẫn báo tiếp nè mày ngay trc khi mày soạn tn bảo fix r luôn"*.

### Căn nguyên:
- Hermes Gateway (`pythonw.exe -m hermes_cli.main gateway run`) là tiến trình daemon chạy ngầm dài hạn (long-running).
- Python chỉ import và nạp module plugin vào RAM lúc khởi động tiến trình. Các chỉnh sửa mã nguồn file `.py` trên đĩa **HOÀN TOÀN KHÔNG CÓ HIỆU LỰC TRONG RAM** nếu chưa khởi động lại tiến trình Gateway.

### Quy tắc xử lý:
- Sau khi chỉnh sửa plugin guard hoặc các hook trong `deploy/hermes-home/plugins/`:
- **BẮT BUỘC** kích hoạt script khởi động lại Gateway detached (`restart_gateway_detached.py` hoặc `restart_gateway_detached.ps1`):
  * Chờ 5 giây (`sleep 5`) để lượt trả lời hiện tại hoàn tất chuyển phát về Telegram.
  * Quét và dừng sạch toàn bộ tiến trình Gateway cũ (`p.kill()`).
  * Khởi động Gateway mới qua `Hermes_Gateway.vbs` để nạp mã nguồn mới vào RAM.

---

## 2. BẪY FALSE POSITIVE TRÊN TIN NHẮN RECAP & CÔNG VIỆC SỔ SÁCH / BACKEND

### Cạm bẫy:
- Khi User hỏi xác nhận: *"M làm xong hết r à"*, *"Xong chưa"*, *"Done"*.
- Coordinator trả lời giải trình, tóm tắt lại các việc đã làm trong phiên (ví dụ: *"Đã bật 2FA cho nick A, đã ghi vào Excel máy 266, đã login nick B"*).
- Hook `_enforce_evidence_first_gate` dùng regex quét cứng, bắt trúng các cụm từ `"đã bật 2FA"`, `"đã login"`. Do câu trả lời recap không đính kèm lại thẻ `MEDIA:`, hệ thống tự động coi đây là claim mới chưa có bằng chứng và nhồi banner vi phạm đỏ vào khung chat.

### Giải pháp cơ học đã chuẩn hóa:
1. **Kiểm tra Session-State Recap (`sess_state`):**
   - Trước khi kích hoạt vi phạm, gate bắt buộc đối soát danh sách claim phát hiện được với danh sách bằng chứng thị giác đã thẩm định thành công trước đó trong cùng phiên (`sess_state.get("verified_media_details")`).
   - Nếu toàn bộ các tài khoản/hành động đã có ảnh kiểm chứng hợp lệ trong phiên, tự động xác định đây là **Recap hợp lệ** và bỏ qua, không chèn banner vi phạm.
2. **Loại trừ các mệnh đề nghiệp vụ Backend / Sổ sách / Script:**
   - Trong `_detect_completion_claims`, mở rộng danh sách từ khóa loại trừ: `excel`, `sổ sách`, `totp`, `cli`, `terminal`, `kịch bản`, `tới ca`, `lúc nãy`, `trước đó`, `nhắc lại`, `thu dọn`.
   - Các hành động ghi file sheet, cấu hình 2FA qua script hay dọn dẹp không phải thao tác màn hình TikTok trực tiếp trên máy nên không bị đòi ảnh chụp giao diện điện thoại.
