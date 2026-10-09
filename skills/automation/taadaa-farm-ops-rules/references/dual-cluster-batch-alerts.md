# Cấu trúc phân tách Cụm Batch Alert (Kibe vs Admin)

## 1. Kiến trúc Runner đa cụm (Multi-Cluster Runner)
Trong `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`, Farm được cấu hình phân tách thành 2 cụm độc lập:
- **Cụm Kibe (Local):** Dải máy `1 – 80`, kết nối trực tiếp qua USB local, artifact lưu tại `D:\Taadaa\runtime\kibe\live\...`.
- **Cụm Admin (Remote):** Dải máy `201 – 280`, kết nối qua remote ADB daemon `192.168.110.119:5037` (sử dụng host config `admin.yaml`), artifact lưu tại `D:\Taadaa\runtime\admin\live\...`.

## 2. Độc lập Batch Aggregator & Cơ chế Alert
Khi chạy nuôi feed (`run-feed-session.ps1`), runner hoàn thành phiên nào sẽ kích hoạt hook `automation_core.batch_aggregator` riêng cho thư mục artifact của cụm đó:
```powershell
& $Python -m automation_core.batch_aggregator "$targetBatchDir" --telegram
```

## 3. Đặc điểm phân biệt trên thông báo Telegram
Khi hệ thống gặp lỗi vượt ngưỡng kép (rate >= 10% & count >= 3) hoặc lỗi P0 Auth/Login:
- **Alert Cụm Kibe:** Danh sách máy là M1..M80. Các lỗi thường gặp: app crash, checkpoint login, mất phiên (session lost).
- **Alert Cụm Admin:** Danh sách máy là M201..M280. Các lỗi đặc trưng: `adb/usb disconnected`, timeout socket kết nối sang máy chủ phụ LAN .119.
- Do chạy trên 2 thư mục artifact độc lập vào 2 thời điểm spawn/kết thúc khác nhau, hệ thống luôn bắn 2 báo cáo `[BATCH ALERT: LỖI HỆ THỐNG]` riêng biệt về topic Farm Alerts.
