# Kibe-Admin Parity & Cross-Machine Reg TikTok Rules

## 1. Parity 100% Giữa Kibe và Admin (Cái gì Kibe có, Admin phải có)
- Dàn máy Kibe (1–80) và Admin (201–280) có quyền hạn và cơ chế tự động ngang nhau.
- **CẤM** Coordinator tự bịa lý do an toàn để né chạy tự động hoặc hủy tính năng của cụm Admin.
- Tự động reg bù khi thiếu tài khoản (`_preflight_ensure_accounts`) phải chạy cho cả Kibe và Admin.

## 2. Kỹ Thuật Reg Cho Dàn Admin Từ Máy Kibe
- Khi chạy script reg cho Admin từ máy Kibe:
  - Bắt buộc set `TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml"`.
  - Bắt buộc set `ADB_SERVER_SOCKET="tcp:192.168.110.119:5037"` để điều khiển thiết bị qua PortProxy.
  - Marker file preflight phải kèm tên cluster (`.preflight_admin_<window_key>`) để không xung đột với Kibe.
