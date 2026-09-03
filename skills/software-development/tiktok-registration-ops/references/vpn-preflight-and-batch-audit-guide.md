# VPN Preflight & Batch Reg Audit Guide

## Truy vết sự cố chạy Batch Reg & VPN Check trên Farm

Khi user kiểm tra hiện trường hoặc chất vấn về việc script nào chạy / tại sao máy lại vượt qua bước kiểm tra VPN để reg:

### 1. Nguồn gốc Script & Log thực thi
- **Repo:** `D:\Taadaa\Tiktok_Reg`
- **File chạy chính:** `social_reg_v1.py` hoặc runner qua `_run_all_targets.py`
- **Log tổng:** `D:\Taadaa\Tiktok_Reg\social_reg_log.txt`
- **Artifacts theo mốc thời gian:** `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<timestamp>\`
  - `all_results.json`: Bảng tổng kết status toàn bộ máy trong đợt chạy.
  - `batch_1\machine_launch.json`: Thứ tự và độ trễ khởi chạy giữa các máy.
  - `batch_1\stt_<STT>\stdout.log` & `stderr.log`: Chi tiết từng bước kiểm tra gate và UI flow của từng máy.

### 2. Logic kiểm tra VPN Preflight (`require_android_vpn`)
- **Nguyên tắc fail-closed:** Máy có gán proxy trong `PROXYgandienthoai.xlsx` bắt buộc phải có VPN `tun0` active VÀ ViChanger broadcast `GET_IP` thành công trả về IP hợp lệ.
- **Trường hợp máy từng bị block rồi lại chạy được:**
  - Nếu ở tick trước (ví dụ lúc proxy bị ngắt), script sẽ báo `VPN_PREFLIGHT_BLOCKED(ViChanger GET_IP failed after 3 retries: proxy dead/unreachable)` và dừng ngay.
  - Sau đó, nếu daemon proxy nền (`gan_proxy_fleet.py`) reconnect thành công hoặc proxy sống lại, ở lần batch chạy kế tiếp ViChanger `GET_IP` sẽ thành công (`vpn preflight: CONNECTED`), do đó script pass gate và tiến hành đăng nhập / đăng ký.
- **Quy tắc giải trình:** Luôn trích dẫn log thực tế (mốc thời gian, trạng thái `VPN_PREFLIGHT_BLOCKED` vs `CONNECTED`, mã lỗi chi tiết) thay vì phỏng đoán.
