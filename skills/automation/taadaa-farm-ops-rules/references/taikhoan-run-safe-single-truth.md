# Quy Tắc Bất Di Bất Dịch: `taikhoan_run_safe.xlsx` Là Nguồn Chân Lý Duy Nhất & CẤM Tự Chế Xoá Cache/Manifest Runtime

## 1. Nguồn Chân Lý Duy Nhất Của Farm (Single Source of Truth)
- Toàn bộ hoạt động nuôi feed / upload / follow trên farm chạy theo file **`D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`** (`Accounts` sheet).
- Khi chạy trực tiếp hoặc ép chạy: script đọc thẳng số máy (`machine 1..80`) và hàng tài khoản (`account_row_index 1..6`) từ file Excel này để thực thi trên thiết bị thật.
- **CẤM** over-engineer thêm các tầng trung gian phức tạp, state machine tự chế hoặc logic kiểm tra chéo digest/manifest/cohort làm cản trở hoặc làm sập luồng chạy trực tiếp từ Excel.

## 2. CẤM Tự Ý `shutil.rmtree` Xoá Cache/Manifest/Cohort Trong Runtime Cron
- **Hiện tượng lỗi (Anti-Pattern):**
  - Script cron 5 phút (`hermes_taikhoan_sync_cron.py`) khi phát hiện file Excel thay đổi đã tự ý gọi `shutil.rmtree` xoá sạch thư mục `manifests/YYYY-MM-DD`, `snapshot_bundles/`, `cohorts/` trong khi farm đang chạy dở một ca nuôi kéo dài 30-45 phút.
  - Hậu quả: Khi các máy tiếp theo trong đợt chạy đối soát manifest/cohort đã nạp lúc khởi động với manifest mới tái tạo trên đĩa, hash SHA-256 bị lệch hoàn toàn ➔ Kích hoạt exception `cohort artifact assignment digest mismatch` / `MANIFEST_IDENTITY_MISMATCH` làm sập chùm toàn bộ 80 máy và giam lock hiện trường.
- **Quy tắc chuẩn:**
  1. Cron sync Excel (`hermes_taikhoan_sync_cron.py`) **CHỈ ĐƯỢC PHÉP** đồng bộ dữ liệu vào `taikhoan_run_safe.xlsx`. Tuyệt đối không xoá đè/tái tạo manifest ngầm khi farm đang vận hành.
  2. Không bao giờ can thiệp xoá file trong `runtime/.../manifests/` hoặc `cohorts/` giữa ngày nếu không có lệnh kiểm soát phiên rõ ràng.
