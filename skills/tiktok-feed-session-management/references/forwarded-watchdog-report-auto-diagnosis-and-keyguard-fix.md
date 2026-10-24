# Forwarded Watchdog Report Auto-Diagnosis & Keyguard Fix

## 1. Nguyên Tắc Xử Lý Khi User Forward Báo Cáo Nuôi / Watchdog
Khi người dùng chuyển tiếp (forward) bản tin báo cáo của cronjob watchdog (ví dụ: `📊 [TIKTOK NUÔI ACC] Ca 1 hoàn tất (Row 2)... + Fail (20): M1... Lỗi mở/focus App TikTok`):
- **CẤM TUYỆT ĐỐI hỏi lại** các câu hỏi mơ hồ (*"Bạn có muốn tôi sửa không?"*, *"Tôi nên làm gì?"*).
- **Hành động mặc định:** Tự động xem bản tin forward là **Lệnh Triage & Code Fix O(1)**.

### Quy trình giải mã O(1):
1. **Xác định Repo nguồn:**
   - `[TIKTOK NUÔI ACC]` -> `D:/Taadaa/tiktok-luot nuoi acc`
   - `[TIKTOK FOLLOW]` -> `D:/Taadaa/tiktok-follow`
   - `[TIKTOK VIDEO]` -> `D:/Taadaa/tiktok-video`
2. **Dựng đường dẫn log O(1):**
   - Bóc tách Cụm (`【Kibe Local】` -> `kibe`, `【Farm Admin】` -> `admin`), Ngày, Row và `(Run: {run_id})`.
   - Đường dẫn: `D:/Taadaa/runtime/{cluster}/live/{date}/row-{row}-*/{run_id}/machines/machine_{M}/{run_id}/`
3. **Map nhóm lỗi sang file code chịu trách nhiệm:**
   - `Lỗi mở/focus App TikTok`: `python_runner/flows/device_prepare.py`
   - `Lỗi thao tác vuốt (Swipe)`: `python_runner/flows/feed_session.py`
   - `Lệch Profile/Nick TikTok` / `Kẹt Account Switcher`: `python_runner/flows/account_switcher.py`
   - `Chưa gán Proxy / Proxy :0` / `Nghẽn đường truyền Proxy / 4G`: network / proxy config
4. **Trích xuất bằng chứng 1 máy đại diện:**
   - Đọc trực tiếp `summary.txt` hoặc `log.jsonl` của 1 máy tiêu biểu trong nhóm lỗi.
   - Dùng `python D:/Taadaa/tools/inspect_machine.py <M>` nếu cần kiểm tra trạng thái màn hình hiện tại.
5. **Thực thi bản vá O(1) & Canary Gate:**
   - Soạn patch <= 30 dòng, chạy focused unit test (<30s).
   - Chạy kiểm chứng Canary trên máy thật qua `python D:/Taadaa/tools/canary_runner.py --repo "tiktok-luot nuoi acc" --auto-device`.
   - Soi mắt đọc ảnh chụp nghiệm thu qua `browser_vision` / WinRT OCR trước khi báo kết quả.

---

## 2. Bẫy Nghẽn SystemUI / Keyguard Trên Samsung S7 Android 8
### Triệu chứng:
Hàng loạt máy rớt với lỗi: `prepare-tiktok failed to focus TikTok after launch`, dumpsys focus bị kẹt tại `mCurrentFocus=Window{... com.android.systemui/...}`. Cá biệt có máy bị kẹt dumpsys tới hơn 50 phút.

### Nguyên nhân gốc:
1. Trên Samsung Galaxy S7 Android 8, khi máy ở màn hình khóa Keyguard (Swipe to unlock), lệnh `input keyevent 4` (phím BACK) hoàn toàn vô hiệu, không thể giải phóng màn hình khóa.
2. Vòng lặp Auto-Healing chỉ thăm dò 1 nhịp sau 2.0s. Khi farm tải cao, khởi động cold boot của TikTok mất từ 3-8s mới chiếm được focus, dẫn tới việc phán đoán sai và abort sớm.

### Giải pháp kỹ thuật chuẩn:
Trong `python_runner/flows/device_prepare.py`:
1. **Giải phóng Keyguard dứt điểm:** Khi phát hiện `com.android.systemui`, gửi ngay `input keyevent 82` (KEYCODE_MENU/Unlock), đồng thời bổ sung vuốt fallback `input swipe 540 1400 540 500 300`.
2. **Polling Auto-Healing đa nhịp:** Thăm dò 4 nhịp x 1.0s; nếu nhịp 2 chưa có focus thì chủ động gửi intent tường minh vào `com.ss.android.ugc.aweme.splash.SplashActivity` để kéo TikTok lên foreground.

---

## 3. Canary Runner Cho Repo Nuôi Feed (`canary_runner.py`)
Khi chạy canary cho repo `tiktok-luot nuoi acc`:
- Runner kiểm tra chuỗi `Status: success` hoặc `multi-machine-feed-session completed` trong stdout (không dùng `parse_follow_result` của repo follow).
- Tự động trích xuất thư mục `Artifacts: ...` từ stdout để lấy ảnh chụp nghiệm thu `screen.png` từ bước profile preflight hoặc swipe sau cùng, copy vào file nghiệm thu chuẩn và sinh biên nhận `.canary_receipt.json`.
