# Stale Upload Watchdog: Cluster Separation, Slot-Level Independence, and USB Triage

## 1. Bối Cảnh & Hiện Tượng Gây Hiểu Nhầm (Watchdog Misinterpretation)
Khi cronjob `daily-stale-upload-accounts-watchdog` phát báo cáo:
```text
🚨 [TOP NICK BỊ ĐÓNG BĂNG LÂU NHẤT (> 14 NGÀY)] (108 nick):
  • M10  T1 (kibe): @anhtruong840 (kẹt 26d từ 2026-09-17, dừng ở 24 clip)
  • M30  T1 (kibe): @ninhvan04061999 (kẹt 26d từ 2026-09-17, dừng ở 14 clip)
  • M74  T1 (kibe): @muyduyen4589 (kẹt 26d từ 2026-09-17, dừng ở 9 clip)
  • M69  T2 (kibe): @tranthibich3499 (kẹt 26d từ 2026-09-17, dừng ở 1 clip)
  • M13  T1 (kibe): @m.my7409 (kẹt 26d từ 2026-09-17, dừng ở 9 clip)
  • M209 T7 (admin): @ngochuyen5327 (kẹt 23d từ 2026-09-20, dừng ở 1 clip)...
```
Người vận hành dễ hiểu nhầm rằng: *"Cả đống máy bên Kibe bị kẹt không đăng clip"* hoặc hệ thống upload tê liệt.

Thực tế kiểm tra hiện trường:
- **Ngay trong ca sáng:** 50/80 máy Kibe vừa đăng clip thành công rực rỡ (tăng 250 clip/ngày toàn hệ thống).
- Danh sách 108 nick "kẹt" phân bổ theo 3 tầng hoàn toàn khác nhau.

---

## 2. Quy Tắc Bóc Tách 3 Tầng Nguyên Nhân (3-Tier Root Cause Triage)

### Tầng 1: Tách Biệt Cụm Farm (Cluster Separation: Admin vs Kibe)
- **Tỷ lệ áp đảo:** Thường 80–85% nick kẹt >14 ngày (ví dụ 89/108 nick) thuộc cụm **Admin PC (M201–M280)**.
- **Nguyên nhân nghiệp vụ:**
  - Admin là cụm máy mới, chỉ đăng thử nghiệm 1–2 clip vào cuối tháng 9 rồi tạm dừng.
  - Quy tắc bất di bất dịch: **Media Kibe và Admin độc lập tuyệt đối, cấm copy chéo**. Cụm Admin chỉ được upload khi đã download & render xong nguồn video riêng (`D:\video goc may 2`).
  - Khi kho video Admin chưa render đủ 45 clip (mới đạt ~30% folder, Tik6–8 đạt 0%), các nick Admin bắt buộc phải "ngâm dưỡng" chờ video. Đây là **kế hoạch chủ động**, không phải lỗi.
- **Kỷ luật điều phối:** Báo cáo watchdog bắt buộc phân tách rành mạch: `Số nick kẹt Kibe` vs `Số nick kẹt Admin (chờ render)`, cấm gộp chung làm biến dạng bức tranh vận hành.

### Tầng 1.5: Phân Loại & Truy Vết Các Acc Lẻ Tẻ (Isolated Stale Accounts Triage)
Khi bóc tách các nick kẹt còn lại trên cụm Kibe, tuyệt đối không kết luận vội vã là "lỗi hệ thống", mà truy vết 3 nhóm nguyên nhân kỹ thuật:
1. **Nhóm Slot 7 & Slot 8 (Chiếm đa số, ~60% acc lẻ):**
   - Phân bổ theo chu kỳ 4 ngày (96h): Day 0 (Row 1,3,5), Day 1 (Row 2,4,6), Day 2 (Row 7,8), Day 3 (Dưỡng sinh xả tải).
   - Nếu ngày hiện tại là Day 0 hoặc Day 1, các nick Slot 7 & 8 hiển nhiên chưa đến lượt chạy. Kiểm tra kho media `D:\TIKTOK-videonuoinick\<folder>` thấy đủ 45-65 clip `.mp4` thì khẳng định đây là tiến độ bình thường theo nhịp chu kỳ.
2. **Nhóm trượt nhịp tại các Chốt An Toàn (Fail-Closed Safety Gates):**
   - `[POST_SUBMISSION_UNKNOWN]`: TikTok không trả về popup xác nhận bài đăng thành công kịp trong deadline $\rightarrow$ runner fail-closed, không tự ý ghi tăng video vào workbook/tracker.
   - `Editor Next tapped but caption composer did not open`: TikTok bị lag ở editor khi bấm "Tiếp", không mở được màn hình viết caption $\rightarrow$ thử 3 lần rồi dừng ở `MANUAL_REVIEW`.
   - `prepare-tiktok failed to focus TikTok`: App TikTok bị crash/rớt focus về Launcher (`com.sec.android.app.launcher`) lúc khởi động $\rightarrow$ dừng phiên an toàn trước hook upload.
3. **Quy trình truy vết O(1) nguyên nhân trượt ca:**
   - Tra cứu `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`: xem `status` ca gần nhất (`success` vs `launched` vs `failed`).
   - Đọc trực tiếp `upload_result.json` và `report.json` tại `D:\Taadaa\runtime\kibe\live\<date>\<session>\machine_<N>\<run_id>\`: lấy chuỗi `reason` và `stdout_tail` cụ thể.
   - Với máy bị treo lệnh `inspect_machine.py` do socket transport hang (như case M74): Gửi lệnh `host-serial:<serial>:reconnect` qua socket ADB port 5037 để gỡ kẹt tức thì thay vì phán rút cáp.

### Tầng 2: Độc Lập Giữa Các Slot (Per-Machine Multi-Slot Independence)
- Mỗi máy vật lý quản lý **8 slot tài khoản** (Tik 1 đến Tik 8).
- **Hiện tượng đánh lừa:** Máy 13 vừa đăng thành công Tik 7 (@ngohuong3008) sáng nay lúc 06:11, nhưng Tik 1 (@m.my7409) lại dừng ở 9 clip từ 17/09. Máy 19 vừa đăng Tik 7 (@makkocuo162) lúc 06:23, nhưng Tik 1 (@hoanghan27093) dừng ở 27 clip từ 23/09.
- **Cơ chế chu kỳ 96h (4 ngày):**
  - Day 0: Row 1, 3, 5
  - Day 1: Row 2, 4, 6
  - Day 2: Row 7, 8
  - Day 3: Dưỡng sinh xả tải
  - Mỗi slot chỉ chạy **1 lần duy nhất sau mỗi 96 giờ (4 ngày)**.
- **Bẫy logic cũ (Đã loại bỏ ngày 11/10/2026):**
  - Hàm `_is_account_organic_rest_day` trước đây có logic bốc ngẫu nhiên 1/3 số nick để "nghỉ dưỡng sinh không upload" (`int(h[:8], 16) % 3 == 0`).
  - Nếu một nick Tik 1 vô tình rơi vào 1/3 ngẫu nhiên này, hoặc bị rớt mạng đúng ca chạy, nick đó bị hoãn thêm 4 ngày (96h) tiếp theo. Lặp lại 2-3 chu kỳ khiến số ngày stale vọt lên 16-24 ngày dù máy vẫn online.
  - **Khắc phục:** Logic random 1/3 đã bị khai tử (commit `08cc160`). Các nick Tik 1, Tik 2 đến lượt ca sẽ được tự động đăng bù đầy đủ.

### Tầng 3: Rớt ADB Phần Cứng Do Nghẽn Bus USB 2.0 (X99 EHCI)
- **Hiện tượng:** Kiểm tra `adb devices` thấy 30–37 máy rớt kết nối (`device not found` hoặc `offline`).
- **Nguyên nhân:** Bo mạch chủ X99 chạy 80 máy dồn vào 2 controller USB 2.0 EHCI. Sau >24h chạy liên tục, các micro-spike I/O làm nghẽn buffer và kẹt socket uevent ở kernel điện thoại (đường VBUS 5V vẫn giữ nên máy không restart adbd).
- **Xử lý:**
  - **Không hoảng loạn sửa code hay can thiệp ADB:** Đây là đặc tính phần cứng đã có quy hoạch.
  - **Task `Taadaa_Farm_Daily_Reboot_1135` lúc 11:35:** Tự động kích hoạt reboot host hàng ngày trước Ca 2 (12:00). Xung System Bus Reset từ BIOS giải phóng 100% thanh ghi và kéo toàn bộ dàn máy online xanh trở lại.

---

## 3. Checklist Điều Phối Khi Nhận Phàn Nàn "Máy Kẹt Không Đăng Clip"
1. **Kiểm tra nhật ký ca mới nhất O(1):**
   - Đọc `summary.txt` và `upload_result.json` tại `D:\Taadaa\runtime\kibe\live\<today>\<row-time>\`.
   - Xác định ngay số máy upload `success` trong ngày hôm nay để khẳng định hệ thống đang sống.
2. **Đối soát DB Tracker vs Thực tế:**
   - Đếm số nick tăng clip trong 24h: `SELECT COUNT(*) FROM snapshots s2 JOIN snapshots s1 ... WHERE (s2.video - s1.video) > 0`.
3. **Phân loại danh sách Stale:**
   - Lọc bỏ ngay các nick Admin (M201–M280) sang mục "Chờ nguồn video".
   - Với các máy Kibe: Liệt kê rõ slot nào đang kẹt (ví dụ: chỉ kẹt Tik 1, còn Tik 7 vừa đăng sáng nay).
4. **Kiểm tra trạng thái USB & Thời gian tới cữ Reboot 11:35:**
   - Nếu gần mốc 11:35: Thông báo tiến trình reboot tự động làm sạch.
   - Nếu cần gấp trước giờ ca: Khởi động lại Windows 1 lần (PC có `AutoAdminLogon = 1` tự nạp sau 60s).
