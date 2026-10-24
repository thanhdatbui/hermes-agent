# Hook Wiring Parity & Quản Trị Vòng Đời Pre-Tool Guard (Chống Hook Bị Bỏ Rơi)

## 1. Bối Cảnh Thực Tế & Lỗ Hổng "Gate Đã Viết Nhưng Vẫn Bị Lách"
- Khi một Invariant Gate được thiết kế (ví dụ: `guard_cronjob_safety.py` chặn tạo cron job chạy LLM), developer/agent thường chỉ tập trung viết logic kiểm tra và viết test suite (12/12 unit tests pass).
- Tuy nhiên, **Hermes runtime không tự động quét thư mục để load hooks**. Engine chỉ thực thi các hook được khai báo tường minh trong file cấu hình:
  ```yaml
  hooks:
    pre_tool_call:
      - command: python D:/Taadaa/tools/guard_cronjob_safety.py
        matcher: cronjob|terminal
        timeout: 5
  ```
- **Hậu quả của việc thiếu bước Wiring:**
  * Operator đinh ninh: "Hệ thống đã có gate chặn cronjob dùng LLM".
  * Thực tế runtime: Hook chưa được nạp vào chain pre-tool call.
  * Agent ở các session tiếp theo vẫn thoải mái gọi `cronjob(action='create', no_agent=false, prompt="...")` vi phạm luật mà không bị chặn, dẫn tới sự cố nghẽn token 503 ban đêm.

## 2. Quy Chuẩn Đồng Bộ Parity 2 Cấu Hình (Dual-Config Parity)
Mọi hook mới phát triển bắt buộc phải được đăng ký song song vào 2 tệp cấu hình:
1. **Runtime Config:** `%LOCALAPPDATA%\hermes\config.yaml` (hoặc `~/.hermes/config.yaml`). Đây là cấu hình đang được engine Hermes Agent tải vào bộ nhớ để điều khiển các tool call trực tiếp.
2. **Deploy Config:** `D:\Taadaa\Hermes\deploy\hermes-home\config.yaml`. Đây là cấu hình nguồn lưu trữ trong Git repo để phục vụ deploy/sync sang các máy trạm khác.

Bất kỳ sự lệch pha nào (ví dụ: Deploy có 6 hooks, Runtime có 5 hooks) đều phải được cảnh báo và xử lý đồng bộ ngay.

## 3. Danh Mục 9 Pre-Tool Hooks Tiêu Chuẩn Tại Taadaa Farm
1. `guard_read_file_size.py` (`matcher: read_file`): Chặn đọc file quá lớn chống phình context.
2. `guard_broad_grep.py` (`matcher: terminal|search_files`): Chặn quét ổ đĩa diện rộng (`grep -r`, `find`).
3. `guard_device_bulkhead.py` (`matcher: terminal`): Giới hạn can thiệp ADB, bảo vệ máy farm.
4. `guard_dispatch_contract.py` (`matcher: delegate_task`): Ép hợp đồng O(1) & fail-fast khi gọi worker.
5. `guard_closeout_discipline.py` (`matcher: terminal|clarify`): Cấm git push lậu và cấm clarify trốn việc.
6. `guard_cronjob_safety.py` (`matcher: cronjob|terminal`): Bắt buộc `no_agent=true` & ép `CREATE_NO_WINDOW (0x08000000)` ẩn console.
7. `guard_android_proxy.py` (`matcher: terminal`): Bắt buộc IP tĩnh LAN RFC1918 khi gán proxy Android.
8. `guard_pytest_scope.py` (`matcher: terminal`): Buộc chạy focused test, cấm quét cả repo.
9. `guard_model_drift.py` (`matcher: terminal`): Chặn truyền model cấm (sol-pro, sol-instant) vào closeout_gate.

## 4. Quy Trình Wire An Toàn Bằng Tool (Atomic Wiring)
- Cấm sửa thủ công `config.yaml` bằng text editor hoặc regex cẩu thả vì YAML rất nhạy cảm với thụt đầu dòng (indentation).
- Sử dụng tool chuẩn hóa:
  * Gọi hàm nội bộ `_wire_pre_tool_hook(command, matcher, timeout)` trong `manage_hermes_config.py`.
  * Tool tự động tạo bản sao lưu `config.bak.<timestamp>`, ghi qua tệp tạm `.tmp`, gọi `fsync` và `os.replace` để đảm bảo tính nguyên tử (atomic write).
- Sau khi wire, chạy script kiểm chứng đối soát 2 chiều để xác nhận cả Runtime và Deploy đều có cùng số lượng và danh sách hooks.
