# Tra cứu nhanh: Dual-Cluster Batch Alert Architecture

Khi xuất hiện thắc mắc hoặc phân tích về việc Batch Alert bắn nhiều thông báo trong 1 phiên:
- Hệ thống chạy đa cụm: Kibe (Local máy 1-80) và Admin (Remote máy 201-280).
- `tiktok_runner.py` chạy tuần tự từng cụm và ghi ra artifact riêng (`runtime/kibe/live` vs `runtime/admin/live`).
- `automation_core.batch_aggregator` được hook gọi độc lập sau mỗi lượt kết thúc cụm.
- Báo cáo cụm Kibe tập trung vào máy local & cảnh báo login/session-lost P0.
- Báo cáo cụm Admin tập trung vào máy remote & đặc thù lỗi ngắt kết nối socket ADB LAN `.119`.
