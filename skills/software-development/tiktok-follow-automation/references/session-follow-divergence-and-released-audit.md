# Session Follow Divergence & Released Follow Audit

## 1. Cơ chế Phân loại "Nhả follow" (Watchdog Telemetry)

Trong `feed_session_watchdog.py`, trạng thái follow của từng máy được phân loại bởi hàm `classify_machine_follow_result(fd)`:

```python
if status == "FOLLOW_FAILED" and fd.get("follow_failed") is True:
    return "released", f_reason
```

- **Nhả follow (`fl_released`)**: Máy attempt follow nhưng bị trả về `status == "FOLLOW_FAILED"` và cờ `follow_failed == True` (thường do TikTok drop follow ngay sau khi bấm hoặc nút follow tự revert).
- **Phân nhóm theo số lượt (`format_released_follows`)**:
  - `rel_0` (Nhả liền, 0 lượt): Máy bị nhả ngay ở lượt đầu tiên (0 lượt thành công ghi nhận).
  - `rel_1_4` (1 - 4 lượt): Hoàn thành 1-4 lượt trước khi bị fail/nhả.
  - `rel_5_9` (5 - 9 lượt): Hoàn thành 5-9 lượt.
  - `rel_10_plus` (10+ lượt): Đã đạt ngưỡng cao.

## 2. Tại sao Danh sách Nhả Follow Khác nhau giữa Phiên 1 và Phiên 2 trong Cùng 1 Row / Ca?

Đây là **hành vi đúng thiết kế (by design)** vì các lý do cốt lõi sau:

1. **Snapshot theo phiên độc lập:**
   - Mỗi phiên chạy tạo ra 1 artifact/log JSON riêng biệt.
   - Watchdog đánh giá `fd` dựa trên log của chính phiên đó, không tích lũy lịch sử phiên trước.
2. **Quota / State Consumption:**
   - Nếu ở Phiên 1, nick X đã follow đủ quota được giao hoặc rơi vào trạng thái `follow-released / đã follow sẵn`, sang Phiên 2 nick đó sẽ được đánh dấu `SKIPPED` (thuộc nhóm `other_skipped`) chứ không attempt follow nữa -> không còn nằm trong list `released`.
3. **Organic Rest (~33%) Dynamic Rotation:**
   - Danh sách máy nghỉ dưỡng sinh (organic rest) được tính toán theo slot/thời điểm.
   - Máy nghỉ ở Phiên 1 có thể hoạt động ở Phiên 2 (và ngược lại), làm thay đổi tập máy thực sự tham gia follow.
4. **Môi trường & Mạng biến động (Proxy / UI / TikTok Rate Limit):**
   - Phiên 1 gặp proxy chậm/chập chờn hoặc TikTok pop-up -> fail ngay từ đầu (`rel_0`).
   - Phiên 2 proxy đã refresh hoặc IP sạch hơn -> follow mượt -> không nhả.
5. **Mode 2 (Anchor Mining) phụ thuộc nguồn:**
   - Mỏ anchor được khai thác động theo từng thời điểm. Nếu Phiên 1 trúng mỏ cạn hoặc account bị TikTok hạn chế tạm thời, sang Phiên 2 đổi anchor hoặc đổi pool target sẽ cho kết quả khác.

## 3. Quy trình Đối soát khi Có Lệch Bất Thường

1. Đọc log chi tiết của từng máy bị nhả ở Phiên 1: kiểm tra trường `reason` và `details` trong log JSON artifact.
2. Đối soát với TikTok Web: Xem dòng `+ Đối soát TikTok Web (+N Following thật - Khớp X% so với script báo)` của Watchdog.
3. Không vội kết luận lỗi script khi thấy list nhả đổi phiên: chỉ can thiệp khi cùng 1 máy bị `rel_0` liên tục qua nhiều ca/nhiều ngày (dấu hiệu nick bị shadowban hoặc checkpoint account).
