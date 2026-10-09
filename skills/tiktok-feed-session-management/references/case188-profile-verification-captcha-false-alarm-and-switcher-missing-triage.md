# Case 188: False Alarm Captcha do Substring 'verification' & Triage 'ACCOUNT_MISSING' Switcher trên S7 (23/09/2026)

## 1. Sự cố 1: Watchdog Gắn Nhãn Nhầm Captcha do Substring `verification` trong Bước `profile verification`

### Hiện tượng & Farm Alert
Trong batch nuôi acc / lướt feed (Row 5 - ca 20:00), hệ thống giám sát farm phát cảnh báo:
```text
⚠️ [CẢNH BÁO XÁC MINH / CAPTCHA TẠM THỜI]: Phát hiện 1 máy gặp captcha/xác minh (chưa mất phiên):
   • Máy M13: profile verification navigation-failed: TikTok focus lost
```

### Phân tích Root Cause
1. **Tiến trình thực tế trên thiết bị**: Máy M13 đã chạy đủ 100% quota video (`16/16` swipes hoàn tất an toàn trên FYP).
2. Sau swipe cuối cùng, TikTok bị trễ focus / văng về launcher. Cơ chế tự động relaunch lại TikTok về FYP thành công.
3. Khi vào bước `verify_profile` để kiểm tra tài khoản trước khi kết thúc ca, bước kiểm tra focus `verify_tiktok_focus` trả về `failed: TikTok focus lost`.
4. Script ghi nhận `stop_reason: profile verification navigation-failed: TikTok focus lost`.
5. **Cơ chế gây False Alarm**: Bộ phân loại `batch_aggregator.py` quét danh mục `CHALLENGE_KEYWORDS` có chứa từ khóa bare `"verification"`. Vì lý do này, cụm từ `"profile verification"` bị khớp nhầm vào nhóm Captcha/Challenge.
6. **Thực tế**: Máy 13 KHÔNG hề gặp Captcha hay Verify Identity, tài khoản vẫn sống và phiên lướt feed đã xong trọn vẹn.

### Quy chuẩn Triage & Điều Phối
- **Kỷ luật Coordinator**: Khi gặp alert chứa `"profile verification"`, Coordinator BẮT BUỘC kiểm tra `summary.txt` (mục `total_swipes_completed` / `completed_steps`). Nếu số swipe đã đạt quota (ví dụ 16/16), đây là lỗi mất focus ở khâu xác thực profile cuối phiên, KHÔNG ĐƯỢC báo User là máy bị dính Captcha.
- **Rule loại trừ trong Watchdog**: `batch_aggregator.py` cần loại trừ các cụm từ nội bộ: `"profile verification"`, `"preflight verification"`, `"proxy verification"`, và chỉ kích hoạt `CHALLENGE_KEYWORDS` khi có các marker thử thách thật (`"manual_challenge"`, `"puzzle"`, `"captcha"`, `"checkpoint"`).

---

## 2. Sự cố 2: Báo Động Nhầm Mất Phiên do Switcher Chưa Bung (`ACCOUNT_MISSING` trên S7)

### Hiện tượng & Farm Alert
```text
⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Phát hiện 1 máy dính lỗi login/mất phiên:
   • Máy M53: manual-needed:account-switcher-missing-expected: expected account not found in account switcher
```
Trong log `execution.log` của workflow:
```text
[ACCOUNT_SWITCHER] Account mgpovhrgnnq not visible in current viewport; attempting scroll
[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found. Cần MANUAL_REVIEW...
```

### Phân tích Root Cause
1. Trên Samsung Galaxy S7 (Android 7/8) chạy TikTok 47.0.3, khi chuyển nick qua `open_switcher`, tiến trình dump XML qua UiAutomator dễ bị OOM-kill (`ATX_SESSION_EMPTY_XML` / `SHELL_EXIT_137`).
2. Màn hình thiết bị thực tế vẫn đang đứng ở Profile cá nhân của nick cũ (ví dụ `@leivanlftxg`, Row 3), bảng Bottom Sheet Switcher (`rid='psy'` / `rid='g1z'`) chưa kịp mở ra.
3. Hàm `select_exact_account` trong `automation_core` khi thấy `ACCOUNT_MISSING` thực hiện 3 lần cuộn màn hình. Nhưng vì đang đứng ở Profile root, thao tác cuộn chỉ làm trôi grid video của trang cá nhân, không thể tìm thấy nick đích `mgpovhrgnnq`.
4. Runner ngắt tiến trình và ném lỗi `ACCOUNT_MISSING`, khiến hệ thống phát cảnh báo P0 mất phiên.

### Quy chuẩn Xử lý & Phục hồi (Recovery Protocol)
1. **Soi Screencap Trước Khi Kết Luận**:
   - Dùng WinRT OCR hoặc inspect screencap `account-switcher-profile.png` / `screen.png`.
   - Nếu màn hình là Profile root của nick khác chứ KHÔNG phải Bottom Sheet "Chuyển đổi tài khoản", đây là sự cố **mở Switcher thất bại**, không phải tài khoản bị xóa hay văng session.
2. **Quy trình Fast Login Bù An Toàn**:
   - Kiểm tra database `taikhoan_dat_v2_updated .xlsx` / workbook để lấy credentials.
   - Chạy lệnh Fast Targeted Login:
     ```bash
     python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID> --ss
     ```
     *(Kèm `--allow-parent-lock` nếu gọi lồng trong phiên nuôi acc đang giữ lock thiết bị)*.
3. **Chụp Ảnh Nghiệm Thu Trước Khi Teardown (Capture-Before-Cleanup)**:
   - Chụp ảnh màn hình đích (`D:/Taadaa/m<STT>_login_verified.png`) xác nhận tài khoản đã có mặt trong Switcher hoặc đã chuyển profile thành công trước khi gửi lệnh `am force-stop` và `KEYCODE_HOME`.
