# Dual-Cluster Wi-Fi Preflight Fallback & adbjoinwifi Triage

## 1. Dual-Cluster Mapping Lookup Trap in `vpn_preflight.py`
Khi một host (ví dụ Kibe) chạy quy trình kiểm tra preflight hoặc cứu hộ Wi-Fi cho serial thuộc host đối ứng (Admin):
- `get_default_proxy_mapping()` chỉ trỏ về mapping của host hiện tại (`D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`), chỉ chứa các máy 1–80.
- Hàm `get_wifi_credentials_for_serial(serial)` không tìm thấy serial của máy Admin (201–280), dẫn đến trả về `None`.
- Stage 2 Recovery (`adbjoinwifi`) bị bỏ qua hoàn toàn vì `if wifi_creds:` đánh giá là False.

## 2. Chuẩn Hóa Fallback Hai Chiều (Dual-Cluster Aware)
- Khi `machine is None` trong bảng mapping chính, bắt buộc fallback đọc mapping của cluster đối ứng:
  - Nếu mapping chính ở thư mục `kibe`, tìm tiếp ở `admin/PROXYgandienthoai.xlsx`.
  - Nếu mapping chính ở thư mục `admin`, tìm tiếp ở `kibe/PROXYgandienthoai.xlsx`.
- Chỉ khi cả hai bảng mapping đều không có serial mới kết luận không rõ profile máy.
- Điều này đảm bảo `adbjoinwifi` luôn nhận đúng SSID (`admin 1` / `admin 2` hoặc `kibe 1` / `kibe 2`) và mật khẩu chuẩn (`19051995` hoặc `23102025`).
