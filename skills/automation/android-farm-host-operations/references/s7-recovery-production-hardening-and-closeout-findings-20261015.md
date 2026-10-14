# S7 Recovery Production Hardening & Closeout Review Findings (15/10/2026)

## 1. Bối Cảnh & Vấn Đề
Khi vận hành Farm 80–160 máy Samsung S7 (Android 8) trên mainboard Huananzhi X99 Dual Xeon qua 2 chip điều khiển USB 2.0 EHCI (`8D26`, `8D2D`), câu hỏi thường gặp của người vận hành:
- *"Có nên thêm bước reboot S7 trước ca nuôi để giảm lag truyền dữ liệu không?"*
- *"Khi S7 bị kẹt lệnh shell thì có reboot S7 từ PC được nữa không?"*

## 2. Bản Chất Kỹ Thuật (S7 Reboot Anti-Pattern)
- **Nút thắt cổ chai không nằm ở S7:** Băng thông USB 2.0 trần chỉ 35–40 MB/s. Khi chạy dồn dập, buffer và thanh ghi phần cứng của 2 chip EHCI trên bo mạch chủ PC bị kẹt (lỗi `HRESULT 0x8004100c`), Windows không thể reset mềm bằng lệnh mà bắt buộc phải Reboot Host PC để kích hoạt System Bus Reset từ BIOS/UEFI. Điện thoại S7 không bị tích tụ rác trên đường truyền USB.
- **Tác hại của việc reboot đồng loạt 80 máy S7:**
  1. *USB Enumeration Storm:* 80 máy đồng loạt boot và bắt tay ADB làm sập cụm Hub (Box 3, Box 4 rụng 8–16 máy).
  2. *Flapping cáp Micro-USB:* Cáp dão chân data D+/D- bị rớt kết nối (socket 10061, `unauthorized`).
  3. *Thermal Throttling:* 5–10 phút đầu sau boot, Android 8 chạy MediaScanner, Knox, dexopt background đẩy CPU lên 100%, làm máy nóng ran và lag hơn bình thường.
  4. *Bão DHCP Wi-Fi & Giết Daemon:* 80 máy cùng kết nối lại Wi-Fi gây nghẽn MikroTik/Aruba, đồng thời kill toàn bộ tiến trình nền (`atx-agent` port 7912, minicap).
- **Phân biệt Kẹt Shell vs Kẹt Transport:**
  * Lệnh `adb reboot` là service `reboot:` độc lập trong daemon `adbd`, **KHÔNG** đi qua `/system/bin/sh`. Do đó, khi S7 bị deadlock ứng dụng/dumpsys treo, `adb -s <serial> reboot` vẫn khởi động lại máy bình thường từ PC.
  * Chỉ khi cáp USB đứt, cổng USB treo hoặc pipe `/dev/android_adb` trên nhân Linux của S7 bị đứt (transport dead), mọi lệnh ADB mới tê liệt hoàn toàn.

## 3. Kiến Trúc Cứu Hộ Phân Tầng O(1) (`recover_stuck_s7.py`)
Module `recover_stuck_s7.py` được thiết kế 3 cấp độ cứu hộ tăng dần:
1. **Pre-flight Check:** Kiểm tra `adb -s <serial> get-state`. Nếu khác `device` (như `offline`, `unauthorized`), nhảy thẳng xuống Level 3 Reconnect/Transport, tuyệt đối không reboot mù.
2. **Level 1 — Soft Recovery (Timeout 3.0s):**
   - Gọi `am force-stop com.ss.android.ugc.trill`.
   - Gửi `input keyevent 223` (KEYCODE_SLEEP - lệnh idempotent tắt màn hình chống nóng).
   - *Post-condition verify:* Ping nhẹ `shell echo 1` (timeout 2.0s). Phải trả về exit code 0 và output `"1"` mới chứng nhận `recovered_soft`.
3. **Level 2 — Bypass Shell Direct Reboot (Timeout 5.0s):**
   - *Anti-Reboot Loop Cooldown:* Kiểm tra file lock `~/.codex/device-locks/reboot_cooldown_<serial>.json`. Nếu máy vừa reboot trong vòng 5 phút (300s), huỷ lệnh và trả về `aborted_cooldown` để ngăn vòng lặp khởi động lại liên tục.
   - Bắn trực tiếp packet daemon: `adb -s <serial> reboot`.
   - Chờ `adb wait-for-device` và kiểm tra `get-state == 'device'` tối đa 60s.
4. **Level 3 — Transport / Reconnect Triage:**
   - **Tử huyệt cú pháp ADB Reconnect:** Cú pháp chuẩn của ADB là `adb [-H ...] -s <serial> reconnect` (hoặc `adb reconnect offline`), **CẤM TUYỆT ĐỐI** dựng sai cú pháp `adb reconnect <serial>`.
   - Nếu `reconnect` thất bại -> ghi nhận `failed_transport`, nhả tiến trình ngay để cô lập lỗi phần cứng.

## 4. Kiến Trúc Rolling Healer Toàn Farm (`batch_recover_s7.py`)
Khi cần quét và dọn dẹp hàng loạt cho toàn Farm (80–160 máy):
- **Khống chế I/O đồng thời:** `ThreadPoolExecutor(max_workers=8)` tương thích với Heavy-IO Semaphore của Farm, tránh spike bus USB 2.0.
- **Khóa chống bão Reboot:** `reboot_sem = threading.Semaphore(max_reboots=2)`. Bắt buộc chỉ tối đa **2 máy** được reboot đồng thời trên toàn Farm. Máy thứ 3 phải xếp hàng chờ máy trước boot xong mới được cấp vé reboot.
- **Lọc slot trống tự động:** Bỏ qua slot trống vật lý đã biết (Máy 255 trên Admin Farm).
- **Chống cướp focus:** Mọi lệnh subprocess trên Windows bắt buộc dùng cờ `creationflags=subprocess.CREATE_NO_WINDOW`.

## 5. Kết Quả Kiểm Chứng Thực Tế Trên Toàn Farm (15/10/2026)
Đã chạy live 100% trên 159 máy vật lý:
- **Cụm Admin Remote (M201–280):** 79 máy hoàn tất trong **17.1 giây**.
  * 78/79 máy soft recovered thành công ở Cấp 1 (1.5s/máy, không cần reboot).
  * 1 máy (M228) phát hiện đứt chân data cáp USB vật lý, cô lập ở Cấp 3.
- **Cụm Kibe Local (M1–80):** 80 máy hoàn tất trong **15.2 giây**.
  * 77/80 máy soft recovered thành công ở Cấp 1.
  * 3 máy (M1, M10, M30) nhận diện lỗi transport. M1 sau đó hồi phục online bình thường; M10 và M30 khu trú chân cáp Micro-USB bị dão chấu data D+/D-.
