# OmniRoute Production Update & Patch Re-Application SOP

Tài liệu hướng dẫn quy chuẩn cập nhật mã nguồn, tái áp dụng các bản vá quan trọng và biên dịch OmniRoute trên môi trường Windows Production.

---

## 1. Nguyên Tắc Bất Biến (Invariants)

1. **TUYỆT ĐỐI CẤM `npm run build`:**
   - Full build bao gồm cả Next.js client bundle/frontend ngốn >8GB RAM, gây tràn bộ nhớ (Out-Of-Memory / OOM), treo toàn bộ máy chủ và làm đứt các runner automation.
2. **TUYỆT ĐỐI CẤM Chạy Dev Mode (`npm run dev`):**
   - Dev mode sinh file lock, tiêu tốn CPU/RAM và không đảm bảo tính ổn định production.
3. **BẮT BUỘC Dùng `npm run build:backend`:**
   - Chỉ biên dịch phần backend API & routing logic (`tsup`).
   - Thời gian build cực nhanh: 2–3 phút.
   - Sử dụng RAM tối thiểu (<500MB), an toàn 100% cho server đang chạy.
4. **BẮT BUỘC Bảo Toàn 2 Bản Vá Sản Xuất:**
   - **Fail-Fast Semaphore** (`D:\Taadaa\AI-Tools\patches\omniroute_failfast_semaphore.diff`): Tránh ngâm 30–90s khi gặp account cooldown 403/429, nhảy ngay 0ms sang account tiếp theo.
   - **Hard Connection Binding** (`D:\Taadaa\AI-Tools\patches\omniroute_hard_connection_binding.diff`): Ràng buộc kết nối cứng trên toàn bộ combo strategies (weighted, fill-first, autoCombo...) và đồng bộ cấu hình reasoning specs (`gemini-3.8-flash-tiered`, etc.).

---

## 2. Quy Trình 3 Bước Chuẩn Khi Update OmniRoute

Mỗi khi kéo code mới (`git pull origin main/master`) hoặc nhận bản cập nhật mới của OmniRoute, thực hiện đúng 3 bước:

### Bước 1: Kiểm tra & Tái áp dụng các bản vá sản xuất
Chạy script tự động vá:
```bash
python D:\Taadaa\AI-Tools\scripts\apply_omniroute_patch.py
```
Script sẽ tự động verify và áp dụng cả 2 bản patch:
- `patches/omniroute_failfast_semaphore.diff`
- `patches/omniroute_hard_connection_binding.diff`

### Bước 2: Biên dịch Backend Production
Mở terminal và di chuyển vào thư mục repo OmniRoute:
```bash
cd C:\Users\Kibe\OmniRoute
npm run build:backend
```
*Lưu ý: Không dùng `npm run build`.*

### Bước 3: Restart Dịch Vụ & Kiểm Thử Canary

1. **Khởi động lại tiến trình Node:**
   Khởi động lại OmniRoute để watchdog nạp bundle mới:
   ```powershell
   Get-Process -Name node | Where-Object { $_.Path -like "*OmniRoute*" } | Stop-Process -Force
   ```
   *(Hoặc dừng/chạy lại service/watchdog quản lý OmniRoute)*

2. **Chạy test Canary:**
   Kiểm tra endpoint API và model routing hoạt động ổn định:
   ```bash
   curl -s -X POST http://localhost:20128/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer sk-omniroute-root-key" \
     -d '{"model":"omni-worker","messages":[{"role":"user","content":"ping"}]}'
   ```
   Hoặc cổng dự phòng 20129 nếu đang chạy multi-instance. Xác nhận phản hồi trả về HTTP 200 và có nội dung câu trả lời.
