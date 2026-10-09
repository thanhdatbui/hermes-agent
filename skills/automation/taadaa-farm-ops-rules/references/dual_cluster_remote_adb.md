# Dual-Cluster Execution & Remote ADB Architecture (Kibe Master <-> Admin Remote)

## 1. Bản chất cơ chế Remote ADB trong Farm Dual-Cluster
- **Master Kibe (Máy 1 - 80)**: Chạy ADB Server cục bộ trên port 5037 (`localhost:5037`).
- **Thin Worker / Remote Admin (Máy 201 - 280)**: ADB Server chạy tại `192.168.110.119:5037`.
- **Cơ chế định tuyến ADB Client**:
  - Khi script Python / PowerShell từ Kibe can thiệp vào máy thuộc cụm Admin, nếu chỉ truyền tham số serial mà không trỏ remote server, ADB mặc định trên Kibe sẽ báo lỗi:
    `device 'ce05160521cac10f03' not found`
  - Biến môi trường chuẩn của ADB để trỏ toàn bộ client sang remote server qua socket:
    `ADB_SERVER_SOCKET = tcp:192.168.110.119:5037`
  - Kết hợp cùng cấu hình host isolation:
    `TAADAA_HOST_CONFIG = D:/Taadaa/machine-config/admin.yaml`

## 2. Quy chuẩn cấu hình khi Dispatch Runner từ Master
Khi viết hoặc sửa wrapper cron (`tiktok_runner.py` / `run-feed-session.ps1`):
```python
child_env = dict(os.environ)
if host_config:
    child_env["TAADAA_HOST_CONFIG"] = host_config
    if "admin" in host_config.lower():
        child_env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
    else:
        child_env.pop("ADB_SERVER_SOCKET", None)
```

## 3. Kỷ luật Giờ giấc & Lịch ca (Anti-Hallucination Time Window)
- Trước khi thông báo tình trạng vận hành các ca chạy, Coordinator BẮT BUỘC kiểm tra giờ hiện tại (`datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))`).
- CẤM TUYỆT ĐỐI nói về một ca như thể sắp diễn ra khi giờ thực tế đã vượt qua (ví dụ: thực tế đã 20h47 thì cửa sổ Ca 20h00 đã đóng/đã trôi qua, không phát biểu "sắp tới ca 20h").
