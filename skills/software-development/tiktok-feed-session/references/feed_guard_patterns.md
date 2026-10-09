# Feed Guard & Environment Execution Patterns

## 1. Main Feed False-Positive Guard in Popup Detectors

### Vấn đề
Các marker text chung như `"Follow lại"`, `"Theo dõi lại"`, `"Mời bạn bè"`, `"Tìm bạn bè"` trong `detect_follow_friends_suggestion_popup` (`benign_popup.py`) và `_detect_follow_friends` (`benign_popup_registry.py`) có thể vô tình match trúng văn bản trên video caption, card tác giả, hoặc nhãn giao diện trong luồng For You / Bảng tin. Điều này dẫn đến việc nhận diện nhầm màn hình Feed chính là popup gợi ý kết bạn và liên tục cố bấm đóng/thoát nhầm.

### Giải pháp (Guard Feed Chính)
Trong cả 2 hàm phát hiện:
1. Trích xuất text từ OCR và XML tree.
2. Kiểm tra dấu hiệu Feed chính:
   - Tab feed: `"Đề xuất"` / `"de xuat"`, `"Dành cho bạn"` / `"danh cho ban"`, `"For You"`.
   - Hoặc thanh điều hướng `"Trang chủ"` / `"Home"` kết hợp cùng các nút tương tác feed (`"Đăng lại"` / `"repost"`, `"Bình luận"` / `"comment"`, `"Chia sẻ"` / `"share"`).
3. Nếu màn hình là Feed chính:
   - Chỉ xem là popup khi có sự xuất hiện của modal dialog thực sự (`android.app.Dialog`) HOẶC có nút đóng ngữ nghĩa hợp lệ (`_find_follow_friends_semantic_close_control(root) is not None`).
   - Ngược lại, lập tức `return False` để tránh chặn luồng lướt video.

---

## 2. Windows Bash / MSYS PYTHONPATH Shadowing Pitfall (PIL ImportError)

### Triệu chứng
Khi chạy PowerShell script hoặc Python runner từ bash/terminal:
```
ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
```
Do môi trường bash của agent tự động export biến `PYTHONPATH` trỏ vào venv của Hermes, khiến Python 3.12 của hệ thống nạp nhầm binary C-extension không tương thích.

### Cách xử lý
Luôn dọn sạch `PYTHONPATH` trước khi gọi PowerShell hoặc Python chạy farm:
```bash
env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines 9 -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
hoặc:
```bash
env -u PYTHONPATH python ...
```

---

## 3. Device Lock Preflight trên Máy Farm

### Cơ chế
Hệ thống nuôi acc dùng lock file trung tâm đặt tại `C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json`. Khi một worker hoặc tiến trình khác đang giữ lock (ví dụ PID còn sống), coordinator sẽ fail-closed:
- Status: `manual-needed`
- Reason / Event: `skipped-device-locked`
- Message: `multi-machine-feed-session has locked machine(s) requiring operator decision`

Khi gặp tình trạng này trong canary run, kiểm tra `run_manifest.json` và `machines/machine_<N>/<run_id>/log.jsonl` để biết PID và thời gian lock trước khi can thiệp.
