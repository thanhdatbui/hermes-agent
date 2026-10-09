# GPM Profile Lifecycle & Orphan Chrome Cleanup

## Bối cảnh & Nguyên nhân lỗi rò rỉ (Chrome Leak)
Khi chạy tự động hóa hàng loạt trên GPMLogin (login Google, ChatGPT, OAuth token sync):
- **CẠM BẪY CHẾT NGƯỜI CỦA GPM API V3**: Gọi `GET /profiles/stop/{profile_id}` qua Local API v3 luôn trả về `{"success": True}` và báo tắt trên giao diện GPM, **nhưng nó KHÔNG HỀ diệt tiến trình `chrome.exe` thực tế của Windows**!
- Mỗi profile Chrome khi mở sẽ sinh ra 1 tiến trình mẹ và 6–10 tiến trình con (`--type=gpu-process`, `--type=renderer`, `--type=utility`, `--type=crashpad-handler`). Các tiến trình con này KHÔNG chứa tham số `--remote-debugging-port`, do đó cơ chế lọc kill theo port thông thường sẽ bỏ sót toàn bộ tiến trình con.
- Hậu quả: Khi duyệt qua 50–80 profile, các tiến trình Chrome không được giải phóng mà tích tụ lũy kế lên tới hơn 400 tiến trình trong Task Manager, ngốn kiệt tài nguyên RAM/CPU và làm máy tính của user bị đơ cứng (freeze).

## Quy tắc bắt buộc: Dual-Stage Teardown (API Sync + Process Tree Kill)
Trong MỌI script tự động hóa mở GPM profile (đặc biệt trong khối `finally`):

1. **Lưu `process_id` ngay khi start profile:**
   ```python
   r_start = requests.get(f"{GPM_BASE}/profiles/start/{pid}?win_scale=0.8", timeout=25).json()
   proc_id = r_start.get("data", {}).get("process_id")
   ```

2. **Stage 1: Đồng bộ trạng thái qua GPM API:**
   ```python
   try:
       requests.get(f"{GPM_BASE}/profiles/stop/{pid}", timeout=10)
   except Exception:
       pass
   ```

3. **Stage 2: Cưỡng chế diệt sạch cây tiến trình (Parent + All Children) qua `psutil`:**
   Dùng `process_id` đã lưu để truy sát và `kill()` đệ quy toàn bộ cây tiến trình:
   ```python
   if proc_id:
       try:
           proc = psutil.Process(proc_id)
           for child in proc.children(recursive=True):
               try: child.kill()
               except Exception: pass
           proc.kill()
       except (psutil.NoSuchProcess, psutil.AccessDenied):
           pass
   ```

4. **Stage 3: Bảo vệ Chrome cá nhân của User (Port 9222 & Program Files):**
   Tuyệt đối KHÔNG dùng `taskkill /f /im chrome.exe` bừa bãi vì sẽ làm sập trình duyệt đang làm việc của user.
   Nếu quét dọn rác, CHỈ lọc các tiến trình có đường dẫn chứa `gpm_browser` hoặc `GPMLogin`:
   ```python
   def sweep_gpm_zombies():
       for p in psutil.process_iter(['pid', 'name', 'exe']):
           try:
               exe = (p.info['exe'] or '').lower()
               if 'gpm_browser' in exe and 'chrome' in exe:
                   p.kill()
           except Exception:
               pass
   ```

5. **Kỷ luật Concurrency trong Batch:**
   - Trong các batch loop (ver 5sim, sync session, nạp acc), BẮT BUỘC chỉ duy nhất 1 profile GPM được phép mở tại một thời điểm (Concurrency = 1).
   - Trước khi chuyển sang profile tiếp theo, phải xác nhận profile trước đã được đóng sạch sẽ hoàn toàn.
