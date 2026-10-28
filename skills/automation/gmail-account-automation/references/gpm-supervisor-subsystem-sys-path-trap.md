# GPM Supervisor Subsystem: Subprocess sys.path Trap & Batch False-Failure Diagnosis

## 1. Triệu chứng False-Failure Loop (Chết cứng hàng loạt trong vài ms)
Trong các vòng lặp giám sát vòng đời tài khoản (GPM Hotmail/ChatGPT Supervisor):
- **Hiện tượng**: Một loạt tài khoản trong cùng 1 tick supervisor đều trả về `status: FAILED`, `detail: "Hotmail login that bai"`, và timestamp `at` của các tài khoản giống hệt nhau từng mili-giây.
- **Hệ quả**: Sau 3 tick (khoảng 15 phút), toàn bộ các nick này chạm trần `login_retry_count = 3` và bị đẩy vào `QUARANTINE` hàng loạt, dù mật khẩu trong Excel và proxy hoàn toàn chính xác.

## 2. Root Cause: Bẫy Lọc `sys.path` Khi Gọi Subprocess
Trong script đăng nhập con (ví dụ `D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py`):
```python
# CỐ TÌNH LỌC ĐỂ NÉ XUNG ĐỘT C-EXTENSION (greenlet...):
sys.path = [p for p in sys.path if not ("hermes" in p.lower() and "site-packages" in p.lower())]
```
- Khi Hermes cronjob thực thi, interpreter đang chạy là Python của venv Hermes (`.../hermes/hermes-agent/venv/Scripts/python.exe`).
- Dòng code trên đã strip **toàn bộ** thư mục `site-packages` của môi trường venv vì đường dẫn có chứa chữ `"hermes"`.
- Kết quả: Khi script import `gpm_client` -> `gpm_client` import `requests` -> văng ngay `ModuleNotFoundError: No module named 'requests'` trong 0.001 giây!
- Subprocess thoát với exit code `1` ngay lập tức trước khi kịp khởi động Playwright hay kết nối tới GPM API.

## 3. Quy Tắc Chẩn Đoán Phân Biệt (Timing Diagnostic Pattern)
- **Lỗi mạng / Browser / Proxy thật**: Thời gian thực thi `page.goto` hoặc form login luôn mất tối thiểu **10s - 45s**. Các tài khoản trong batch 5 workers sẽ kết thúc so le lệch nhau vài giây.
- **Lỗi môi trường / ImportError / Crash script**: Toàn bộ batch kết thúc cùng một thời điểm chính xác tới mili-giây (do supervisor lặp qua kết quả threadpool sau khi các worker crash đồng loạt). Khi thấy dấu hiệu này, **bắt buộc kiểm tra ImportError của sub-script trước tiên**, không đoán mò sang lỗi proxy hay sai mật khẩu.

## 4. Quy Trình Cứu Hộ & Reset Quarantine Chuẩn Farm
1. **Kiểm tra file state**:
   - Kibe: `D:/Taadaa/runtime/kibe/cron-state/batch_gpm_5profiles_supervisor_state.json`
   - Admin: `D:/Taadaa/runtime/admin/cron-state/batch_gpm_5profiles_supervisor_state.json`
2. **Khôi phục trạng thái hàng đợi**:
   - Chạy công cụ phục hồi chuyên dụng:
     ```bash
     python D:/Taadaa/tools/reset_admin_quarantine.py
     ```
   - Script tự động đưa các nick `QUARANTINE` về `PENDING`, reset `login_retry_count = 0` và xóa `error = None` để supervisor tiếp tục chu kỳ an toàn.
