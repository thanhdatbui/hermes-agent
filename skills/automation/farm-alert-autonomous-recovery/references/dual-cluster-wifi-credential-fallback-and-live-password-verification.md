# Dual-Cluster Wi-Fi Credential Fallback & Live Password Verification SOP

## 1. Bẫy Tra Cứu Wi-Fi Đơn Cụm Khi Chạy Batch (Dual-Cluster Wi-Fi Lookup Trap)
### Hiện tượng (Sự cố 2026-10-28):
Trong đợt chạy Nuôi Acc / Lướt Feed trên cụm Admin (M201-280), 5 máy (M216, M229, M266, M268, M277) bị rớt mạng hoặc mất kết nối Wi-Fi. Mặc dù hệ thống có cơ chế tự động kết nối lại (Stage 2 Recovery qua `adbjoinwifi`), toàn bộ 5 máy đều bị văng lỗi fail-closed ngay lập tức mà không hề kích hoạt `adbjoinwifi`.

### Nguyên nhân gốc (Root Cause):
1. Trong script preflight của flow nuôi nick (`D:/Taadaa/tiktok-luot nuoi acc/python_runner/core/vpn_preflight.py`), hàm `get_wifi_credentials_for_serial(serial)` dùng `get_default_proxy_mapping()` để đọc file mapping `PROXYgandienthoai.xlsx`.
2. Khi ca chạy khởi tạo trên máy chủ Kibe (Controller), file mapping mặc định trỏ về `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (chỉ chứa danh sách máy M1–M80).
3. Khi tra cứu các serial của cụm Admin (M201–M280), hàm không tìm thấy trong file Kibe nên trả về `machine = None` $\rightarrow$ `wifi_creds = None`.
4. Vì `wifi_creds is None`, script **bỏ qua hoàn toàn khối lệnh `adbjoinwifi`** và dừng máy.

### Giải pháp kỹ thuật chuẩn hóa (Dual-Cluster Fallback):
Hàm `get_wifi_credentials_for_serial` bắt buộc phải có cơ chế fallback đa cụm (Dual-Cluster Fallback):
- Khi tra cứu trong mapping hiện tại không thấy serial, tự động kiểm tra sang thư mục đối ứng (`kibe` <-> `admin`).
- Nếu file đối ứng tồn tại, đọc bảng mapping và lấy đúng số máy để cấp đúng SSID và mật khẩu (`admin 1` / `admin 2` với pass `19051995`).

---

## 2. Kiểm Chứng Mật Khẩu TikTok Thật Thay Vì Tin Mù Vào Dữ Liệu Backup Cũ
### Hiện tượng:
Tài khoản `thuthanh2911` (M261) trong file `taikhoan_dat_v2_updated .xlsx` có cột `PASS = None`. Khi tra ngược lại các file backup lịch sử (`taikhoan_dat_v2_updated .bak_final.xlsx`), tìm thấy mật khẩu `A6SpYQZm#W` và nạp lại vào bảng.

### Thực tế hiện trường khi chạy Live (2026-10-28 08:16:54 AM):
TikTok mở màn hình đăng nhập, điền pass `A6SpYQZm#W`, nhưng server TikTok trả về dòng chữ đỏ:
```text
['Nhập mật khẩu', '••••••••••', 'Mật khẩu sai', 'Bạn cần trợ giúp đăng nhập?']
```

### Bài học & Quy tắc bất biến:
1. Cột `PASS` bị để trống (`None`) trong database chính thức thường là kết quả của việc tài khoản đã bị đổi mật khẩu hoặc chưa hoàn tất đặt pass trong quá trình reg/sync trước đó.
2. Tuyệt đối không được khẳng định 100% mật khẩu từ file backup là đúng khi chưa qua kiểm chứng live trên thiết bị.
3. Khi TikTok báo `Mật khẩu sai`: Script bắt buộc phải tự động fail-fast từ `fast_login` sang luồng cứu hộ chuyên sâu `reconcile_tiktok_accounts.py` để xử lý cấp lại mã hoặc khôi phục qua token/mail, cấm lặp lại việc thử pass sai làm khóa tài khoản.
