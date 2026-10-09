# LƯU Ý VẬN HÀNH & CHẨN ĐOÁN LỖI FEED TOÀN FARM (CẬP NHẬT 2026-09-22)

## 1. DẸP VICHANGER & CHUYỂN TOÀN BỘ SANG GLOBAL HTTP PROXY
- **Hiện trạng kiến trúc:** Farm đã **dẹp hoàn toàn ViChanger**. Toàn bộ 80 máy Kibe chạy qua **Global HTTP Proxy** (`192.168.110.2:200xx`).
- **CẤM TUYỆT ĐỐI:** Suy đoán lỗi do app ViChanger hoặc đưa ra giải pháp restart/cài đặt ViChanger.
- **Giải mã nhãn `blocked-proxy-vpn`:** Đây là tên phân loại legacy trong `vpn_preflight.py` khi máy mất mạng/rớt kết nối ADB vật lý, hoàn toàn không liên quan đến app ViChanger.

## 2. CHẨN ĐOÁN LỖI KHỞI ĐỘNG TIKTOK KHÔNG FOCUS (CASE M19)
- **Triệu chứng:** Log báo `prepare-tiktok failed to focus TikTok after launch`, focus kẹt ở `com.sec.android.app.launcher` hoặc `com.android.systemui`.
- **Bản chất kỹ thuật:** Không phải app TikTok bị crash/văng. Tiến trình `com.ss.android.ugc.trill` bị kẹt ở `D-state` (Uninterruptible Sleep / I/O wait) do dịch vụ `UiTestAutomationBridge` cũ bị kẹt trên thiết bị.
- **Quy trình xử lý chuẩn:**
  1. Kill bridge kẹt: `adb -s <serial> shell pkill -f uiautomator`
  2. Force-stop TikTok: `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
  3. Khởi động lại: `adb -s <serial> shell am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`
  4. Lấy XML qua `atx-agent` port 7912 RPC (`dumpWindowHierarchy`) để phân loại màn hình feed.

## 3. CHẨN ĐOÁN LỖI RỚT ADB VẬT LÝ
- **Triệu chứng:** Log báo `blocked-proxy-vpn` hoặc `config-error: Device serial was not found in adb devices` (như M10, M30).
- **Hiện trường:** `adb devices` trả về `device not found`.
- **Hành động:** Báo user cắm lại cáp USB vật lý hoặc bật lại USB debugging, không can thiệp bằng script vô ích.
