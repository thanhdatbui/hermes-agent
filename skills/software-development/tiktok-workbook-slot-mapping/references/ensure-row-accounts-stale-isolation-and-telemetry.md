# Ensure Row Accounts: Stale Isolation, Telegram Guard & Integration Testing

## 1. Vấn đề Stale Artifacts trong Multi-Runner Batches
Khi các batch reg hoặc worker chạy bất đồng bộ, các thư mục con trong `artifacts/runs/social-batch-all/` có thể còn sót lại từ lần chạy trước (có thể cách hàng giờ hoặc hàng ngày).
Nếu `apply_results` hoặc `send_telegram_summary` chỉ lấy `dirs[0]` theo `st_mtime` mà không đối chiếu với thời điểm batch thực tế bắt đầu:
- Có nguy cơ đọc nhầm artifact cũ nếu batch hiện tại chưa kịp ghi file hoặc bị huỷ giữa chừng.
- Gửi thông báo Telegram tổng kết giả định (báo kết quả của phiên trước).

### Nguyên tắc xử lý:
1. `batch_start_time: datetime | None = None` phải được lấy ngay trước lệnh trigger runner (`subprocess.run`).
2. Truyền `batch_start_time` vào cả `apply_results` và `send_telegram_summary`.
3. Lọc thư mục theo mtime:
   ```python
   min_ts = batch_start_time.timestamp() - 10  # đệm 10 giây cho clock skew/file creation delay
   dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
   if not dirs:
       # Bỏ qua xử lý / gửi báo cáo stale
       return False
   ```

## 2. Guard Telegram Summary trong Môi Trường Test
- Trong môi trường `pytest` hoặc unit testing, hàm gửi Telegram summary phải mặc định không gửi ra kênh thật để tránh spam Telegram channel:
  ```python
  if disable_telegram or "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
      return False
  ```
- Hàm phải trả về `bool` (`True` khi thành công/gửi thật, `False` khi bỏ qua do test env hoặc stale data).
- Hỗ trợ thêm cờ `disable_telegram: bool = False` để caller có thể chủ động tắt khi cần kiểm tra logic nội bộ.

## 3. Quy chuẩn Test Kiểm Chứng (Unit & Integration)
1. **Test stale folder filter**:
   - Dùng `tmp_path`, tạo folder giả lập với timestamp quá khứ (`os.utime`).
   - Gọi hàm với `batch_start_time=datetime.now()`, khẳng định hàm lọc bỏ thư mục và trả về `False`.
2. **Test fresh folder picked**:
   - Tạo đồng thời folder cũ và folder mới (mtime hiện tại).
   - Khẳng định thư mục mới được chọn, dữ liệu UID / STT được trích xuất chính xác.
3. **Integration test runner**:
   - Mock `subprocess.run`, `apply_results`, và `send_telegram_summary`.
   - Chạy hàm runner chính (`run_tiktok_reg_for_machines`), kiểm tra `batch_start_time` (kiểu `datetime`) được khởi tạo và truyền đồng bộ vào cả hai khâu apply và telemetry summary.
