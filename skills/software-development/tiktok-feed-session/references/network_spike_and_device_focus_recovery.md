# Xử Lý Network Spike, Proxy Burst & Focus Recovery (Nuôi Feed TikTok)

## 1. INVARIANT HẠ TẦNG MẠNG FARM: ĐÃ DẸP VICHANGER HOÀN TOÀN
- **Trạng thái thực tế:** Toàn bộ Farm (Kibe 1-80 & Admin 201-280) đã dẹp ViChanger app trên máy Android, chuyển sang **Global HTTP Proxy** (`192.168.110.2:200xx` trên Kibe).
- **CẤM TUYỆT ĐỐI:** Báo user "restart ViChanger" hoặc chẩn đoán do ViChanger.
- **Lưu ý về Log nhầm lẫn:** Nhãn `blocked-proxy-vpn` trong `summary.txt` hay log runner chỉ là legacy category name trong `vpn_preflight.py` khi thiết bị offline ADB / mất kết nối mạng, hoàn toàn KHÔNG liên quan đến app ViChanger.

## 2. CHUẨN HOÁ MAX_WORKERS & STAGGER TRÁNH BURST LATENCY
- **Hiện tượng:** Khi chạy batch 40 worker cùng lúc (`max_workers=40`, stagger 2-8s), lưu lượng request ồ ạt qua proxy 4G Mobi / Mikrotik gây spike độ trễ tức thời (>4-5s) -> TikTok nạp video đầu không kịp -> xuất hiện màn hình *"Thử lại"* / *"Không có kết nối Internet"* -> Classifier bắt cờ `manual-needed:network` và dừng máy với signature `detector-miss:network/error/retry marker detected`.
- **Thông số chuẩn hoá bắt buộc:**
  - `max_workers = 30` (Hạ từ 40 xuống 30 máy song song).
  - `stagger = (4000, 10000)` (4s - 10s delay ngẫu nhiên giữa các lần kích hoạt máy để rải đều băng thông proxy).
  - Áp dụng trong: `multi_machine_feed_session.py` và CLI `--max-workers 30 --machine-start-stagger-ms 4000,10000` trong `run_tiktok.py`.

## 3. CHẨN ĐOÁN LỖI FOCUS TIKTOK (VÍ DỤ MÁY 19)
- **CẤM VỘI KẾT LUẬN APP VĂNG / CRASH:**
  - Khi script báo `prepare-tiktok failed to focus TikTok after launch` (focus vẫn ở `com.sec.android.app.launcher`), BẮT BUỘC kiểm tra logcat lọc `am_crash`, `fatal`, `anr`, `exception`.
  - Nếu logcat sạch (0 crash): Nguyên nhân là do tiến trình test bridge cũ (`uiautomator stub` / `UiTestAutomationBridge`) bị kẹt ngầm trên thiết bị khiến hệ điều hành bị hoãn (pause timeout), app TikTok bị trễ không kịp lên foreground trước khi hết 10 lần đếm timeout của script.
- **Biện pháp xử lý:**
  - Dọn sạch tiến trình rác: `pkill -f uiautomator` trên thiết bị.
  - Khởi động lại TikTok: `am force-stop` rồi `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`.
  - Kiểm tra UI qua ATX-agent RPC port 7912 (`dumpWindowHierarchy`) nếu `uiautomator dump` bị kẹt `could not get idle state`.

## 4. KỶ LUẬT TRẢ LỜI USER KHI CÓ FARM ALERT
- Khi user hỏi *"báo lỗi gì"*, *"sao nãy báo lỗi"*, *"tóm lại bị gì mà lỗi"*:
  1. Trả lời **TRỰC DIỆN** lỗi lúc chạy là gì (tên signature, mã lỗi trong code).
  2. Giải thích **NGUYÊN NHÂN GỐC RỄ** (Spike mạng 4G khi bắn 40 máy / Bridge kẹt / Rớt cáp USB).
  3. Báo cáo **TRẠNG THÁI HIỆN TẠI** (đã hồi phục thế nào, test canary ra sao).
  4. Nêu rõ **HƯỚNG KHẮC PHỤC TRIỆT ĐỂ** (giảm worker, tăng stagger, pre-flight clean).
  - TUYỆT ĐỐI KHÔNG vòng vo né tránh bằng câu "hiện tại bình thường rồi" mà bỏ qua việc giải thích lỗi lúc chạy.
