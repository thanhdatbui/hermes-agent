# Profile Verification Focus Lost vs Captcha False Alarm & Switcher Missing Triage (2026-09-23)

## 1. Sự cố 1: False Positive "Cảnh Báo Xác Minh / Captcha Tạm Thời" do Substring `verification`

### 1.1. Hiện tượng trên Fleet (Farm Alert)
Trong batch nuôi acc / lướt feed (Row 5 - ca 20:00), watchdog phát cảnh báo:
```text
⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện 1 máy gặp captcha/xác minh (chưa mất phiên):
   • Máy M13: profile verification navigation-failed: TikTok focus lost
```

### 1.2. Root Cause (Bẫy từ khóa toàn cục trong Watchdog / Batch Aggregator)
- **Hiện trường thực tế**: Máy 13 đã hoàn thành trọn vẹn 16/16 lượt lướt video (`swipe_16_after` OK). Sau khi kết thúc lướt, TikTok bị gián đoạn văng về Launcher. Script tự động relaunch lại TikTok vào For You feed thành công.
- Tuy nhiên, bước kiểm tra cuối cùng `verify_profile` (vào hồ sơ để kiểm tra nick trước khi kết thúc ca) bị fail do mất focus (`verify_tiktok_focus` -> `failed: TikTok focus lost`).
- Script ghi nhận lỗi: `stop_reason: profile verification navigation-failed: TikTok focus lost`.
- **Cơ chế gây false alarm**: `batch_aggregator.py` quét danh sách `CHALLENGE_KEYWORDS` có chứa từ khóa bare `"verification"`.
- Vì lý do này, cụm từ `"profile verification"` bị so khớp nhầm với Captcha / Identity Challenge của TikTok, dẫn đến việc phân loại sai vào nhóm `login/GMS/verification`.
- **Thực tế**: Máy 13 KHÔNG hề gặp Captcha, KHÔNG gặp Identity Verification, tài khoản hoàn toàn bình thường 100%.

### 1.3. Quy tắc phòng chống & Phân loại chuẩn (Watchdog Invariant)
1. **Loại trừ cụm từ nội bộ**: Khi phân loại Captcha/Challenge trong `batch_aggregator.py` hoặc watchdog, bắt buộc loại trừ (exclude) các cụm từ nội bộ của workflow:
   - `"profile verification"`
   - `"preflight verification"`
   - `"proxy verification"`
2. **Yêu cầu từ khóa đặc thù cho Captcha thật**:
   - Chỉ gắn cờ `CHALLENGE_KEYWORDS` khi gặp các marker thực sự của thử thách TikTok: `"manual_challenge"`, `"verify-bar-close"`, `"puzzle"`, `"captcha"`, `"xác minh danh tính"`, `"identity verification"`, `"checkpoint"`.
3. **Thao tác điều phối của Coordinator khi nhận alert này**:
   - Kiểm tra ngay log `summary.txt` và artifact screencap tại bước `verify_profile_relaunch_check`.
   - Nếu thấy app đã quay lại Feed For You (`detected_screen: for-you`) hoặc `swipe_count` đã đạt đủ quota (16/16), lập tức giải tỏa cảnh báo Captcha cho User, tránh hoang mang vô căn cứ.

---

## 2. Sự cố 2: `account-switcher-missing-expected` do Switcher Chưa Kịp Bung (S7 / TikTok 47.x)

### 2.1. Hiện tượng & Triệu chứng lỗi
```text
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/mất phiên:
   • Máy M53: manual-needed:account-switcher-missing-expected: expected account not found in account switcher
```
Trong `execution.log` của workflow:
```text
[ACCOUNT_SWITCHER] Account mgpovhrgnnq not visible in current viewport; attempting scroll
[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW...
```

### 2.2. Root Cause
1. **UiAutomator OOM / Trễ render trên Samsung S7**:
   - Khi runner gọi `open_switcher` trên TikTok 47.0.3, lệnh dump UI XML gặp sự cố OOM-kill (`ATX_SESSION_EMPTY_XML` / `SHELL_EXIT_137`).
   - Màn hình thực tế vẫn đang đứng ở trang Profile của nick cũ (`@leivanlftxg`, Row 3), bảng Bottom Sheet (`rid='g1z'` / `rid='psy'`) chưa bung ra.
2. **Logic cuộn mù trong `select_exact_account`**:
   - Hàm `select_exact_account` khi thấy `ACCOUNT_MISSING` liền tự động vuốt màn hình 3 lần từ 80% lên 50% chiều cao để cuộn danh sách.
   - Nhưng vì màn hình vẫn là Profile root (không phải Switcher Bottom Sheet), thao tác cuộn vô tình cuộn feed video của profile thay vì danh sách nick.
   - Kết quả: `find_exact_account` vẫn trả về `ACCOUNT_MISSING`, dẫn đến báo động giả "Mất phiên / Văng account".

### 2.3. Quy trình Triage & Phục hồi chuẩn (Recovery Protocol)
1. **Kiểm tra Artifact Screencap trước khi phán đoán**:
   - Dùng WinRT OCR hoặc inspect ảnh `account-switcher-profile.png` / `screen.png`.
   - Nếu ảnh là màn hình Profile cá nhân chứ không phải Bottom Sheet `Chuyển đổi tài khoản`: Khẳng định đây là lỗi **mở Switcher thất bại**, không phải tài khoản bị xóa hay văng nick khỏi app.
2. **Tự động đăng nhập bù / xác nhận tài khoản**:
   - Nếu nick thực sự chưa có trong switcher: Không hỏi nhảm User, chạy ngay script Fast Targeted Login:
     ```bash
     python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss
     ```
     *(Lưu ý: Nếu chạy lồng trong tiến trình nuôi acc đang giữ lock, bắt buộc kèm cờ `--allow-parent-lock`)*.
3. **Kỷ luật chụp ảnh nghiệm thu (Capture-before-Cleanup)**:
   - Subagent/Worker bắt buộc chụp ảnh màn hình đích (`D:/Taadaa/m<STT>_login_verified.png`) xác nhận tài khoản đã đăng nhập hoặc đã hiển thị trong Switcher trước khi thực hiện teardown.
