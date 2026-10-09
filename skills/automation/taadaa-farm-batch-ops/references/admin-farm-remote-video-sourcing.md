# Hướng Dẫn Điều Phối Remote Tải & Render Video Gái Xinh Sang Máy Admin Qua SSH

> 📌 **Bối cảnh kiến trúc**:
> - Máy chính (Kibe): Chạy cào Douyin, kiểm soát luồng tải và render chính cho dàn Kibe (`D:\video goc`, `D:\TIKTOK-videonuoinick`).
> - Máy phụ (Admin - 192.168.110.119): Kết nối qua SSH (`admin-farm`). Tự tải và render cho dàn Admin (`D:\video goc may 2`, `D:\TIKTOK-videonuoinick-admin`).

---

## 1. Thông Số & Hiện Trạng Ổ Đĩa / Workbook Hai Máy

### Host Kibe (Local)
- **Workbook Tik7**: 80 máy. 27 folder ưu tiên đã render xong 100% (1.074 video MP4), 53 folder còn lại đang chứa niche cũ chờ dọn và nạp gái xinh cuốn chiếu.
- **Workbook Tik8**: 80 máy đã đăng rải rác từ 0 đến 4 video (10 máy 0 clip, 7 máy 1 clip, 23 máy 2 clip, 25 máy 3 clip, 13 máy 4 clip, 2 máy 5 clip).
  - **Quy tắc render Tik8 Kibe**: BẮT BUỘC giữ nguyên cột `Video Đã Đăng = N` trong Excel và render với flag `--start-seq <N+1>` để bot upload nối tiếp từ clip mới, không bao giờ reset Excel.

### Host Admin (`admin-farm` / 192.168.110.119)
- **Workbook Tik7 Admin**: 80 máy, 100% `Video Đã Đăng = 0`.
- **Workbook Tik8 Admin**: 80 máy, 100% `Video Đã Đăng = 0`.
- **Thư mục video**:
  - Raw: `D:\video goc may 2\<folder>`
  - Render: `D:\TIKTOK-videonuoinick-admin\<folder>`
- **Dung lượng đĩa trống**: Ổ `D:\` của Admin còn trống khoảng **26.3 GB**.
  - **Kỷ luật cuốn chiếu**: Mỗi đợt tải chỉ nạp từ 15–25 folders (~600–1.000 video) để tránh làm đầy đĩa của máy Admin.

---

## 2. Quy Trình Đồng Bộ Hạ Tầng Lần Đầu Sang Admin

Trước khi bắn lệnh chạy, máy Admin có thể thiếu các file script mới, manifest nguồn hoặc thư viện:

```bash
# 1. Đồng bộ code và manifest sang Admin
scp -q "D:/Taadaa/Tiktok-video/scripts/smart_gaixinh_distributor.py" \
       "D:/Taadaa/Tiktok-video/scripts/ai_channel_filter.py" \
       "D:/Taadaa/Tiktok-video/scripts/gaixinh_claims.py" \
       admin-farm:"D:/Taadaa/Tiktok-video/scripts/"

scp -q "D:/Taadaa/Tiktok-video/data/source_manifest_gaixinh.jsonl" \
       "D:/Taadaa/Tiktok-video/proxy_pool_67.txt" \
       admin-farm:"D:/Taadaa/Tiktok-video/data/"

# 2. Đồng bộ model ViT ONNX (~87MB)
ssh admin-farm "powershell.exe -NoProfile -Command \"New-Item -ItemType Directory -Force -Path 'D:\Taadaa\Tiktok-video\models\onnx'\""
scp -q "D:/Taadaa/Tiktok-video/models/onnx/model_quantized.onnx" admin-farm:"D:/Taadaa/Tiktok-video/models/onnx/"

# 3. Cài đặt thư viện Python trong venv của Admin
ssh admin-farm "powershell.exe -NoProfile -Command \"& 'C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' -m pip install numpy onnxruntime Pillow yt-dlp\""
```

---

## 3. Cạm Bẫy Lệnh PowerShell / SSH Windows & Giải Pháp Tránh Lỗi

### Cạm bẫy 1: Unicode charmap can't encode (cp1252)
- Console Windows của Admin mặc định không dùng UTF-8, khi in tiếng Việt có dấu từ Python (`argparse` help hoặc log) sẽ bị lỗi:
  `UnicodeEncodeError: 'charmap' codec can't encode character ...`
- **Khắc phục**: Luôn đặt biến môi trường UTF-8:
  ```cmd
  set PYTHONUTF8=1
  ```

### Cạm bẫy 2: Nuốt dấu ngoặc kép / escape lồng nhau qua SSH
- Lệnh có đường dẫn chứa dấu cách (`D:\video goc may 2`) khi truyền qua SSH và PowerShell rất dễ bị cắt sai argument (`PositionalParameterNotFound`).
- **Khắc phục**: Ghi toàn bộ lệnh vào một file `.bat` tại máy Kibe, `scp` sang Admin rồi kích hoạt:

```cmd
@echo off
set PYTHONUTF8=1
"C:\Users\Admin\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" "D:\Taadaa\Tiktok-video\scripts\smart_gaixinh_distributor.py" --folders 8,16,24,32,40,48,56,64,72,80 --mode auto --min-videos 40 --parallel 10 --manifest "D:\Taadaa\Tiktok-video\data\source_manifest_gaixinh.jsonl" --proxy-pool "D:\Taadaa\Tiktok-video\data\proxy_pool_67.txt" --output-root "D:\video goc may 2" --render-root "D:\TIKTOK-videonuoinick-admin" --clean-old > "D:\Taadaa\Tiktok-video\admin_download.log" 2>&1
```

Kích hoạt chạy ngầm độc lập qua SSH:
```bash
scp run_admin_download.bat admin-farm:"D:/Taadaa/Tiktok-video/run_admin_download.bat"
ssh admin-farm "powershell.exe -NoProfile -Command \"Start-Process -FilePath 'D:\Taadaa\Tiktok-video\run_admin_download.bat' -WindowStyle Hidden\""
```

---

## 4. Giám Sát Tiến Trình Ngầm Trên Admin

Kiểm tra tiến trình đang chạy:
```bash
ssh admin-farm "powershell.exe -NoProfile -Command \"Get-Process | Where-Object { \$_.ProcessName -match 'python|yt-dlp|ffmpeg' } | Select-Object Id, ProcessName\""
```

Xem log tiến độ tải:
```bash
ssh admin-farm "powershell.exe -NoProfile -Command \"Get-Content 'D:\Taadaa\Tiktok-video\admin_download.log' -Tail 30\""
```
