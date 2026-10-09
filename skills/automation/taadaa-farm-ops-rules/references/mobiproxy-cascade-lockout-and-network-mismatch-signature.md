# MobiProxy 4G Cascade Lockout, Watchdog Stampede & Chẩn Đoán Lỗi Mismatch Tài Khoản (08/09/2026)

## 1. Triệu Chứng Điển Hình
- **Batch nuôi acc fail diện rộng (>50% dàn máy):** Báo lỗi signature `script-blocker:profile username still mismatched after switch` trên hàng loạt máy (ví dụ 39/68 máy).
- **Trạng thái mạng trên thiết bị S7:** Thanh trạng thái hiện biểu tượng Wi-Fi ba vạch kèm thông báo `Không có Internet`.
- **Phản hồi Sing-box:** Kết nối thử qua cổng local `192.168.110.2:200xx` trả về ngay lập tức `HTTP/1.1 502 Bad Gateway`.
- **Giao diện Web MobiProxy (`test.taadaa.click`):** Báo `ERR_CONNECTION_REFUSED` trên Chrome, hoặc trang web bị đơ/timeout không load được; API `/proxy_getlist` bị timeout.

---

## 2. Phân Tích Cơ Chế Gốc Rễ (Root Cause Mechanism)

### A. Vì sao mất mạng lại sinh ra lỗi `profile username still mismatched after switch`?
1. **Runner mở Account Switcher thành công:** Do giao diện Bottom Sheet đã được cache cục bộ trong app TikTok, runner vẫn tìm thấy tài khoản mục tiêu theo đúng tên hiển thị / content-desc (ví dụ `ahmetsguthe17`).
2. **Lệnh tap được gửi nhưng app không chuyển session:** Runner tap đúng tọa độ của dòng tài khoản (center $x=540$), nhưng do **không có Internet** để kết nối đến máy chủ TikTok đồng bộ session đăng nhập mới, app TikTok âm thầm giữ nguyên tài khoản hiện tại.
3. **Runner verify thất bại:** Sau khi chờ settle và quay lại Profile, username hiển thị trên màn hình vẫn là nick cũ $\rightarrow$ runner kết luận switch thất bại và ném lỗi `profile username still mismatched after switch`.
👉 **Quy tắc:** Khi thấy lỗi mismatch username bùng phát đồng loạt trên diện rộng (>15-20% dàn máy), **99% là do proxy/mạng upstream bị rớt**, không phải do TikTok update UI hay lỗi click.

### B. Hiệu Ứng Thác Đổ (Watchdog Stampede) Làm Sập Box MobiProxy
1. **Lỗi thiết kế chu kỳ Cron quá ngắn:** Cronjob `mobiproxy-auto-healer-watchdog` được cấu hình chạy mỗi 1 phút (`*/1 * * * *`).
2. **Thiếu Singleton Process Lock:** Khi nhiều cổng proxy bị chết (ví dụ 22/32 cổng), script `mobiproxy_auto_healer.py` phải gọi tuần tự `/proxy_recreat` cho từng cổng, chờ 5-10s/cổng $\rightarrow$ tổng thời gian thực thi của một ca heal kéo dài >3-4 phút.
3. **Tiến trình chồng chéo (Process Accumulation):** Do không có file lock ngăn chạy trùng, mỗi phút scheduler lại đẻ thêm 1 tiến trình mới. Các tiến trình này (3-5 instances song song) đồng loạt gửi dồn dập các request `/proxy_recreat` vào Box MobiProxy.
4. **Kernel/Hardware Hang:** Box MobiProxy (phần cứng mini/ARM) bị quá tải CPU/IO, driver USB quản lý 32 modem (`/dev/ttyUSB*`) bị kẹt trong trạng thái D-state (uninterruptible sleep). Dịch vụ Nginx/PHP-FPM trên Box bị nghẽn hoàn toàn, khiến toàn bộ 32 cổng proxy bị ngắt kết nối và web UI không thể truy cập.

### C. Cạm Bẫy Trình Duyệt Chrome: HTTP vs HTTPS
- Web UI quản lý của Box MobiProxy chạy trên web server thuần `http://` (cổng 80), **không cài chứng chỉ SSL/HTTPS (cổng 443)**.
- Khi người dùng gõ `test.taadaa.click` trên Google Chrome, trình duyệt tự động thêm tiền tố `https://`. Vì cổng 443 trên Box bị đóng, Chrome lập tức báo lỗi `ERR_CONNECTION_REFUSED`.
- **Khắc phục:** Bắt buộc gõ rõ ràng `http://test.taadaa.click` trên thanh địa chỉ.

---

## 3. Quy Trình Cứu Hộ Chuẩn (Recovery Runbook)

### Bước 1: Ngắt Cơn Bão Stampede Trên Máy Host
```bash
# 1. Tạm dừng cronjob healer để ngăn đẻ tiến trình mới
hermes cron pause <job_id_mobiproxy_healer>

# 2. Kill sạch toàn bộ tiến trình healer đang chạy ngầm
powershell -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*mobiproxy*' } | Stop-Process -Force"
```

### Bước 2: Hạ Nhiệt / Reboot Phần Cứng Box MobiProxy
- Chờ 1-2 phút để các modem 4G xả nghẽn và kết nối lại mạng di động.
- Nếu sau 2 phút cổng web vẫn timeout (do driver USB bị deadlock trong nhân Linux): **Rút nguồn cắm lại (reboot cứng) cục Box MobiProxy**.

### Bước 3: Kiểm Tra Lại Độ Thông Suốt Của Từng Cổng
```bash
# Kiểm tra trực tiếp cổng upstream qua curl từ máy host
curl -s -m 8 -x http://test.taadaa.click:5101 http://api.ipify.org
curl -s -m 8 -x http://192.168.110.2:20001 http://api.ipify.org
```

---

## 4. Hardening Phòng Chống Hồi Quy
1. **Singleton Guard cho Watchdog:** Bắt buộc bọc cơ chế Singleton (file lock `mobiproxy_healer.lock`) ở đầu script `mobiproxy_auto_healer.py`. Nếu ca trước chưa chạy xong, ca sau phải tự động thoát ngay (exit 0) mà không tạo tiến trình đè.
2. **Giãn cách chu kỳ Cron:** Không để lịch `*/1 * * * *` cho watchdog có tác vụ can thiệp nặng. Tối thiểu phải là `*/3 * * * *` hoặc `*/5 * * * *`.
3. **Batch Rate Limit:** Giới hạn số lượng modem được phép recreate tối đa trong một lượt chạy (ví dụ tối đa 3-5 modem/lần, không recreate ồ ạt 20+ modem cùng lúc).
