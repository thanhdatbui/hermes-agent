# Triage: Sự Cố Lỗi Script Upload Hàng Loạt & Phân Lập Rớt USB EHCI vs UI Drift (16/10/2026)

## 1. Bối Cảnh Sự Cố & Dấu Hiệu Nhận Biết
- **Cảnh báo Farm Alert:** `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT UPLOAD HÀNG LOẠT (15 máy lỗi script Upload) - Ca 2 - Phiên 2/2 (Chiều) (Row 4)`.
- **Tổng quan phân bố:**
  * **Farm Kibe (1-80):** 65 máy thành công, 3 máy lỗi script (M42, M45, M79), 1 máy hết video (M60).
  * **Farm Admin (201-280):** 45 máy thành công, 12 máy lỗi script (M211, M213, M221, M261, M262, M264, M267, M268, M274, M275, M278, M279), 16 máy hết video.

---

## 2. Quy Trình Triage Đối Soát 3 Tầng Phân Loại Lỗi

### Tầng 1: Phân Biệt "Rớt USB EHCI / Network Latency Tức Thời" vs "Lỗi Phần Cứng Thật" (11/15 máy)
- **Triệu chứng trong log:**
  * Kibe M42 (`ce06160692e07d0404`), M45 (`ce0716071586c80602`): Văng lỗi `[DEVICE_OFFLINE] device offline or ADB/USB disconnected: adb.exe: device not found`.
  * Kibe M79 (`ce0516059d279f3e03`), Admin M267 (`ce0616060a187c0b03`): Văng lỗi timeout lệnh kiểm tra interface VPN `tun0` (`adb command timed out: ... ip addr show tun0`).
  * Admin M261, M262, M264, M274, M275, M278, M279: Dính `[DEVICE_OFFLINE]` hoặc `[OPEN_TIKTOK_FAILED]` do ADB disconnect lúc cao điểm.
- **Bản chất kỹ thuật:**
  * Dưới áp lực tải song song lớn (>40 máy cùng chạy render, copy video, chụp màn hình và ATX-agent qua hub USB), buffer USB 2.0 EHCI bị nghẽn tức thời, khiến một số lệnh ADB bị rớt hoặc timeout >10s.
  * **CẠM BẪY PHÁN ĐOÁN:** Tuyệt đối không được vội vàng kết luận thiết bị hỏng hay tuột cáp USB vật lý.
- **Kiểm chứng O(1) phục hồi:**
  * Kibe local: Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra ngay sau ca chạy.
  * Admin remote: Chạy `python D:/Taadaa/tools/admin_ssh.py 'python -c "import subprocess; ... adb.exe devices"'`.
  * Nếu các máy đều hiển thị `device` (ONLINE), pin sạc ổn định: Khẳng định 100% lỗi **TRANSIENT (L0)**, không cần can thiệp sửa code hay tác động vật lý.

---

### Tầng 2: Phân Tích Lỗi Giao Diện UI & Idempotency Guard (4/15 máy)
- **Trường hợp Trễ duyệt Profile Grid (`POST_RECHECK_UNAVAILABLE` - M221 `@ngocbo3176`):**
  * Trong thư mục run (`run_<serial>_<timestamp>`), file bằng chứng `post-published-surface.png` đã sinh thành công, submission đã rời Composer.
  * Tuy nhiên bước `POST_RECHECK` quét 3 viewport thấy lưới video chưa kịp hiển thị clip mới (vẫn giữ baseline 2 clip do TikTok indexing delay).
  * **Xử lý chuẩn:** Script kích hoạt Idempotency Guard, dừng an toàn tại `MANUAL_REVIEW` để **chống repost trùng clip**. Tuyệt đối không bấm đăng lại thủ công.
- **Trường hợp Visual Gate Từ Chối Nút Tạo Video (`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` - M268):**
  * Log ghi nhận: `Visual create-button gate rejected screenshot: white=0.845, dark=0.052, cyan=0.000, red=0.034`.
  * Nút `[+]` ở giữa thanh điều hướng bị che khuất bởi popup, banner hoặc app đang ở subpage/onboarding. Cần clear Recent apps và đưa về Home sạch.
- **Trường hợp Lỗi Account Switcher (M211, M213):**
  * M211: `ACCOUNT_MISSING` (Menu switcher mở được nhưng không tìm thấy nick mục tiêu).
  * M213: `SWITCHER_NOT_CONFIRMED` (Marker switcher của TikTok không nhận diện được).
  * Cần kiểm tra lại trạng thái session / login của nick trên app trước ca kế tiếp.

---

### Tầng 3: Bẫy Nhảy Cóc Số Clip Video (Missing Video Number Jump - M60)
- **Triệu chứng:** Script upload dừng và báo *Hết video/Cần cào* cho Máy 60 (Folder `476`).
- **Hiện tượng kiểm tra:** Thư mục `D:\TIKTOK-videonuoinick\476` có tới 46 file `.mp4`, nhưng số video đã đăng trong Excel là 10.
- **Căn nguyên:** Các file trong thư mục gồm `1.mp4`, ..., `10.mp4`, rồi nhảy vọt lên `27.mp4`, thiếu mất file tuần tự tiếp theo là **`11.mp4`**.
- **Quy tắc:** Script upload yêu cầu video tuần tự `posted_count + 1`. Khi thiếu file tuần tự, runner bắt buộc fail-closed để tránh nhảy cóc nội dung. Cần render bù file clip thiếu.

---

## 3. Các Quy Tắc An Toàn & Tooling Bắt Buộc (Invariant Safeguards)

1. **Hard Gate #5 (Device Lock Required):**
   - Mọi thao tác ADB can thiệp trực tiếp vào thiết bị thật đều bị Coordinator Guard chặn nếu chưa giữ active lock trong `~/.codex/device-locks/`.
   - Bắt buộc bọc lệnh qua:
     ```bash
     python D:/Taadaa/tools/with_device_lock.py --machine <N> -- <command...>
     ```
2. **Invariant Soi Mắt Đọc Ảnh Trước Khi Gửi (Chống Gửi Cho Có Lệ):**
   - Sau khi chụp màn hình hiện trường thiết bị, bắt buộc gọi `browser_vision` (hoặc WinRT OCR) mở ảnh ra kiểm tra trước khi gửi.
   - **Xử lý màn hình đen:** Khi máy đang ở chế độ sleep/tắt màn hình tiết kiệm pin (`farm-idle-screen-and-app-healer`), ảnh screencap sẽ có màu đen hoàn toàn. **CẤM TUYỆT ĐỐI gửi ảnh màn hình đen kèm thẻ `MEDIA:` lên chat để đối phó**. Bắt buộc báo cáo trung thực trạng thái sleep của thiết bị.
3. **Kỹ Thuật Gọi Lệnh Qua `admin_ssh.py` Không Bị Lỗi Console Windows:**
   - Lệnh PowerShell/Python qua SSH trên Windows Admin-PC mặc định dùng codepage CP1252.
   - Khi in output JSON hoặc tiếng Việt qua `python -c`, bắt buộc thêm `sys.stdout.reconfigure(encoding="utf-8")` ở đầu script để tránh `UnicodeEncodeError`.
   - Giữ lệnh thực thi trên 1 dòng đơn (single-line), bọc trong dấu nháy đơn `'...'` trong terminal bash để tránh bash phân rã ký tự chấm phẩy `;` thành các câu lệnh độc lập.
