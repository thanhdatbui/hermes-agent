# Dual-Cluster Canary Alignment & Exact Slot Row Target

## 1. Bẫy Canary Sai Slot Tài Khoản (False-Green Illusion)
- **Hiện tượng**: Khi nhận alert lỗi thiếu nick ở một slot cụ thể (ví dụ Row 2 - `thuthanh2911` trên M261), Coordinator chạy canary với `--row 1`.
- **Hậu quả**: Slot 1 của máy là nick `lamhongloan1907` đã được đăng nhập sẵn từ trước. Bước `profile_preflight` kiểm tra thấy nick khớp ngay (`already matched`), script tiếp tục lướt feed và báo `CANARY_VERDICT: PASSED`.
- **Bẫy**: Đây là **bằng chứng ảo (False Green)**, hoàn toàn không chạm vào nhánh code cần kiểm chứng (nhánh phát hiện thiếu nick -> kích hoạt auto-login recovery). User quở trách gay gắt: *"Chứ mày canary kiểu lồn gì mà đéo làm đúng cái lỗi đi thử vs acc khác. Bị ngu k"*.
- **Quy tắc bất biến**: Khi chạy Canary tái hiện hoặc nghiệm thu bản vá, BẮT BUỘC phải chỉ định chính xác `--row <N>` của tài khoản bị lỗi trong alert. Đối chiếu:
  ```python
  import openpyxl
  wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\<cluster>\taikhoan_run_safe.xlsx", data_only=True)
  # Tra cứu đúng số thứ tự row của nick bị lỗi
  ```

## 2. Chuẩn Hóa Dual-Cluster Trong `canary_runner.py`
Khi chạy Canary cho cụm Admin (máy $\ge 200$), `canary_runner.py` bắt buộc phải tự động inject môi trường:
```python
if "Admin" in cluster or m >= 200:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
    env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
else:
    env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\kibe.yaml"
    env.pop("ADB_SERVER_SOCKET", None)
```
Nếu thiếu biến môi trường này, script runner sẽ bị `HostConfigError: MACHINE_OUT_OF_RANGE` do rơi về mặc định Kibe (1-80).

## 3. Ngưỡng Timeout Thích Hợp Cho Canary Đơn Máy Kèm Login Bù
- Lệnh nuôi feed thông thường: timeout $\le 300\text{s}$.
- Lệnh nuôi feed CÓ KÍCH HOẠT `auto_login_recovery` qua mạng liên cụm (Kibe -> Admin): Timeout tối thiểu bắt buộc là **$720\text{s}$** (chu trình kiểm tra Switcher + Fast Login + Graph API OTP + Reconcile + Lướt feed mất từ 350s - 500s). Đặt 300s sẽ bị kill timeout trước khi kịp hoàn tất.
