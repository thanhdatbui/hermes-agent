# GPM Supervisor Concurrency Ceiling & Profile Explosion Prevention

## 1. Hiện Tượng (Incident Pattern)
Thanh Taskbar Windows xuất hiện hàng chục biểu tượng Chrome đánh số (10, 11, 14, 15, ..., 75) xếp san sát nhau, chiếm toàn bộ màn hình và vắt kiệt RAM máy host:
- Cửa sổ ứng dụng đen/treo (`xiaowei.exe` hoặc GPM UI bị nghẽn IPC).
- Hơn 35–40 tiến trình `chrome.exe` chạy ngầm thuộc thư mục `GPMLogin\gpm_browser\gpm_browser_chromium_core_142\chrome.exe`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lệch pha giữa chu kỳ Cronjob và Script Timeout:**
   - Cronjob supervisor (`batch_gpm_5profiles_supervisor.py` hoặc tương tự) được cấu hình chạy định kỳ rất ngắn (ví dụ: mỗi 5 phút `*/5 * * * *`), mỗi tick nhặt tối đa 5 profile vào `ThreadPoolExecutor`.
   - Trong khi đó, script con (`chatgpt_gpm_direct_reg.py`, `codex_5sim_auto_verify.py`, ...) lại có timeout đơn lẻ lên tới 1.800s (30 phút).
2. **Kẹt Form UI OpenAI / GPM:**
   - Trình duyệt điều hướng đến các form xác minh của OpenAI hoặc bị Cloudflare/Turnstile chặn:
     - *"Bạn bao nhiêu tuổi? - OpenAI - GPM-Browser"*
     - *"Kiểm tra hộp thư đến của bạn - OpenAI - GPM-Browser"* (chờ OTP)
     - *"Tạo mật khẩu - OpenAI - GPM-Browser"*
     - *"Bắt đầu | ChatGPT - GPM-Browser"*
   - Khi không có fail-fast xử lý các form này, Playwright/automation treo đợi đủ 30 phút.
3. **Thiếu Global Running Concurrency Ceiling:**
   - Supervisor chỉ kiểm tra proxy port va chạm trong *cùng một tick* hoặc trạng thái account trong file state JSON, nhưng **KHÔNG kiểm tra tổng số profile Chromium thực tế đang còn sống** trong GPMLogin trước khi khởi động đợt mới.
   - Hậu quả: Cứ 5 phút lại mở thêm 5 profile mới trong khi các profile cũ chưa đóng -> Tích tụ lũy tiến 35–50 profile.

## 3. Quy Trình Điều Tra Nhanh O(1) (Triage Playbook)
Khi phát hiện tràn ngập profile Chrome trên Taskbar:
1. **Trích xuất Window Titles để định danh form bị kẹt:**
   ```bash
   tasklist.exe /v /fi "imagename eq chrome.exe" /fo csv
   ```
   *Nhìn cột Window Title sẽ thấy ngay:* Profile số mấy, email nào, đang dừng ở bước nào (ví dụ: "Bạn bao nhiêu tuổi?", "Check your inbox", "ChatGPT").
2. **Xác minh Parent Process:**
   Lấy PPID của các tiến trình `chrome.exe` để khẳng định do `GPMLogin.exe` sinh ra thay vì Chrome thông thường hay trình duyệt người dùng.
3. **Rà soát Cronjob đang hoạt động:**
   Kiểm tra cronjob scheduler (ví dụ qua `cronjob action='list'`) để tìm supervisor đang chạy định kỳ ngắn (5m/10m).

## 4. Giải Pháp Phòng Chống (Prevention Patterns)

### A. Bắt buộc Concurrency Ceiling trước khi Launch
Trước khi chọn candidate và mở bất kỳ profile mới nào, supervisor BẮT BUỘC phải đếm số lượng profile Chromium đang chạy:
```python
def get_running_gpm_profiles_count() -> int:
    try:
        # Cách 1: Query API GPM v3
        r = requests.get("http://127.0.0.1:19995/api/v3/profiles", timeout=3)
        if r.status_code == 200:
            profiles = r.json().get("data", [])
            # Đếm các profile có cờ running hoặc check tiến trình thực tế
            return sum(1 for p in profiles if p.get("running") or p.get("status") == "running")
    except Exception:
        pass
    
    # Cách 2: Đếm qua tasklist / psutil
    count = 0
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if p.info['name'] == 'chrome.exe' and 'gpm_browser' in ' '.join(p.info['cmdline'] or []):
                cmd = p.info['cmdline'] or []
                if not any(arg.startswith('--type=') for arg in cmd):
                    count += 1
        except Exception:
            pass
    return count

# Trong supervisor tick:
MAX_TOTAL_RUNNING_PROFILES = 5
running_count = get_running_gpm_profiles_count()
if running_count >= MAX_TOTAL_RUNNING_PROFILES:
    print(f"[GUARD] Hiện có {running_count}/{MAX_TOTAL_RUNNING_PROFILES} profile GPM đang chạy. Bỏ qua tick để chống tràn Taskbar.")
    return 0
```

### B. Giảm Timeout Từng Form & Fail-Fast
- Giảm timeout của `run_cmd` đăng ký từ 1.800s xuống tối đa 300s - 450s (5-7.5 phút).
- Bổ sung handler tự động cho màn hình "Bạn bao nhiêu tuổi?" (`input[name="age"]`, `input[type="number"]`) hoặc chọn ngày sinh mặc định và click Continue.
- Nếu kẹt form quá 60s không tiến triển, chủ động raise exception và thoát profile thay vì sleep vô tận.

### C. Cơ chế Đóng Profile Triệt Để (Guaranteed Teardown)
- Đảm bảo khối `finally` luôn gọi `/api/v3/profiles/close/{pid}`.
- Kiểm tra lại sau 5s, nếu tiến trình `chrome.exe` tương ứng với `--user-data-dir` của profile đó vẫn còn tồn tại thì cưỡng chế kill PID đó để giải phóng Taskbar và RAM.
