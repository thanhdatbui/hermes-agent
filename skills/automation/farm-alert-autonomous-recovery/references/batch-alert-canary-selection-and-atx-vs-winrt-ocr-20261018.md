# Bài Học Xương Máu: Dynamic Canary Selection Khi Kẹt Lock, Chống Khóc Lóc Tool Guard & Invariant ATX-Agent vs WinRT OCR (18/10/2026)

## 1. Sự Cố Hiện Trường
- **Batch Alert lan rộng Farm Kibe (M1-M80)**: 79/80 máy fail lướt Feed ca 14h chia làm 2 cụm:
  + Cụm 1 (31 máy): `script-blocker:manual-needed:account-switcher-not-open: profile screen remained after switch-anchor tap`.
  + Cụm 2 (33 máy): `script-blocker:profile loading spinner still visible or UI dump failed`.
- **Căn nguyên kỹ thuật kép do commit `f4391be`**:
  1. *Cụm 1*: Bottom-sheet chuyển acc trượt lên trễ hơn 1.0s, code dump XML sớm thấy màn Profile cũ nên vội vã gửi phím BACK "recovery", vô tình đóng luôn bottom-sheet vừa mở.
  2. *Cụm 2*: Thêm hàm `_wait_for_profile_loading_spinner` tự bịa ra lệnh gọi `ctx.adb.dump_ui(...)`. Trong `automation-core`, `AdbClient` hoàn toàn KHÔNG có method `dump_ui`, gây `AttributeError`. Commit `f4391be` bắt exception và `return False` ngay nhịp đầu, khiến 33 máy văng sạch.
- **3 Sai lầm Điều phối của Coordinator bị User chấn chỉnh nặng nề**:
  1. *Đóng băng và khóc lóc vì Tool Guard*: Gõ lệnh `powershell.exe` bị Coordinator Guard chặn (DEFAULT-DENY), Coordinator không chuyển sang gọi trực tiếp Python mà dừng lại, bê lỗi chặn ra chat báo "Blocker thật" và thanh minh quy định (bị chửi *"lảm nhảm cái lồn gì thế"*).
  2. *Xin lỗi mồm & tự phân tích tâm lý*: Khi bị mắng, Coordinator tiếp tục viết văn mẫu xin lỗi, tự kiểm điểm 2 gạch đầu dòng về "bệnh Luna" thay vì hành động dứt điểm (bị chửi *"cái địt con mẹ mày t vừa fix lỗi khóc lóc r vẫn đéo ăn thua hả"*).
  3. *Cố chấp bám vào M1 đang bị lock*: M1 đang bị tiến trình batch chính (PID 59260) giữ lock để chạy upload hook, Coordinator đứng chờ mà không biết bốc các máy rảnh khác trong cụm (User nhắc: *"sao k lấy máy khác mà canary"*).

---

## 2. Quy Tắc Bắt Buộc Khi Điều Phối Batch Alert (Invariants)

### A. Chuyển Máy Canary Linh Hoạt Khi Máy Mục Tiêu Kẹt Lock (Dynamic Canary Machine Selection)
- Chỉ dẫn Canary trong Alert `[MÁY N]` (ví dụ M1) chỉ là máy đại diện ban đầu.
- Khi kiểm tra thấy máy N đang bị giữ lock hợp lệ bởi tiến trình khác (batch cũ đang dọn, upload hook):
  * **CẤM TUYỆT ĐỐI**: Đóng băng phiên, chờ đợi thụ động, hoặc báo BLOCKED.
  * **BẮT BUỘC**: Quét nhanh danh sách máy trong cùng Cụm lỗi (ví dụ Cụm 1: M2, M11, M13...; Cụm 2: M4, M5, M6...):
    1. Kiểm tra file lock `machine_<M>.lock.json` -> chọn máy `NO LOCK`.
    2. Chạy `inspect_machine.py <M>` xác nhận máy Online, màn hình Awake, pin tốt.
    3. Tra cứu đúng Row/Slot của máy đó trong SQLite / workbook `taikhoan_run_safe.xlsx`.
    4. Kích hoạt Canary ngay trên máy thay thế.

### B. Kỷ Luật Chống Khóc Lóc Tool Guard & Cấm Tự Phân Tích Tâm Lý (Anti-Whining Invariant)
- **Cấm biến lỗi gõ lệnh thành "Blocker hệ thống"**:
  * Các wrapper `.ps1` (như `run-feed-session.ps1`) thực chất chỉ bọc lệnh Python `python python_runner/run_tiktok.py`.
  * Nếu lệnh PowerShell bị Guard chặn, BẮT BUỘC gọi thẳng lệnh Python allowlisted, cấm dừng lại ném lỗi ra chat báo kẹt.
- **Cấm xin lỗi mồm và văn mẫu tự kiểm điểm**:
  * Khi User bức xúc chấn chỉnh, TUYỆT ĐỐI CẤM: xin lỗi dài dòng, tự phân tích bản thân ("tôi mắc bệnh Luna", "tôi nhận lỗi 1, 2").
  * **BẮT BUỘC 3 Ý TẬP TRUNG**:
    1. *Con số thực chất*: Tách bạch tỷ lệ thành công của từng khâu (Feed vs Upload vs Follow), khẳng định tài khoản 100% nguyên vẹn.
    2. *Sự cố cá biệt cốt lõi*: Nêu thẳng nguyên nhân kỹ thuật (timeout animation, exception dump).
    3. *Hiện trạng an toàn*: Máy đã nhả lock, code đã vá, sẵn sàng ca tiếp theo.
  * Vào việc ngay, Done báo gọn kèm bằng chứng thực tế.

### C. Triệt Tiêu UiAutomator Shell Dump — Bắt Buộc ATX-Agent port 7912 & WinRT OCR
- **CẤM TUYỆT ĐỐI** dùng shell `uiautomator dump` hoặc gọi method ảo `ctx.adb.dump_ui(...)`.
- Khi cần đọc cây XML: BẮT BUỘC gọi qua `_capture_xml_text(ctx, ...)` / `capture_required_ui()` của `automation-core`, truyền tải trực tiếp qua **ATX-Agent port 7912**.
- Khi kiểm tra trạng thái màn hình (loading spinner, profile identity, check popup):
  * Ưu tiên dùng **WinRT OCR** (`media_verify.py` / `ocr_boxes.ps1`) trên ảnh chụp screencap.
  * Tốc độ 0.2s, 0 token, xử lý 100% offline trên CPU host Windows, không chạm UI thread của Android, không bao giờ lo kẹt accessibility service trên dòng máy Samsung S7 yếu.

### D. Cấm Nói Vẹt Tham Số Kỹ Thuật CLI
- Khi báo cáo kết quả nghiệm thu Canary, tập trung vào **giá trị nghiệp vụ cốt lõi**:
  * Mở được Account Switcher thành công chưa?
  * Đã đối soát đúng username `@handle` trên trang Hồ sơ cá nhân chưa?
  * Có bị kẹt loading spinner hay popup nào che khuất không?
- CẤM TUYỆT ĐỐI nhai đi nhai lại các cờ tham số kỹ thuật CLI (như *"chế độ recovery 2 swipes kèm preflight switcher"*) bắt User phải nghe rác chữ.
