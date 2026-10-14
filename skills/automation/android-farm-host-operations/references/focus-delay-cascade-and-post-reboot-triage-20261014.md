# Focus Delay Cascade & Post-Reboot Triage Protocol (2026-10-14)

## 1. Bản Chất Cụm Lỗi Kép & Quan Hệ Nhân Quả (Dual-Cluster Correlation)
Trong các đợt chạy batch quy mô lớn (ví dụ `tiktok-luot nuoi acc` trên fleet 80-280 máy), hệ thống cảnh báo thường ghi nhận 2 cụm lỗi xuất hiện đồng thời:
1. **Cụm 1 (App Focus):** `focus-device-issue:prepare-tiktok failed to focus TikTok after launch`
2. **Cụm 2 (Transport Offline):** `proxy-vpn:device is offline or ADB/USB disconnected for <serial>: adb.exe: device '<serial>' not found`

### Cơ chế tác động lan truyền:
- **Nguyên nhân gốc (Root Cause):** Tình trạng bão hòa / nghẽn bus EHCI USB phần cứng (đặc thù chipset Intel X99 sau 24h chạy liên tục) làm tê liệt socket transport của 20-30 thiết bị (Cụm 2).
- **Hệ quả lan truyền:** Khi ADB daemon bị nghẽn socket I/O do hàng chục kết nối transport bị rớt đột ngột, các lệnh shell IPC (`monkey launch`, `dumpsys window`, `get_focused_activity`) gửi tới các máy đang online bình thường (Cụm 1) bị chậm trễ nghiêm trọng. Quá trình khởi chạy TikTok vượt quá ngưỡng timeout 15s của `core_prepare_app_for_automation`, dẫn đến báo động giả "failed to focus TikTok after launch".
- **Kết luận:** Lỗi focus ở Cụm 1 không phải lỗi app TikTok hay lỗi UI blocker trên máy, mà là triệu chứng lan truyền từ việc nghẽn ADB transport ở Cụm 2.

---

## 2. Quy Trình Triage & Nghiệm Thu Sau Reboot (Post-Reboot Auto-Resume)

Khi hệ thống vừa trải qua chu kỳ Auto-Reboot (hoặc gateway restart sau reboot):

### Bước 1: Kiểm tra an toàn Device Locks
Xác nhận không còn lock mồ côi nào cản trở lượt chạy mới:
```bash
ls -la ~/.codex/device-locks/
```
- Điều kiện: Không có file `.lock.json` đang hoạt động (`locks == 0`).

### Bước 2: Kiểm tra phục hồi ADB Fleet & Đối soát Uptime O(1)
Khi có nghi vấn "máy không reset mà tự hết", BẮT BUỘC kiểm tra ngay thời điểm boot của host:
```bash
python -c "import psutil, time; print('Uptime:', (time.time() - psutil.boot_time()) // 60, 'phút')"
```
- Nếu thời gian boot sát với thời điểm sau khi kết thúc batch: khẳng định 100% PC đã reboot và System Bus Reset từ BIOS giải phóng thanh ghi EHCI.
Chạy script inspect chuẩn của farm:
```bash
python D:/Taadaa/tools/inspect_machine.py
```
- Đếm tổng số thiết bị `device` online ở cả 2 cụm Kibe Local và Admin Remote.
- System Bus Reset từ BIOS sẽ tự động giải phóng hoàn toàn thanh ghi USB EHCI, kéo hầu hết các máy offline (Cụm 2) trở lại trạng thái `device`.

### Bước 3: Kiểm chứng Canary đại diện trên máy chỉ định
Chạy kiểm tra O(1) trên máy canary (ví dụ M5):
```bash
python D:/Taadaa/tools/inspect_machine.py M5
```
Xác nhận:
- Model, Pin, Build info trả về đầy đủ (không dính `device offline` hay `device not found`).
- Màn hình và trạng thái thiết bị sẵn sàng.

---

## 3. Kiến Trúc Phòng Thủ Fast-Fail & Skip Launcher

Trong repo `tiktok-luot nuoi acc`:
1. **Skip Launcher Popup Dismissal (`device_prepare.py`):**
   - Nếu `_last_focus` là Launcher (`com.sec.android.app.launcher`, `nexuslauncher`, `launcher3`, `systemui`), bỏ qua toàn bộ vòng lặp chụp XML/dismiss popup. Tránh lãng phí thời gian và giảm tải socket ADB khi app chưa lên foreground.
2. **Fast Fail-Closed on Fatal Focus Failure (`multi_machine_feed_session.py`):**
   - Đưa `"failed to focus tiktok after launch"` vào `_FATAL_DEVICE_ERROR_PATTERNS`.
   - Khi gặp lỗi này, worker giải phóng child thread ngay lập tức và nhả slot, không giữ ngâm threadpool 35 phút.
3. **Bộ test kiểm chứng focused:**
   - `python_runner/tests/test_device_prepare.py` (33 tests pass)
   - `python_runner/tests/test_multi_machine_fast_fail.py` (3 tests pass)

---

## 4. Ngăn Ngừa Tái Diễn: Hạ Trần Concurrency & Nới Nhịp Khởi Động
Để ngăn chặn hoàn toàn hiện tượng USB bus saturation tái diễn trong các ca chạy 80 máy:
- **`MaxWorkers` = 16** (hạ từ 25 trong `run-feed-session.ps1`): giảm 36% áp lực I/O đồng thời.
- **`MachineStartStaggerMs` = 3000,10000** (tăng từ 2000,8000): giãn cách 3s–10s giữa các lượt mở app, triệt tiêu cú sốc I/O tức thời.
- Đồng bộ cấu hình tại: `scripts/run-feed-session.ps1`, `scripts/hermes_cron/tiktok_runner.py`, và `run_74machines.bat`.
