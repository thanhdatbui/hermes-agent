# Triage & Khắc Phục: Nick Ký Sinh (Parasite Account) & False Positive Logout Trên Phone Farm

**Ngày ghi nhận:** 11/10/2026  
**Ngữ cảnh áp dụng:** Khi điều tra lỗi `[ACCOUNT_SWITCHER_FAILED]` / `ACCOUNT_MISSING` và xử lý nick rác / nick cũ chưa đăng xuất chiếm slot 8 tài khoản trên TikTok.

---

## 1. Bản Chất Nick Ký Sinh (Parasite / Rogue Account Drift)

1. **Giới hạn cứng TikTok Android:**
   - Ứng dụng TikTok trên Android giới hạn tối đa **8 tài khoản** đăng nhập đồng thời trên một thiết bị.
   - Khi farm có các đợt đổi slot, thay nick die hoặc reg nick mới:
     - Dữ liệu trong Excel master (`taikhoan_dat_v2_updated .xlsx`), `taikhoan_run_safe.xlsx` và `tiktok_tracker.db` đã được cập nhật nick mới.
     - **Trên thiết bị vật lý:** Nick cũ (ví dụ `samnga2403`) chưa từng được đăng xuất (logout) khỏi app TikTok.
2. **Hậu quả chiếm slot:**
   - Nick cũ tiếp tục nằm lì trong Switcher, chiếm 1/8 slot.
   - Khi ca nuôi mới nạp nick chính chủ (ví dụ `muyduyen4589` Slot 1), thiết bị không còn chỗ để đăng nhập hoặc nick chưa vào được máy.
   - Khi chạy ca đó, script tìm nick theo workbook không thấy -> ném `ACCOUNT_MISSING` -> Watchdog cảnh báo nhầm thành mất phiên.
3. **Cách truy vết nguồn gốc nick ký sinh:**
   - Tra cứu trong bảng `account_boost_state` hoặc `snapshots` cũ trong `D:/OneDrive/TaadaaData/tiktok_tracker.db`:
     `SELECT username, may, tik, updated_at FROM account_boost_state WHERE username LIKE '%<nick>%'`
   - Đa số nick ký sinh chính là nick cũ của **chính máy đó** ở các ca trước bị thay thế nhưng sót khâu logout.

---

## 2. Cạm Bẫy Tool Logout Báo Xong Giả (False Positive Exit 0)

1. **Nguyên nhân cốt lõi trong `do_logout_account.py`:**
   - Trên các dòng máy cũ (như Samsung Galaxy S7 SM-G930F), lệnh `shell uiautomator dump` bị văng lỗi OOM 137 (`SIGKILL`).
   - `atx-agent` (port 7912) thường xuyên bị lỗi trả về XML rỗng (`ATX_SESSION_EMPTY_XML`).
   - Khi hàm `dump_ui()` trả về `None`, script không ném lỗi mà nhảy vào nhánh `else:` bấm tọa độ mù:
     - Bấm Menu 3 gạch: `(1005, 150)`.
     - Bấm Cài đặt mù tại `(540, 1248)`: Trên TikTok v47, menu này nằm ở **cuối đáy bottom sheet (`y ≈ 1750`)**, nên tọa độ `1248` bấm trúng khoảng trống hoặc menu TikTok Studio / Công cụ sáng tạo.
     - Cuộn mù rồi bấm Đăng xuất mù tại `(540, 1750)` và xác nhận mù tại `(750, 1100)`.
     - Script in ra `DA HOAN TAT LOGOUT` và exit code 0, nhưng **thực tế không có tài khoản nào được đăng xuất**!
2. **Chướng ngại Onboarding / Security Prompt:**
   - Khi vừa switch sang nick cũ/lâu ngày không hoạt động, TikTok thường văng popup **"Thêm số điện thoại"** kèm bàn phím số che nửa màn hình.
   - Nếu không gửi 2 nhịp Back (`input keyevent 4`) để đóng bàn phím và đóng dialog, mọi thao tác tap vào tab Profile `(972, 1857)` đều bị bàn phím nuốt mất.

---

## 3. Quy Trình Chuẩn Xử Lý Dứt Điểm

1. **Kiểm tra thực tế qua WinRT OCR / Vision (Gate 6 Invariant):**
   - Tuyệt đối không tin tưởng exit code 0 của tool.
   - Bắt buộc chụp ảnh Switcher sau khi logout (`reports/m<N>_verified_logout.png`) và chạy WinRT OCR (`evidence_gate_verifier.py` / `winrt_ocr.py`) để đọc danh sách nick.
   - Chỉ xác nhận THÀNH CÔNG khi nick ký sinh đã biến mất khỏi kết quả OCR.
2. **Tọa độ chuẩn TikTok v47 trên màn hình 1080x1920 (SM-G930F):**
   - Sau khi switch nick: Gửi 2 lần `keyevent 4` để thoát bàn phím / popup số điện thoại.
   - Tab Hồ sơ: `(972, 1857)`.
   - Menu 3 gạch: `(1005, 150)`.
   - Cài đặt và quyền riêng tư: Tọa độ đáy bottom sheet `(540, 1750)` (thay vì `1248`).
   - Cuộn xuống đáy: 6 lần swipe `(540, 1600) -> (540, 400)`.
   - Nút Đăng xuất: Dòng chữ đỏ ở đáy màn hình `(540, 1820)`.
   - Nút Xác nhận Đăng xuất trong dialog: `(750, 1150)`.
