# Vòng Đời Profile GPM (Lifecycle Sync) & Chuẩn Silent Watchdog

## 1. Nguyên Tắc An Toàn Tối Cao (Safety Invariants)
- **CẤM XÓA PROFILE GPM KHI GMAIL BỊ DIE / BAN / SUSPENDED**:
  + Profile GPM được tạo có thể đã phát sinh chi phí người dùng (nạp tiền thuê SIM verify SĐT, liên kết tài khoản OpenAI / Codex, lưu trữ cookie & active browser session).
  + Việc tự động gọi API `/api/v3/profiles/delete/{id}` khi phát hiện Gmail DIE sẽ gây mất trắng tài khoản, dữ liệu session và lãng phí chi phí thuê số.
  + Chính sách chuẩn: Bỏ qua hoàn toàn việc xóa profile GPM của Gmail DIE. Dọn tài khoản DIE trên thiết bị vật lý (S7) sang danh sách lưu trữ nếu cần, nhưng profile GPM trên PC phải được bảo toàn.

## 2. Chuẩn Silent Watchdog cho Hermes Cronjob (`no_agent: True`)
- **Cơ chế Hermes Scheduler**:
  + Với các job `no_agent: True`, scheduler sẽ chụp toàn bộ `stdout` của script để làm nội dung tin nhắn giao tiếp gửi về người dùng (Telegram).
  + Nếu `stdout` có ký tự bất kỳ $\rightarrow$ Scheduler tự động gửi tin nhắn.
  + Nếu `stdout` rỗng $\rightarrow$ Scheduler im lặng hoàn toàn (Silent Watchdog pattern).
- **Pitfall phát sinh spam**:
  + Khởi tạo logger dùng `StreamHandler(sys.stdout)` khiến các log thông tin thường nhật (`[INFO] Bắt đầu đồng bộ...`, `[INFO] Không có tài khoản DIE...`) bị in ra stdout mỗi tick (15 phút một lần), biến cronjob thành nguồn tin nhắn rác liên tục.
  + **Bẫy Module Con Chiếm Đoạt Root Logger (Submodule Root Logger Hijack)**: Khi script watchdog import module con (ví dụ: `from preflight_s7_rolling_cleanup import remove_account_adb`), nếu module con đó chạy `logging.basicConfig(handlers=[StreamHandler(sys.stdout)])` ở top-level (module level), toàn bộ root logger của tiến trình sẽ bị chuyển hướng ra `sys.stdout`. Mọi thư viện liên quan (`adb_client`, `subprocess`, v.v.) sẽ tuồn toàn bộ log debug/info (`AdbClient initialized...`, `Tiến hành gỡ...`, `đang trong slot feed...`) thẳng ra stdout, làm vỡ hoàn toàn cơ chế Silent Watchdog và nã hàng chục dòng log rác vào Telegram Farm Alert.
- **Quy tắc thiết kế Watchdog Script & Helper Module**:
  1. **Tuyệt đối cấm StreamHandler(sys.stdout) ở top-level thư viện**: Mọi helper/submodule chỉ được cấu hình console logging bên trong khối `if __name__ == "__main__":` khi chạy độc lập, cấm cấu hình ở module level làm ô nhiễm khi import.
  2. **Cách ly stdout/stderr khi gọi module ngoài (Silent Submodule Isolation)**: Trong watchdog runner, trước khi gọi hàm từ module con có nguy cơ log ra stdout, bắt buộc bọc cách ly stdout/stderr hoặc dùng `redirect_stdout` / `redirect_stderr` vào `io.StringIO()` hoặc file tạm để ngăn rò rỉ log.
  3. **Log chi tiết**: Bắt buộc chỉ ghi qua `FileHandler` vào file log chuyên biệt (ví dụ: `logs/sync_gpm_lifecycle.log`) hoặc `sys.stderr`.
  4. **Console Output**: Mặc định KHÔNG add `StreamHandler(sys.stdout)`. Chỉ kích hoạt khi truyền cờ CLI `--verbose` / `-v`.
  5. **Reporting Gate**: Khi không có hành động thực tế nào (`created_count == 0 and cleaned_count == 0`), script thoát với exit code 0 và `stdout` hoàn toàn rỗng (0 bytes).
  6. **Báo cáo sạch**: Chỉ khi có hành động thực tế diễn ra (`created_count > 0` hoặc `cleaned_count > 0`), in đúng 1 dòng tóm tắt định dạng chuẩn:
     ```python
     print(f"[GPM & S7 LIFECYCLE] {' | '.join(parts)}")
     ```

## 3. Quy Trình Đồng Bộ Vòng Đời (Lifecycle Workflow)
- **Tạo Profile Mới (LIVE)**:
  + Quét Master Excel lấy danh sách Gmail `LIVE` chưa có profile trong GPM SQLite DB.
  + Lấy thông tin proxy 4G tương ứng với máy.
  + Gọi GPM Local API tạo profile với tên chuẩn: `{mid:02d} - {email} - {port}`.
  + Bước tạo profile diễn ra độc lập trên PC, không ràng buộc thiết bị S7 phải online ADB.
- **Dọn Dẹp Thiết Bị S7 (DIE)**:
  + Chỉ thực hiện trong khung giờ sáng quy định (07:15 - 08:45 HCMC).
  + Kiểm tra an toàn: Máy không nằm trong slot nuôi TikTok (manifest check) và lấy được Non-blocking Device Lock (`acquire_device_lock`).
  + Gỡ tài khoản DIE khỏi máy S7 an toàn qua ADB và đưa máy về màn hình HOME.
