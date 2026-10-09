# Multi-Cluster Farm Runner & Host Guard Pitfalls

## 1. Kiến trúc Single Master (Kibe) & Thin-Worker (Admin)
Master Kibe (PC này) điều phối cả 2 cụm:
- Cụm Local: Máy 1-80 (host: `kibe`, range: 1-80)
- Cụm Remote LAN (.119): Máy 201-280 (host: `admin`, range: 200-999)

## 2. Host Guard per Cluster (`TAADAA_HOST_CONFIG`)
Hệ thống sử dụng `taadaa_host.py` để bảo vệ an toàn fail-closed, chống chạy nhầm máy giữa các farm:
- Cấu hình Kibe: `D:\Taadaa\machine-config\kibe.yaml` (`host_id: kibe`, `machine_range: [1, 80]`)
- Cấu hình Admin: `D:\Taadaa\machine-config\admin.yaml` (`host_id: admin`, `machine_range: [200, 999]`)

### ⚠️ Pitfall Chí Mạng khi Spawn Multi-Cluster Runner
Khi runner/cron (như `tiktok_runner.py`) chạy trên Master Kibe và spawn tiến trình cho cụm Admin:
- Biến môi trường của Master Kibe đang có sẵn `TAADAA_HOST_CONFIG=D:\Taadaa\machine-config\kibe.yaml`.
- Nếu runner tạo tiến trình con (`powershell` / `run_tiktok.py`) bằng `child_env = dict(os.environ)` mà **KHÔNG gán đè** `child_env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"`, tiến trình con sẽ kế thừa cấu hình của Kibe!
- Hậu quả: Ngay khi `run_tiktok.py` đọc danh sách máy Admin (201-280), `taadaa_host.py` kiểm tra máy 201 so với dải `[1, 80]` và lập tức văng:
  ```text
  [HOST] host=kibe machines=1-80 workbook_root=D:\OneDrive\TaadaaData\kibe
  Host guard error: MACHINE_OUT_OF_RANGE: machine=201 không thuộc host kibe (range 1-80). Dừng fail-closed.
  ```
- Tiến trình chết trong vòng 0.5s đầu tiên, không có máy nào khởi chạy.

## 3. Silent Lock De-dup State (`runner_simple_state.json`)
- Nếu runner dùng `subprocess.Popen` chạy nền không đồng bộ và ghi nhận `_save_state(last_window)` ngay lập tức khi Popen trả về (mà không kiểm tra tiến trình có chết sớm / early crash hay không):
- File state sẽ bị đánh dấu là "đã chạy xong window này".
- Tất cả các nhịp cron 15 phút tiếp theo (18:15, 18:30...) thấy `_already_ran(window_key) == True` nên sẽ tự động bỏ qua (skip), tạo ra hiện tượng "im lặng mất phiên cả ca".

## 4. Quy tắc Triển khai An toàn
1. Luôn khai báo `host_config` cụ thể cho từng cluster trong cấu hình runner:
   ```python
   CLUSTERS = [
       {"name": "kibe", "host_config": r"D:\Taadaa\machine-config\kibe.yaml", ...},
       {"name": "admin", "host_config": r"D:\Taadaa\machine-config\admin.yaml", ...},
   ]
   ```
2. Luôn truyền `child_env["TAADAA_HOST_CONFIG"] = str(cluster["host_config"])` vào môi trường con.
3. Đối với các tiến trình chạy nền quan trọng, cần kiểm tra nhanh sau 1-2s hoặc kiểm tra return code trước khi chốt state đã hoàn thành khởi động.
4. Kiểm tra số lượng account hợp lệ (`_count_valid_accounts_for_row`) trong workbook riêng của cluster (`D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`) để nắm chắc số máy thực tế có nick vào ca.
