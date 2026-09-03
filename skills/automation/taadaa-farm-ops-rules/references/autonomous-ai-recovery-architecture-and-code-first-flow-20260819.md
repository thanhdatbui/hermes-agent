# Autonomous AI Recovery Architecture & Code-First Order (2026-08-19)

## 1. Nguyên Tắc Cốt Lõi: Code-First & Test-at-Stuck-State
- **Quy tắc bất di bất dịch:** `AI SUY LUẬN ➔ VIẾT CODE VÀO SCRIPT TRƯỚC ➔ CHẠY HÀM VỪA VIẾT LÊN MÁY ĐANG KẸT ➔ TEST PASS MỚI AUDIT, COMMIT & BÁO CÁO`.
- **CẤM TUYỆT ĐỐI bấm tay / bắn lệnh ADB thô trước:** Bắn lệnh ADB thô trực tiếp sẽ làm mất hiện trường lỗi, khiến không còn màn hình thực tế để kiểm chứng hàm Python vừa viết có hoạt động thật hay không. Mọi thao tác giải phóng thiết bị bắt buộc phải do chính đoạn code vừa viết thực thi.
- **Không ép máy về Feed:** Kẹt ở bước nào (Login, OTP, Captcha, DOB, Profile, Popup, Live, Khảo sát...) thì AI suy luận cách giải quyết đúng ngay tại bước đó để máy tiếp tục luồng.

## 2. Kiến Trúc Phân Tầng Tự Hành (Autonomous Pipeline)
1. **Producer (Script nuôi acc):**
   - Khi gặp lỗi dừng phiên ➔ Chụp ảnh đóng dấu Banner Đỏ `[MAY XX] - HH:MM DD/MM`.
   - Gửi Tin nhắn 1 vào nhóm Telegram `Farm Alerts` (`-5373649734`).
   - Giữ nguyên hiện trường lỗi trên máy (không tắt app, không bấm Home).
   - Kích hoạt ngầm (`subprocess.Popen` không block): `python -m ai_recovery.agent --machine XX --serial ...`.
2. **Autonomous Agent (`python_runner/ai_recovery/agent.py`):**
   - **Bước 1:** Lấy Per-Device Lock (TTL 5 phút).
   - **Bước 2:** `screen_verifier` (dHash Hamming distance) kiểm tra máy còn ở đúng màn hình kẹt không (nếu người dùng bấm tay hoặc máy tự đổi thì dừng lại an toàn).
   - **Bước 3:** Gọi Vision Client (`ag/claude-opus-4-6-thinking` qua 9Router port 20128) đọc ảnh kẹt + XML dump để phân tích và sinh đoạn code rule mới.
   - **Bước 4:** Gọi Plan-Review (`gpt-5.6-terra` combo plan-review max) audit git diff (`APPROVED`).
   - **Bước 5:** Patch code mới vào repo (`feed_swipe_smoke.py` hoặc `benign_popup.py`).
   - **Bước 6:** Kích hoạt chính hàm vừa code chạy thử trực tiếp trên máy đang lỗi tại hiện trường.
   - **Bước 7:** Chạy test suite `pytest` xác nhận không có lỗi hồi quy.
   - **Bước 8:** `git commit & push` master đồng bộ toàn farm.
   - **Bước 9:** Bắn Tin nhắn 2 (*Hướng sửa & Kết quả*) vào Telegram `Farm Alerts`.
3. **Auto-Rollback 15 phút:**
   - Nếu bản vá mới gây lỗi tương tự trên $\ge 3$ máy trong 15 phút ➔ Tự động `git revert` và gửi cảnh báo khẩn cấp về nhóm.

## 3. Quản Lý Key 9Router & Fallback Safety
- API Key chuẩn của 9Router cục bộ nằm trong bảng `apiKeys` của `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` ➔ Nạp vào `.env` thành `NINEROUTER_API_KEY`.
- Phải đảm bảo key hợp lệ để tránh agent rơi vào fallback an toàn.

## 4. Xử Lý Khởi Động & Recents Rỗng (`startup.py`)
- Khi máy vừa mở khóa mà danh sách Recent Apps rỗng (chưa có app nào chạy ngầm), hàm `close_all_recent_apps` không tìm thấy nút "Đóng tất cả" ➔ Script gửi phím Home về màn hình chính và coi như thành công (`safe-pass`), TUYỆT ĐỐI KHÔNG được ném exception làm sập `prepare_android_for_automation` hay ngắt phiên.
