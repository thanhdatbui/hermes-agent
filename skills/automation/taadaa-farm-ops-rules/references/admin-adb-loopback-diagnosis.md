# Farm Admin — ADB Loopback Binding Chẩn Đoán & Recovery

## Symptom
- `inspect_machine.py MN` (N ≥ 200) timeout: `adb command timed out`
- Batch alert hiện `proxy-vpn:device is offline or ADB/USB disconnected`
- Nhưng `ping 192.168.110.119` thành công (< 5ms)
- `Test-NetConnection -Port 5037` → `TcpTestSucceeded: False`

## Root Cause
ADB server trên Admin PC khởi động bind **127.0.0.1:5037** (loopback-only).  
Xiaowei gọi ADB từ trong cùng máy nên vẫn chạy được (localhost).  
Nhưng kết nối từ Kibe qua `-H 192.168.110.119 -P 5037` bị TCP refused.

**Phân biệt với thiết bị vật lý offline:**  
- ADB loopback: `ssh admin-farm "adb.exe devices"` vẫn thấy **đủ serial**  
- Thiết bị vật lý: serial biến mất khỏi list

## Quy Trình Chẩn Đoán O(1)

```bash
# 1. Ping OK?
ping -n 3 192.168.110.119

# 2. TCP 5037 open?
powershell.exe -Command '$ports = 5037; Test-NetConnection -ComputerName 192.168.110.119 -Port $ports -WarningAction SilentlyContinue'

# 3. SSH kiểm tra binding
ssh admin-farm "netstat -ano | findstr 5037"
# LOOPBACK (lỗi): TCP  127.0.0.1:5037  LISTENING
# OK:             TCP  0.0.0.0:5037    LISTENING

# 4. Kiểm tra ADB local trên Admin còn sống không
ssh admin-farm "\"C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe\" devices"
# Nếu thấy 70-80 serial → ADB OK, chỉ binding lỗi
```

## Recovery

### Option A — Restart ADB bind 0.0.0.0 (nhanh, cần test)
```bash
ssh admin-farm "\"C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe\" kill-server && start /b \"\" \"C:\\Program Files (x86)\\xiaowei\\tools\\adb.exe\" -a nodaemon server start"
```
- Yêu cầu ADB ≥ 1.0.39 (flag `-a`)
- Kill-server làm mất kết nối 78 thiết bị ~5-10s; Xiaowei tự reconnect
- Sau đó verify: `powershell.exe -Command 'Test-NetConnection 192.168.110.119 -Port 5037'` → phải `True`

### Option B — SSH Port Forward (zero-risk, không động Admin)
```bash
# Chạy trên Kibe, giữ terminal mở (hoặc dùng & để background)
ssh -N -L 5037:127.0.0.1:5037 admin-farm &

# Verify tunnel hoạt động
powershell.exe -Command 'Test-NetConnection 127.0.0.1 -Port 5037'
```
Sau đó sửa `ADMIN_IP = "127.0.0.1"` trong `inspect_machine.py` hoặc chạy ADB thẳng trên Admin qua SSH.

### Option C — Chạy inspect trực tiếp trên Admin qua SSH
```bash
ssh admin-farm "python D:/Taadaa/tools/inspect_machine.py 204"
```
Không cần thay đổi binding, hoạt động ngay.

## Context Batch Alert này (Sep 2026)
- Quy mô: 11/80 máy (M204, M208, M212, M214, M215, M223, M225, M264, M265, M276, M278)
- Lỗi: 100% cùng signature loopback ADB timeout
- Phát hiện: xiaowei.exe PID 19912 giữ 70+ kết nối tới adb.exe PID 37648 — tất cả localhost
- Kết luận: không phải thiết bị vật lý die, là hạ tầng ADB binding
