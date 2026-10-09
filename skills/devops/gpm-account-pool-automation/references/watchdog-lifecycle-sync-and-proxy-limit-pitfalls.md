# GPM Watchdog Lifecycle Sync & Proxy Rate Limit Pitfalls

## 1. Bug đếm proxy ảo (pre-increment proxy_count) làm tê liệt toàn bộ Pool
- **Hiện tượng**: Watchdog báo tất cả các cổng proxy đều chạm trần (`proxy_limit 2/port/ngày`) và tự kết thúc `finished: true`, dù thực tế cả tuần không có port nào được chạy login.
- **Nguyên nhân**: Bộ đếm `proxy_count[port] += 1` bị đặt nhầm bên trong vòng lặp lọc ứng viên (`get_candidates()`) thay vì khi thực sự trigger worker (`run_login`). Khi lưu vào state JSON, toàn bộ port bị điền khống `2`, khiến các lần cron tiếp theo đọc state thấy tất cả port đều chạm trần $\rightarrow$ bị chặn 100%.
- **Quy tắc chuẩn**:
  - Trong hàm lọc ứng viên (`get_candidates`): CHỈ dùng bản sao tạm `current_run_proxy_count = dict(proxy_count)` để giới hạn số lượng trong batch của lần duyệt hiện tại. Tuyệt đối không cộng dồn vào `proxy_count` bền vững.
  - `proxy_count` bền vững CHỈ được tăng khi một tác vụ thực sự hoàn tất chạy qua worker:
    ```python
    for fut in as_completed(futures):
        res = fut.result()
        processed.append(res["email"])
        port = res.get("port")
        if port:
            proxy_count[port] = proxy_count.get(port, 0) + 1
    ```

## 2. Watchdog tự hành quản lý vòng đời profile GPM (sync_gpm_profiles_lifecycle)
- **Hiện tượng**: Kho Excel có hàng chục Gmail LIVE mới nhưng Watchdog login bỏ qua hết vì kiểm tra `if email not in gpm_emails: continue`.
- **Yêu cầu cốt lõi**: Mỗi script watchdog login GPM phải có module tự hành `sync_gpm_profiles_lifecycle()` chạy ngay đầu mỗi tick:
  1. Quét file Master Excel (sheet `Kibe_Farm_S7`).
  2. **Dọn dẹp**: Xóa profile GPM của các Gmail bị `DIE / BAN / SUSPENDED`.
  3. **Tự sinh Profile LIVE**: Quét các Gmail `LIVE` chưa có profile, lấy chuỗi Proxy 4G tương ứng từ Excel, tự động gọi GPM Client/API để sinh Profile chuẩn.
  4. **Farm Safety Invariant**: Tuyệt đối **KHÔNG ĐÒI HỎI ĐIỆN THOẠI S7 ONLINE ADB** khi tạo profile GPM. Profile GPM tạo hoàn toàn độc lập trên PC qua GPMClient/API v3.

## 3. Triage báo cáo `[LOGIN GPM ĐÊM - TỔNG KẾT] ✓ 0 | ✗ N` (Hard Phone Checkpoint Fail-Fast)
- **Hiện tượng**: Watchdog ca tối báo cáo `✓ 0 | ✗ 36 | proxy_limit 2/port/ngày | Hoàn tất ca tối`.
- **Bản chất & Cơ chế an toàn (Fail-Safe)**:
  1. Khi login tài khoản Google lần đầu trên môi trường PC browser qua proxy, Google phát hiện thiết bị/môi trường mới và kích hoạt màn hình chặn `challenge/iap`: *"Có điều bất thường về hoạt động của bạn / Xác minh số điện thoại để nhận mã SMS"* (Hard Phone Checkpoint).
  2. **Kỷ luật an toàn tối cao Farm**: CẤM TUYỆT ĐỐI spam SĐT lạ / bừa bãi vào Google Checkpoint để tránh dẫn đến khóa vĩnh viễn (DIE) tài khoản.
  3. Script `run_oauth_s7_pipeline.py` nhận diện đúng `hard_phone_checkpoint`, lưu ảnh chụp bằng chứng vào `D:\Taadaa\GPM auto\debug_screenshots`, và lập tức abort `PHONE_CHECKPOINT`, không thử lại liên tục.
  4. Watchdog tôn trọng trần `proxy_limit 2/port/ngày` và cửa sổ thời gian ca tối (21:30 - 23:45). Khi hết ca hoặc hết candidate thỏa mãn, watchdog ghi nhận kết quả, kết thúc phiên an toàn (`finished: true`), và giải phóng tài nguyên để farm chuyển sang Ca 4 (Đêm) lướt feed TikTok trên máy thật S7.
  5. **Hướng hành động chuẩn**: KHÔNG vội vàng sửa code ép đăng nhập. Giữ nguyên tài khoản ngâm trên thiết bị gốc S7 (nơi tài khoản đang LIVE an toàn) và chỉ can thiệp thủ công hoặc dùng số điện thoại chỉ định có kiểm soát khi thực sự cần thiết.

