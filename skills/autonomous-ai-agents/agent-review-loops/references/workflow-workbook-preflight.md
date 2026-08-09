# Workflow workbook và live preflight

## Nguồn dữ liệu

- Mỗi workflow workbook là nguồn độc lập: `Tik1.xlsx`, `Tik2.xlsx`, `Tik3.xlsx`...
- Workbook workflow tự chứa mapping và policy: `Máy`, `device ID`/serial, `ID TikTok`, `Folder Video`, `Keyword Video`, `Hashtag Pool`, `Video Đã Đăng`.
- Chọn dòng đầu tiên của mỗi `Máy`; validate serial nếu CLI truyền `--single-device`.
- Workbook mapping của runner nuôi account (`May/So Seri/ID`) không được trộn làm nguồn tiến độ upload của Tik workbook.
- Không tạo `account_profile` YAML để bù thiếu mapping.

## Preflight Windows

1. Đọc config/entrypoint của sibling đang vận hành để tìm ADB thực tế; không giả định `adb` trong PATH. Một pattern đã xác nhận là `C:\Program Files (x86)\xiaowei\tools\adb.exe`.
2. Kiểm tra `adb devices -l`, rồi `adb -s <serial> get-state` và `getprop ro.product.model`.
3. Đối chiếu cả `machine_<n>.lock.json` và `serial_<serial>.lock.json`.
4. Không xoá lock của process sống đang điều khiển pool/device, kể cả user đã cho phép xoá tuỳ ý; chỉ xoá stale lock sau khi xác minh PID chết hoặc có handoff/stop protocol rõ ràng.
5. Xác minh workbook thật, dòng đầu của target machine, video kế tiếp tồn tại, config runtime ngoài OneDrive và ADB path trước live.
6. Chỉ sau khi preflight pass mới bắt đầu single-device live run; giữ dry-run mặc định và không chạy batch.

## Multi-workbook CLI contract

Ưu tiên `--workflow-workbook`/`workflow_workbook` thay vì hardcode tên Tik1. Nếu dùng `--machine`, resolve serial từ chính workflow workbook. Nếu dùng `--single-device`, yêu cầu serial khớp dòng workbook. Dùng config runtime ngoài repo để thay path, không ghi artifact vào OneDrive.