# Mid-Session ADB Socket Drop & Silent Launcher Crash Triage

## 1. Triệu chứng & Bản chất Lỗi Sụp Socket ADB Giữa Phiên (Cascading Timeout)

### Triệu chứng nhận diện:
- Watchdog cảnh báo: Hàng loạt máy fail (vd: 60/80 máy fail).
- Phân bố kết quả:
  - Đầu phiên: 10 - 20 máy đầu tiên chạy thành công bình thường (swipes >= 16).
  - Giữa phiên: Một loạt máy đồng loạt dính `adb command failed exit=4294967295: error: device '<serial>' not found` hoặc kẹt ở bước `profile_preflight_navigation_blocker`.
  - Cuối phiên: Hàng chục máy còn lại có `swipes_completed: 0` và fail với lý do `hard outer watchdog deadline expired` (hết 2 tiếng phiên nuôi).
- Kiểm tra ngay sau phiên bằng `inspect_machine.py`: Toàn bộ máy đều hiển thị `device` online, pin tốt, không có máy nào offline.

### Cơ chế kỹ thuật:
- Khi kết nối ADB Server (đặc biệt là Remote Cluster như `192.168.110.119:5037`) bị nghẽn mạng LAN, khởi động lại service hoặc drop socket:
  1. Các worker đang chạy đồng loạt mất kết nối tới serial thiết bị.
  2. Logic recovery trong `flows/multi_machine_feed_session.py` cố gắng retry nhiều lần (mỗi lần chờ ADB timeout 15 - 20 phút).
  3. Worker pool bị chiếm dụng 100% bởi các tiến trình recovery treo, không giải phóng slot cho các máy tiếp theo trong queue.
  4. Sau 2 giờ (`120 phút`), watchdog cứng của session kích hoạt `hard outer watchdog deadline expired`, hủy toàn bộ các máy chưa kịp chạy.

### Quy trình Triage O(1):
1. **Kiểm tra liveness hiện tại:**
   Chạy `python D:/Taadaa/tools/inspect_machine.py` để xác nhận danh sách thiết bị hai cụm. Nếu thiết bị đã online đầy đủ -> Khẳng định lỗi là TRANSIENT socket drop / network glitch, không phải đứt cáp vật lý.
2. **Xác định mốc thời gian sụp đổ:**
   Đọc `log.jsonl` của các máy bị lỗi tìm timestamp đầu tiên xuất hiện `device '<serial>' not found`. So sánh để xem có diễn ra đồng loạt trên nhiều máy cùng một phút hay không.
3. **Phân biệt với lỗi đứt cáp USB thật (CM_PROB_PHANTOM):**
   Nếu `inspect_machine.py` hoặc PowerShell `Get-PnpDevice` báo `Present: False` hoặc `CM_PROB_PHANTOM` thì mới là tuột cáp vật lý. Nếu `device` online thì tuyệt đối không đổ thừa hạ tầng.

---

## 2. Lỗi "Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)" do Silent Launcher Crash

### Triệu chứng:
- Watchdog báo: `🏢 【FARM KIBE - MÁY 1-80】 • Trạng thái: Không có lượt chạy nào trong phiên (Chưa chạy / Bị skip)`.
- Thư mục runtime `live/<date>` hoàn toàn không có folder run của phiên đó (vd: thiếu `row-0-1400xx`).

### Cơ chế kỹ thuật:
- `tiktok_runner.py` gọi `run-feed-session.ps1` bằng `subprocess.Popen` với stdout/stderr redirect về `subprocess.DEVNULL`.
- Ngay sau lệnh spawn, runner cha coi như thành công (`rc == 0`) và ghi `_save_state` cập nhật `last_window` (vd: `2026-10-29T14`) vào `runner_simple_state.json`.
- Tuy nhiên, nếu tiến trình con PowerShell gặp lỗi ngoại lệ ngay lúc khởi động (throw trước khi tạo `$ArtifactRoot`, lỗi preflight kiểm tra port hoặc device locks), tiến trình con chết ngay lập tức mà không để lại thư mục run trong `live/`.
- Watchdog quét thư mục `live/<date>`, không thấy folder `row-*` nào trong khung giờ nên kết luận "Chưa chạy / Bị skip".

### Quy trình Triage O(1):
1. Đọc `runner_simple_state.json` tại `runtime/<cluster>/cron-state/runner_simple_state.json`:
   - Nếu `last_window` đã trùng với khung giờ hiện tại -> Runner cha ĐÃ CỐ GẮNG CHẠY và đã spawn, không phải cronjob bị quên tick.
2. Kiểm tra folder `$ArtifactRoot`:
   - Không tồn tại folder -> Khẳng định tiến trình launcher PowerShell con bị crash ở pha pre-flight (trước khi khởi tạo `run_tiktok.py`).
