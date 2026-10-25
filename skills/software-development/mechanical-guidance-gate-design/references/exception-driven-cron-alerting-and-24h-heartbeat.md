# Exception-Driven Cron Alerting & 24H Heartbeat Governance ("Silent on Nominal, Loud on Anomaly")

## 1. Bối cảnh & Tử Huyệt "Im Lặng Giả Tạo" (False-Negative Masking)
Khi áp dụng nguyên tắc *"Không có vi phạm thì im lặng"* cho các cron report định kỳ của farm để chống spam Telegram, hệ thống đối mặt với rủi ro nghiêm trọng:
Nếu một script watchdog gặp lỗi ngầm (file DB bị lock, schema thay đổi, API timeout, ngoại lệ chưa bắt, hoặc crash giữa chừng) và thoát âm thầm $\to$ watchdog tưởng là bình thường nên không bắn thông báo. Operator thấy điện thoại im lặng sẽ lầm tưởng Farm đang chạy êm, trong khi thực tế hệ thống đã sập trong bóng tối.

## 2. Tiêu Chuẩn Kiến Trúc 3 Trạng Thái Bắt Buộc
Mọi cron watchdog và report bắt buộc phân định theo 3 trạng thái:
1. **`NOMINAL` (Khỏe mạnh thực sự):** BẮT BUỘC phải chứng minh được: nguồn dữ liệu đọc được, có dữ liệu tươi ($\ge 1$ item hoặc có lý do `allow_empty: true` bằng văn bản), và mọi metric nghiệp vụ nằm trong ngưỡng an toàn. Khi `NOMINAL`, script thoát với stdout rỗng $\to$ Hermes scheduler (`no_agent: true`) im lặng tuyệt đối.
2. **`ANOMALY` (Có sự cố / vi phạm):** Metric vượt ngưỡng, nick kẹt, tài khoản die/checkpoint, hoặc vi phạm gate $\to$ Xuất bản tin markdown có cấu trúc gửi thẳng về Telegram.
3. **`UNKNOWN` (Lỗi ngầm / Ngoại lệ / Mất nguồn):** Exception chưa bắt, file mất, DB lock, timeout $\to$ **MẶC ĐỊNH BỊ COI LÀ `ANOMALY` (P1)** và bắn cảnh báo ngay lập tức. CẤM TUYỆT ĐỐI nuốt ngoại lệ bằng `except: pass` để im lặng.

## 3. Kiến Trúc Lõi O(1): `CronRun` Context Manager
Tất cả watchdog con chỉ cần bọc logic trong `CronRun` từ `cron_alert_core.py`:
```python
from cron_alert_core import CronRun

with CronRun("farm_render_download_watchdog") as run:
    # 1. Kiểm tra nguồn dữ liệu tươi (Fail-Closed)
    rows = run.require_source(load_db_records, name="render_db", allow_empty=False)
    
    # 2. Đánh giá metric với lambda an toàn
    run.check("stale_jobs", count_stale, ok=lambda v: v == 0, severity="P1")
    run.check("disk_free_gb", free_gb, ok=lambda v: v >= 10.0, severity="P0")
    
# __exit__: Tự động tổng hợp -> Ghi state JSON -> Nếu ANOMALY thì print Markdown -> Nếu NOMINAL thì print rỗng.
```

## 4. Cơ Chế Heartbeat 24H Độc Lập (`cron_heartbeat.py`)
Để triệt tiêu rủi ro chính cronjob bị chết (Dead Man's Switch), một tiến trình độc lập `cron_heartbeat.py` được lên lịch chạy vào **00:00 UTC (07:00 VN)** hàng ngày:
* **Không import logic của các watchdog con:** Chỉ đọc trực tiếp các file state JSON tại `runtime/cron_health/<script>.json`.
* **Phát hiện `STALE`:** Nếu `now - last_end > 2 * interval + 30m` $\to$ Cảnh báo script đã bị bỏ cữ hoặc cronjob bị vô hiệu hóa.
* **Phát hiện `HUNG`:** Nếu `last_start > last_end` và quá `max_runtime` $\to$ Cảnh báo script đang bị treo vô hạn.
* **Bản tin duy nhất trong ngày:** Dù tất cả đều OK, đúng 07:00 VN vẫn gửi 1 bản tin tóm tắt `💓 [FARM CRON HEARTBEAT — 24H]` xác nhận hệ thống sống khỏe. Các khung giờ khác trong ngày giữ im lặng tuyệt đối.
