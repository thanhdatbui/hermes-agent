# Dual-Cluster Batch Alert Triage Fastpath

## Bối Cảnh
Khi một ca chạy feed / reg / upload kết thúc và watchdog báo cáo danh sách máy fail (ví dụ 8 máy Kibe, 12 máy Admin), việc gọi `inspect_machine.py <N>` tuần tự từng máy có thể gặp vấn đề:
- Nếu thiết bị bị treo kernel/USB, ADB daemon trên máy đích có thể hang các lệnh `shell dumpsys` (mỗi lệnh timeout 10s, 6 lệnh = 60s/máy).
- Đặc biệt với cụm Admin Remote (`192.168.110.119:5037`), độ trễ mạng cộng dồn làm tăng nguy cơ timeout lệnh terminal.

## Fastpath Triage 2 Bước (O(1) Siêu Tốc)

### Bước 1: Quét Snapshot Toàn Dàn (Attached List Dump)
Chạy:
```bash
python D:/Taadaa/tools/inspect_machine.py
```
Lệnh này chỉ gọi `adb devices` trên cả Kibe Local và Admin Remote (<2 giây), trả về toàn bộ thiết bị đang gắn.

### Bước 2: Phân Loại Dựa Trên Trạng Thái ADB
Đối soát Serial của máy lỗi (tra từ `PROXYgandienthoai.xlsx` của cụm tương ứng):
1. **Thiết bị không có trong danh sách attached:**
   - Kết luận ngay: **Mất kết nối ADB/USB (Cáp lỏng, cổng USB hub rớt hoặc máy mất nguồn)**.
   - Không cần gọi `inspect_machine.py <N>` để tránh chờ timeout.
2. **Thiết bị báo `offline`:**
   - Kết luận ngay: **ADB daemon bị kẹt / Transport offline**.
   - Cần restart adbd trên thiết bị hoặc cắm lại cáp.
3. **Thiết bị báo `device` (Online bình thường):**
   - Chỉ lúc này mới chạy `inspect_machine.py <N>` để kiểm tra chi tiết Pin, Wi-Fi IP, Proxy và `mCurrentFocus`.
   - Nếu máy đã ở `LauncherActivity` (Home) hoặc Sleep an toàn và không giữ lock: Không cần can thiệp tap tay thô, để máy tự động vào ca tiếp theo.
