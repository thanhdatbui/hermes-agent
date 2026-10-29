# Case Study: Multi-Cluster Date Scanning Parity & XiaoWei Port 5038 False-Positive Fleet Block

## 1. Multi-Cluster Date Scanning Parity (Unilateral Local Log Scraping)
### Bối cảnh:
Trong `feed_session_watchdog.py`:
```python
all_date_dirs = sorted([
    d for d in os.listdir(LIVE_ROOT)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= retention_cutoff and os.path.isdir(os.path.join(LIVE_ROOT, d))
]) if os.path.exists(LIVE_ROOT) else []

dates_to_check = [(d, d == today) for d in all_date_dirs]
```
- `LIVE_ROOT` được gán cứng theo Kibe (`D:/Taadaa/runtime/kibe/live`).
- Khi Kibe bị nghẽn (chưa tạo thư mục `2026-10-29`), `all_date_dirs` chỉ chứa các ngày cũ `[2026-10-22 ... 2026-10-28]`.
- Hệ quả: Ngày hôm nay (`today`) bị loại khỏi `dates_to_check`. Dù cụm Admin (`D:/Taadaa/runtime/admin/live/2026-10-29`) đã hoàn thành cả 2 phiên lướt feed và upload video thành công, Watchdog hoàn toàn không quét Admin cho ngày hôm nay và im lặng, không bắn bất kỳ báo cáo nào.

### Quy tắc bất biến (Invariant):
1. **Always Include Today in `dates_to_check`:** Danh sách ngày cần đối soát bắt buộc phải luôn chứa `(today, True)`, không phụ thuộc vào việc thư mục ngày đã tồn tại trên đĩa hay chưa.
2. **Union Date Dirs Across All Clusters:** Khi quét thư mục lưu trữ, phải lấy hợp (`set.union`) của tất cả các `cluster["live_root"]` thay vì chỉ quét một mình local directory của một cluster.

---

## 2. XiaoWei Port 5038 False-Positive Fleet Block & Ground-Truth Probe
### Bối cảnh:
- Runner `run-feed-session.ps1` có đoạn preflight gate ném lỗi:
  ```powershell
  if (-not (Clear-XiaoWeiPort5038)) {
      throw "PREFLIGHT_PORT_5038_BLOCKED: Port 5038 is occupied. XiaoWei ADB must be stopped before starting feed session."
  }
  ```
- Khi User mở XiaoWei để đặt hàng trên 1 máy, XiaoWei mở daemon ADB rỗng trên port 5038 (`tools/adb -P 5038 nodaemon server start`).
- Preflight gate thấy port 5038 có listener liền `throw` chặn đứng toàn bộ 80 máy của farm.
- Coordinator vội vã suy diễn lý thuyết ("hai ADB tranh chấp làm sập bus USB 80 máy"), trong khi thực tế:
  * Probe `adb -P 5038 devices` cho thấy: 0 devices attached (XiaoWei không claim bất kỳ máy nào).
  * Probe `adb devices` (port 5037): 78 máy vẫn online và điều khiển hoàn hảo trong 0.12s.
  * Máy User dùng đặt hàng đã có cơ chế Device Lock (`machine_<M>.lock.json`) để runner tự động skip. 79 máy còn lại hoàn toàn có thể chạy nuôi bình thường.

### Quy tắc bất biến (Invariant):
1. **Cấm Preflight Block Cả Fleet Vì Port Thứ Ba:** Không chặn đứng cả farm chỉ vì một port công cụ phụ trợ đang mở. Phải probe thực tế xem port đó có claim thiết bị hay không.
2. **Tận Dụng Device Lock Cấp Máy:** Tôn trọng mô hình multi-tenant: máy nào có lock thì skip, các máy còn lại tiếp tục vận hành bình thường.
3. **Cấm Suy Diễn Lý Thuyết Suông Đổ Lỗi Hạ Tầng:** Bắt buộc dùng lệnh trích xuất / probe thực tế trước khi kết luận về xung đột phần cứng.
