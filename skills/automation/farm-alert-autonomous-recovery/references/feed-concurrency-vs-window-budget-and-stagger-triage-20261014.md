# Triage: Giới Hạn Concurrency Cửa Sổ Ca Nuôi vs Stagger Khởi Động USB Farm (14/10/2026)

## 1. Bối Cảnh Sự Cố & Lỗi Kép Lan Rộng
- **Hiện tượng:** Watchdog báo lỗi hàng loạt trên 44/80 máy:
  * 26 máy dính `proxy-vpn:device is offline or ADB/USB disconnected`.
  * 10 máy dính `focus-device-issue:prepare-tiktok failed to focus TikTok after launch`.
- **Cơ chế lỗi:** Nghẽn bus USB EHCI (Intel X99) do 25 worker cùng dump UI XML và screenshot qua ADB socket. Khi một nhánh hub sụt, 26 máy rớt kết nối đột ngột tạo ra bão timeout socket, làm 10 máy còn lại bị nghẽn lệnh launch quá 15s.
- **Tự phục hồi sau Reboot:** Sau khi host reboot (kiểm tra O(1) qua `psutil.boot_time()`), BIOS thực hiện System Bus Reset giải phóng toàn bộ thanh ghi EHCI, 78/80 máy tự động nhận lại `device` online sạch sẽ.

---

## 2. Bài Học Chỉnh Đốn Của User (User Correction) & Invariant Cửa Sổ Thời Gian

### 2.1. Sai lầm trực giác của Agent
- Thấy bus USB bị quá tải $\rightarrow$ Vội vàng giảm `MaxWorkers` từ 25 xuống 16 để "an toàn".
- Phản hồi chỉnh đốn của User: *"T sợ k đủ time chạy á chứ. Lúc giảm worker 40 xuống 25 đã gây tăng time cả phiên lên bn r"*.

### 2.2. Đối soát dữ liệu thực tế lịch sử chạy farm
- **Khi `MaxWorkers = 40` (trước 10/10):**
  * Thời gian 1 phiên: **45 – 65 phút** (`80 máy / 40 = 2 batches`).
- **Khi hạ `MaxWorkers = 25` (từ 11/10):**
  * Thời gian 1 phiên: **75 – 90 phút** (`80 máy / 25 = 3.2 -> 4 batches`), chạm trần 120 phút nếu có máy kẹt timeout.
- **Cửa sổ lịch nuôi (Schedule Window Invariant):**
  * Khoảng cách giữa 2 phiên liên tiếp trong cùng một ca (06:00 $\rightarrow$ 08:00, 12:00 $\rightarrow$ 14:00, 18:00 $\rightarrow$ 20:00) **chỉ có đúng 120 phút**.
  * Nếu hạ xuống 16 workers: `80 máy / 16 = 5 batches` $\rightarrow$ Thời gian chắc chắn vượt **130 phút**.
  * Hậu quả: Phiên 1 chưa chạy xong thì Phiên 2 đã đè vào, làm sập toàn bộ lịch cron nuôi và watchdog phải dập cưỡng bức.

---

## 3. Quy Tắc Cân Bằng Chuẩn Hóa (Concurrency vs Stagger)

1. **CẤM giảm `MaxWorkers` dưới 25:**
   * `MaxWorkers = 25` là giới hạn cân bằng cứng (Hard Floor/Cap) để đảm bảo toàn bộ 80 máy hoàn thành trong < 90 phút, bảo toàn đệm 30 phút an toàn trước phiên tiếp theo.
2. **Dùng Stagger giãn nhịp thay vì giảm Worker:**
   * Tăng `MachineStartStaggerMs` từ `2000,8000` lên **`3000,10000`** (so le 3s – 10s khi các máy mở TikTok).
   * Vừa triệt tiêu xung đột socket ADB và sụt áp hub tại thời điểm `monkey launch`, vừa giữ nguyên thông lượng 25 worker song song suốt phiên.
3. **Cơ chế Fast Fail-Closed bắt buộc:**
   * Khi phát hiện thiết bị rớt kết nối (`device offline`, `device not found`), worker phải `return` giải phóng slot ngay lập tức trong vài giây, cấm chạy tiếp follow/upload hook để không ngâm threadpool 35 phút.
4. **Kiểm tra Reboot O(1):**
   * Khi nghi ngờ host có vừa reset hay không, dùng `psutil.boot_time()` để đối soát chính xác thời điểm boot, tránh phán đoán cảm tính.
