# Inspect Machine O(1), Terminal Guard & Socket Hang Triage

> Ref: Hướng dẫn trích xuất hiện trường máy O(1), tuân thủ rào chắn Terminal Guard của Coordinator và xử lý thiết bị treo socket ADB.

---

## 1. Rào Chắn Terminal Guard Đối Với Coordinator

Trong môi trường điều phối Taadaa Phone Farm, Coordinator hoạt động dưới cơ chế kiểm soát nghiêm ngặt của hook bảo vệ (`guard_terminal_allowlist.py` / `guard_timeout.py`):
1. **`GUARD_FOREGROUND_TIMEOUT_MISSING`:**
   - Mọi lệnh `terminal` foreground bắt buộc phải khai báo tham số `timeout` rõ ràng (tối đa 60s cho foreground). Nếu thiếu `timeout`, lệnh bị từ chối ngay lập tức:
     `[GUARD_FOREGROUND_TIMEOUT_MISSING] Lệnh terminal foreground thiếu timeout! Bắt buộc timeout <= 60s hoặc chạy background=True.`
2. **`COORDINATOR TERMINAL BLOCKED (DEFAULT-DENY)` & `GUARD SELF-PROTECTION`:**
   - Lệnh `powershell.exe` bị chặn hoàn toàn bởi allowlist default-deny (không dùng PowerShell để check Get-PnpDevice từ Coordinator).
   - Lệnh ADB raw chứa `screencap` hoặc shell tùy ý bị chặn bởi guard tự vệ (`GUARD SELF-PROTECTION / GUARD SOURCE BLACKLISTED`).
   - **Công cụ chuẩn tắc duy nhất:** BẮT BUỘC gọi `python D:/Taadaa/tools/inspect_machine.py <N>` (đã nằm trong allowlist).
   - **Chẩn đoán Mass USB Disconnect O(1):** Chạy `python D:/Taadaa/tools/inspect_machine.py` (không tham số) để đếm số máy online trên từng cluster (Kibe vs Admin). Nếu Kibe tụt từ 80 xuống 45 máy và máy lẻ trả về `device '<serial>' not found`, kết luận ngay lỗi sụt nguồn Hub USB/cáp uplink vật lý, cấm cố sửa code.

---

## 2. Đặc Tả Vận Hành `inspect_machine.py`

- **Định tuyến cụm tự động theo Machine ID ($N$):**
  - $N < 200$: Cụm Kibe Local (`D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`).
  - $N \ge 200$: Cụm Admin Remote qua host `192.168.110.119:5037` (`D:/OneDrive/TaadaaData/admin/PROXYgandienthoai.xlsx`).
- **Liệt kê toàn bộ thiết bị (Fleet Overview):**
  - Chạy không tham số: `python D:/Taadaa/tools/inspect_machine.py` (khai báo `timeout=15` đến `30`).
  - Xuất danh sách serial và trạng thái kết nối (`device` vs `offline`) cho cả 2 cụm Kibe và Admin.
- **Trích xuất hiện trường máy $N$:**
  - `python D:/Taadaa/tools/inspect_machine.py <N>` (khai báo `timeout=30`).
  - Trả về 6 chỉ số: Model, % Pin & trạng thái sạc, Màn hình (ON / OFF / Sleep), Wi-Fi IP, Cổng Proxy gán, và `mCurrentFocus` (App đang chiếm foreground).

---

## 3. Cạm Bẫy Socket ADB Treo (Timeout Pitfall) & Cách Xử Lý

- **Cơ chế nội bộ:** `inspect_machine.py` thực hiện tuần tự 4-5 lệnh `adb shell` (`getprop ro.product.model`, `dumpsys battery`, `dumpsys power`, `dumpsys window`). Mỗi lệnh có internal timeout 10 giây.
- **Hiện tượng treo:** Khi một thiết bị bị đơ ADB transport (ví dụ M74):
  - Lệnh có thể kéo dài vượt quá timeout 30s của terminal (`Exit 124: the command hit its timeout`).
- **Quy trình xử lý chuẩn khi `inspect_machine.py <N>` bị timeout:**
  1. Kiểm tra nhanh serial máy từ Excel mà không chạm ADB:
     ```bash
     python -c "from inspect_machine import get_serial_for_machine; print(get_serial_for_machine(<N>))"
     ```
  2. Đối chiếu serial đó với danh sách thiết bị tổng từ `python D:/Taadaa/tools/inspect_machine.py` để xác định:
     - Thiết bị đang `offline` (mất kết nối USB daemon).
     - Hay thiết bị vẫn báo `device` nhưng treo socket command.
  3. Không spam lặp lại lệnh vào thiết bị đang nghẽn socket; ghi nhận lỗi phần cứng / cáp để watchdog tự heal hoặc xử lý vật lý.

---

## 4. Kỷ Luật Xử Lý Báo Cáo Batch Watchdog Trong Telegram DM

1. **Cấm tự ý xóa/pause cron:** Khi nhận báo cáo cron (như `tiktok-feed-session-watchdog`), tuyệt đối không được xóa hay tạm dừng job nếu không có lệnh dứt khoát từ người dùng.
2. **Đối soát Ngân sách Lỗi (Fleet Error Budget):**
   - Tỷ lệ cùng 1 mã lỗi $< 10-15\%$ HOẶC số máy dính $< 3$ máy $\rightarrow$ Coi là hao hụt tự nhiên (Silent Skip), không kích hoạt Farm Alert và không sửa code.
   - P0 Mất phiên / Checkpoint: Ngưỡng 0 tolerance (phát hiện $\ge 1$ máy văng login $\rightarrow$ cảnh báo P0 ngay).
3. **Báo cáo súc tích:** Tóm tắt KPI, đối soát các máy ngoại lệ qua `inspect_machine.py`, xác nhận các máy lỗi đã teardown an toàn về Home launcher và tắt màn hình.
