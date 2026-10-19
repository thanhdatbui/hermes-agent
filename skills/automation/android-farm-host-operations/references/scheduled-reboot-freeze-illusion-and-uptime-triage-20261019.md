# Chẩn Đoán Cảm Giác "Treo Máy" Lúc Reboot 3 Ca Định Kỳ & Kỹ Thuật Đối Soát Uptime (2026-10-19)

## 1. Hiện Tượng & Câu Hỏi Hiện Trường
- **Tình huống:** Người dùng đang ngồi trước máy tính hoặc remote bỗng thấy màn hình khựng lại, chuột/phím không phản hồi trong vài giây rồi máy tự động chuyển sang màn hình *Restarting* hoặc boot lại vào Windows.
- **Phản ứng tự nhiên:** Người dùng nghi ngờ máy bị lỗi phần cứng, crash màn hình xanh (BSOD) hoặc một tiến trình ngầm nào đó làm "treo máy" (*"? Clmm lí do treo / Nãy máy reboot à"*).

## 2. Bản Chất Kỹ Thuật Của Cảm Giác "Treo Máy" Trước Reboot
1. **Lịch Auto-Reboot 3 Ca Farm:**
   - Hệ thống được cấu hình tự động khởi động lại vào đúng 3 mốc: **05:20**, **11:20**, và **17:20** hàng ngày qua Task Scheduler và script `C:\Taadaa_Service\farm_preflight_daily_reset.py`.
   - Mục đích: Giải phóng thanh ghi phần cứng 2 controller USB 2.0 EHCI, xả socket ADB, dọn RAM và rác tiến trình trước mỗi ca nuôi acc chính (06:00, 12:00, 18:00) với 40 phút vùng đệm an toàn.
2. **Tại sao có cảm giác "treo cứng" vài giây:**
   - Tại mốc `11:20:07`, script kiểm tra an toàn (không có trận TFT in-match, không có Warcraft 3 mở) và phát lệnh `shutdown.exe /r /t 5`.
   - Windows lập tức phát tín hiệu broadcast `WM_QUERYENDSESSION` và `WM_ENDSESSION` tới tất cả các tiến trình và cửa sổ đang mở trên desktop.
   - Do máy host farm thường xuyên có các tiến trình I/O nặng (trình duyệt Chromium GPMLogin, ADB server, Playwright, các tiến trình Python watchdog), các socket TCP và file handle mất 3–5 giây để Windows ép flush hoặc force-kill.
   - Trong khoảng thời gian 3–5 giây này, Windows DWM (Desktop Window Manager) ngưng nhận input chuột/phím, tạo cảm giác máy bị "đơ/treo hoàn toàn" ngay trước khi màn hình xanh xoay vòng *Restarting* hiện lên.

## 3. Quy Trình Đối Soát Hiện Trường O(1) Bằng Bằng Chứng Kỹ Thuật
Khi nhận thắc mắc về việc máy vừa reboot hay nghi ngờ treo máy, Coordinator BẮT BUỘC thực hiện đối soát 3 bước trong < 15 giây:

### Bước 1: Tính Uptime & Giờ Boot Thực Tế
Dùng kernel32 `GetTickCount64()` (hoàn toàn read-only, không lo bị Terminal Guard chặn):
```python
import datetime, ctypes
lib = ctypes.windll.kernel32
t_ms = lib.GetTickCount64()
now = datetime.datetime.now()
boot_time = now - datetime.timedelta(milliseconds=t_ms)
print(f"Uptime: {t_ms / (1000 * 3600):.2f}h | Boot approx: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}")
```
- Nếu `boot_time` nằm sát các mốc `05:21:xx`, `11:21:xx`, hoặc `17:21:xx` $\rightarrow$ Xác nhận ngay là máy vừa trải qua chu kỳ Auto-Reboot định kỳ của farm.

### Bước 2: Truy Vấn Windows System Event Log (Phân biệt Clean Restart vs Crash/BSOD)
Dùng `win32evtlog` đọc ngược các Event gần nhất từ System Log:
- **Event ID 1074 (User32):** Lệnh shutdown sạch sẽ được kích hoạt bởi tiến trình nào. Nếu thấy `shutdown.exe` do `DESKTOP-3PFPGQC\Kibe` với lý do `restart` $\rightarrow$ Đây là lệnh restart chủ động do Task Scheduler phát ra.
- **Event ID 6006 (EventLog):** Dịch vụ EventLog ghi nhận hệ điều hành đang tắt máy bình thường (Clean shutdown).
- **Event ID 6005 (EventLog):** Dịch vụ EventLog khởi động sau khi boot thành công.
- **Event ID 41 (Kernel-Power):** CHỈ xuất hiện khi mất nguồn đột ngột, sụt áp hoặc máy bị reset cứng. Nếu không có Event 41 $\rightarrow$ Khẳng định 100% không phải lỗi phần cứng hay sập nguồn.

### Bước 3: Đọc Nhật Ký `C:\Taadaa_Service\daily_reset.log`
Kiểm tra các dòng log tại thời điểm đó:
```text
[2026-10-19 11:20:01] === BAT DAU KIEM TRA PREFLIGHT DAILY REBOOT (TRUOC MOI CA) ===
[2026-10-19 11:20:03] [PASS] Khong co tran game TFT nao dang dien ra...
[2026-10-19 11:20:04] [ADMIN] Da gui lenh reboot Admin PC thanh cong.
[2026-10-19 11:20:07] [KIBE] Kich hoat reboot Kibe PC sau 5 giay...
[2026-10-19 11:20:07] [SUMMARY] {"admin": "dispatched", "kibe": "dispatched", "outcome": "complete"}
```

## 4. Kỷ Luật Phản Hồi Người Dùng
- **Trả lời dứt khoát, trực diện vào bằng chứng:** Xác nhận ngay mốc reboot 11:20 định kỳ, nêu rõ thời điểm khởi động lại sạch sẽ và giải thích hiện tượng khựng chuột do Windows đóng hàng loạt socket/process của Chromium và ADB.
- **Cung cấp mốc kế tiếp:** Nhắc nhở mốc reboot tiếp theo trong ngày là **17:20 chiều** để người dùng chủ động nếu đang chơi game hoặc có tác vụ cần bỏ qua.
