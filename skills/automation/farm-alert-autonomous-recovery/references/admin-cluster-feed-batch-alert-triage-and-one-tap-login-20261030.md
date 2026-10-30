# Admin Cluster Feed Batch Alert Triage & One-Tap Login False Positive (2026-10-30)

## 1. Bối Cảnh & Triệu Chứng Cảnh Báo
Watchdog phát cảnh báo khẩn cấp toàn giàn Admin (201-280) cho quy trình Lướt Feed:
- Tỷ lệ lỗi toàn batch báo động: 22.8% (18/79 máy thất bại), nhưng `Số cụm lỗi hệ thống: 0`.
- Cảnh báo P0 mất phiên / văng account: `Máy M270: login/account screen detected`.

## 2. Quy Trình Đối Soát Hiện Trường O(1) Bằng Bằng Chứng Mắt Thật
1. **Trích xuất trạng thái phần cứng O(1):**
   ```bash
   python D:/Taadaa/tools/inspect_machine.py M270
   ```
   Xác nhận: SM-G930F, Pin 70% Charging, Màn hình Awake, Wi-Fi 192.168.110.19, Proxy 192.168.110.2:10031. Focus: `LauncherActivity` (đã teardown an toàn).

2. **Định vị & soi mắt artifact của ca chạy gần nhất:**
   - File artifact tại `attempt_1`:
     `D:\Taadaa\runtime\admin\live\2026-10-30\row-0-120016\20261030-120411\machines\machine_270\20261030-120411\artifacts\device_4dbd771ab0\account_5d924bb0d8\feed-session-smoke\profile_preflight_identity_guard\attempt_1\screen.png`
   - Chạy WinRT OCR O(1) kiểm tra nội dung text nhanh (<30s):
     ```bash
     python D:/Taadaa/tools/run_winrt_ocr.py "<screen.png>"
     ```
   - Nạp vào trình duyệt & gọi `browser_vision` xác thực trực quan (Invariant LLM Soi Mắt Đọc Ảnh):
     - `browser_navigate(url="file:///<screen.png>")`
     - `browser_vision`: Xác nhận giao diện "Chào mừng bạn trở lại", danh sách 3 tài khoản nguyên vẹn (`ngophuc1612`, `duongthinh4075`, `namsu2668`), các nút "+ Thêm tài khoản khác", "Quản lý tài khoản". Không lỗi hiển thị hay màn hình đen.

3. **Bóc tách nguyên nhân gốc (Root Cause):**
   - Hàng lướt feed hiện tại là Row 4 (mục tiêu `@huynhthiloan112`), nhưng máy M270 mới nạp 3/8 slot tài khoản, chưa có `@huynhthiloan112`.
   - `profile_preflight_identity_guard` phát hiện màn hình One-Tap Login và nick mục tiêu vắng mặt, đã dừng an toàn (*fail-closed*) để chống lướt nhầm nick.
   - Watchdog bắt trúng nhãn `login/account screen detected` và phân loại nhầm thành P0 mất phiên.
   - **Kết luận:** BÁO ĐỘNG GIẢ (FALSE POSITIVE), toàn bộ tài khoản hiện có trên thiết bị không bị văng phiên.

4. **Giải mã ảo ảnh tỷ lệ thất bại (Premature Snapshot):**
   - Khi đối soát `summary.txt` lúc phiên kết thúc hoàn tất: **71/80 máy thành công (88.75%)**.
   - Chỉ 9 máy dừng/lỗi: 5 failed (3 máy lag focus Launcher, 2 máy popup ngoài danh mục), 4 manual-needed (timeout navigation, thiếu nick chưa nạp).
   - Con số 18 máy lỗi trong cảnh báo phát sinh do watchdog lấy mẫu khi các máy chưa hoàn tất và chưa flush đầy đủ log về `log.jsonl`.
