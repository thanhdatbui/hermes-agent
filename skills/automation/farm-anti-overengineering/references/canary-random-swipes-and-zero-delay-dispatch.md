# Canary Random Swipes, Account Switch Recovery & Zero-Delay Dispatch khi nhận lệnh sửa

## 1. Tín hiệu kỷ luật: "Đang sửa trực tiếp hay gọi agent?" (06/09/2026)

### Tình huống vi phạm
Khi điều tra xong hoặc khi user đưa ra yêu cầu phát sinh như: *"Rồi sửa đi"*, *"mở rộng range X"*, Coordinator theo quán tính thực hiện một chuỗi lệnh `read_file` / `terminal grep` ở session chính để tìm dòng code trước khi dispatch.
Hành vi này dẫn đến:
- UI Telegram hiển thị iteration đếm lượt ở session chính, gây nghi ngờ: *"Đang sửa trực tiếp hay gọi agent?"*.
- Dính hard guard chặn terminal hoặc rủi ro sửa trực tiếp ở session chính vi phạm nghiêm trọng kỷ luật Coordinator vs Worker.

### Quy tắc Zero-Delay Dispatch khi nhận lệnh sửa
- Khi user chỉ đạo *"Rồi sửa đi"* hoặc giao task fix code bất kỳ: Coordinator **CHỈ ĐƯỢC PHÉP** xác định tên file/module cần sửa (Scope Lock trong 1 turn duy nhất), tuyệt đối không mở rộng đọc lan man.
- **BẮT BUỘC dispatch ngay lập tức** qua `delegate_task(goal=..., context=...)` để Worker Subagent nhận nhiệm vụ: đọc vị trí, patch code, chạy `py_compile` và kiểm thử độc lập trong context riêng.

---

## 2. Quy chuẩn Canary Swipes Random (2–4 Swipes)

### Triệu chứng & Vấn đề
- Chạy canary test với số lần swipe cố định (ví dụ luôn luôn 2 swipes) tạo dấu vân tay hành vi (behavioral footprint) máy móc trên thuật toán phát hiện bot của TikTok.
- Nếu swipe quá nhiều (>= 5-10 swipes), canary kéo dài thời gian vô ích (> 5-10 phút) làm nghẽn tiến độ kiểm chứng.

### Giải pháp kỹ thuật đã áp dụng
- Nâng trần dải tham số `-RecoveryTestSwipes` từ `[1..3]` lên `[1..4]` trên cả 2 tầng:
  1. PowerShell launcher: `D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1` (`[ValidateRange(1, 4)]`).
  2. Python runner: `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\multi_machine_feed_session.py` (`1 <= target <= 4` trong `_session_targets`).
- **Cú pháp Canary Test chuẩn:**
  ```powershell
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes (Get-Random -Minimum 2 -Maximum 5) -SkipAccountWorkbookSync -Run
  ```
  *(Lệnh `Get-Random -Minimum 2 -Maximum 5` sinh ngẫu nhiên 2, 3 hoặc 4 swipes, vừa tự nhiên vừa hoàn thành dưới 90 giây).*

---

## 3. Khắc phục lỗi `profile username still mismatched after switch`

### Bản chất lỗi
- Khi chuyển nick trên máy farm (ví dụ máy 58 chuyển từ `khoa4597` sang `lamnhu3003`), sau khi tap dòng nick trong switcher bottom sheet, TikTok cần thời gian transition và nạp identity profile mới. Nếu settle time quá ngắn (2–3s), profile đọc lại vẫn là nick cũ $\rightarrow$ văng lỗi `profile username still mismatched after switch`.
- Trước đây, hàm `_is_account_switcher_missing_expected_reason` chỉ bắt lỗi `account-switcher-missing-expected`, khiến trường hợp mismatch không được kích hoạt auto-login reconcile fallback mà rơi thẳng vào `manual-needed`.

### Cách xử lý triệt để trong `feed_swipe_smoke.py`
1. Tăng settle time sau khi tap row account switcher lên `random.uniform(3.5, 5.0)`.
2. Mở rộng `_is_account_switcher_missing_expected_reason(reason)` để nhận diện thêm `"profile username still mismatched after switch"` $\rightarrow$ kích hoạt `_maybe_recover_missing_account_via_login` tự động login/phục hồi nick.
