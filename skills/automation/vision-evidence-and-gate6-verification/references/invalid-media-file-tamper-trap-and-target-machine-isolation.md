# Xử Lý Bẫy INVALID_MEDIA_FILE Do Lệch SHA-256 & Kỷ Luật Cô Lập Máy Mục Tiêu (Admin vs Kibe)

## 1. Hiện Tượng Sự Cố (2026-10-27)
- **Rò rỉ Egress Contradiction Gate:** Khi Agent gửi tin nhắn báo cáo kèm thẻ ảnh `MEDIA:D:/OneDrive/TaadaaData/admin_screen.png`, người dùng trên Telegram nhận được nguyên một khối văn bản kỹ thuật thô:
  ```text
  [CONTRADICTION_GATE_TRIGGERED]
  verdict: INVALID_MEDIA_FILE
  reason: MEDIA file SHA-256 differs from its signed receipt (tampered): D:/OneDrive/TaadaaData/admin_screen.png
  matched: D:/OneDrive/TaadaaData/admin_screen.png
  REQUIRED_NEXT_ACTION (chon dung 1, thuc hien ngay trong luot nay):
  ...
  ```
- **Lệch Target Machine (Kibe PC vs Admin PC):** Khi User yêu cầu kiểm tra và sửa game ĐTCL (TFT PBE) / Riot Client, Agent nhầm lẫn đối tượng, tự ý chạy các lệnh cấu hình và capture cửa sổ `computer_use(app="Riot Client")` trực tiếp trên **Kibe PC** (máy làm việc cục bộ của User, tài khoản `BóngVàoTrăng`), làm hỏng môi trường cục bộ trong khi máy **Admin (`192.168.110.119`)** vẫn kẹt lỗi.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ

### A. Bẫy SHA-256 Desync (`INVALID_MEDIA_FILE`)
1. Đường dẫn `D:/OneDrive/TaadaaData/admin_screen.png` là file ảnh chụp màn hình tái sử dụng (overwritten screenshot).
2. Khi Agent chụp màn hình mới từ máy Admin và ghi đè lên file này, hash SHA-256 của file trên đĩa đã thay đổi so với receipt đã được ký trước đó trong `vision_receipts.jsonl`.
3. Khi Agent gọi `browser_vision`, nếu receipt không được cấp mới đồng bộ với file mới, hàm `_verify_media_files_integrity()` trong `guard_media_vision_gate.py` phát hiện `current_sha256 != receipt.sha256` và kết luận `INVALID_MEDIA_FILE` (file bị sửa đổi/tampered).
4. **Lỗi Egress Leak:** Thay vì chặn ngầm và tự động kích hoạt retry hợp lệ, Gateway / Hook đã trả về nguyên văn prompt cưỡng chế nội bộ ra Telegram.

### B. Nhầm Lẫn Máy Admin vs Kibe PC
1. Theo invariant hệ thống, máy phụ trách game ĐTCL, render và phone farm Admin luôn là **máy Admin (`192.168.110.119`)**, truy cập độc quyền qua `D:/Taadaa/tools/admin_ssh.py`.
2. Agent dùng các công cụ desktop cục bộ (`computer_use`, `sc.exe`, process check local) trên Kibe PC thay vì SSH sang Admin. Điều này vừa vi phạm phân định mục tiêu, vừa gây gián đoạn công việc cá nhân của User trên Kibe PC.

---

## 3. Quy Trình Khắc Phục Chuẩn (Standard Operating Procedure)

### A. Quy Trình Cập Nhật Ảnh & Re-signing Receipt Khi Overwrite File
1. **Tuyệt đối không gửi thẻ `MEDIA:` khi chưa cấp receipt cho bản hash mới:**
   - Khi ghi đè bất kỳ file ảnh nào (như `admin_screen.png` hoặc screencap farm), BẮT BUỘC phải chạy lệnh đọc và ký lại receipt qua công cụ chính thức:
     ```bash
     python D:/Taadaa/tools/run_winrt_ocr.py "<duong_dan_anh>"
     ```
   - Xác nhận receipt mới đã được ghi nhận vào `vision_receipts.jsonl` với đúng SHA-256 của file mới trước khi đính kèm thẻ `MEDIA:`.
2. **Triệt tiêu Egress Leak ở Tầng Hook:**
   - Trong `guard_media_vision_gate.py`, hàm `transform_llm_output_check` hoặc hook Telegram egress phải đảm bảo: nếu bị `INVALID_MEDIA_FILE` hoặc `CONTRADICTION_GATE_TRIGGERED`, tuyệt đối CẤM truyền raw prompt này ra channel Telegram.

### B. Kỷ Luật Cô Lập Máy Mục Tiêu (Target Machine Isolation)
1. **Lệnh Game / ĐTCL / Riot / Render Admin:**
   - Mặc định 100% đích đến là **Máy Admin (`192.168.110.119`)**.
   - BẮT BUỘC thực thi qua script điều khiển từ xa: `python D:/Taadaa/tools/admin_ssh.py --powershell "..."`.
   - CẤM TUYỆT ĐỐI gọi `computer_use` (chụp màn hình Kibe PC), cấm kill tiến trình local, cấm sửa registry/service trên Kibe PC cho các task thuộc máy Admin.
2. **Kiểm Tra Trạng Thái ĐTCL / Riot Client Trên Admin:**
   - Chạy lệnh qua `admin_ssh.py`:
     ```powershell
     python D:/Taadaa/tools/admin_ssh.py --powershell "Get-Process Riot*, League*, TFT*, vgc -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, Responding; Get-Service vgc | Select-Object Status, StartType"
     ```
   - Chụp màn hình Admin bằng helper capture từ xa rồi sync về file đích, sau đó re-sign receipt trước khi gửi `MEDIA:`.
