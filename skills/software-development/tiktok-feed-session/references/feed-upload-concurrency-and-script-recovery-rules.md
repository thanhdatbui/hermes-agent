# Feed vs Upload Concurrency, Script Recovery, and Workbook Hygiene Rules

## 1. Cấm chạy Batch Upload đè lên nhịp Feed Session đang chạy dở
- **Hiện tượng:** Khi Feed Session đang ở nhịp chạy vét cuối phiên (hoặc sau 00:00), nếu vội vàng kích hoạt batch upload video (`run_tiktok_upload_batch.ps1`) song song, cả 2 tiến trình sẽ cùng tranh chấp mở app TikTok, gây lỗi văng app ra ngoài Launcher (`TikTok focus lost`), kẹt màn hình Camera/Picker (`navigation target home not found in XML`), và kích hoạt Farm Alert đỏ.
- **Quy tắc:** Bắt buộc đợi toàn bộ các worker của Feed Session kết thúc và dọn dẹp sạch sẽ trạng thái thiết bị (`pkill uiautomator`, restart `atx-agent`) trước khi kích hoạt batch upload.

## 2. Quy tắc Xử lý Lỗi Bằng Code / Script Engine (Cấm Workaround Tạm Bợ)
- **Quy tắc:** Khi có yêu cầu fix lỗi các máy chạy thất bại, toàn bộ logic sửa đổi phải được update trực tiếp vào codebase, review APPROVED qua model reviewer và commit/push Git.
- **Thực thi Recovery:** Chạy lại bằng runner chính thức với các cờ recovery chuẩn (`-RecoveryMode -AllowDeviceRebootRecovery`) để engine tự động xử lý popup, giải phóng giao diện kẹt, và đối soát bằng chứng UI. Tuyệt đối không can thiệp sửa tay file Excel khi chưa có bằng chứng hiển thị trên Profile Grid (`post_verified: True`).

## 3. Báo cáo Số liệu Upload Video Rõ Ràng (Mới vs Lũy kế)
- Tránh gây hiểu nhầm cho user giữa 2 chỉ số:
  1. **Số máy đăng MỚI thành công trong ca/đợt hiện tại:** Số lượng máy vừa thực hiện flow đăng video tiếp theo và tăng số thứ tự video thành công.
  2. **Tổng số máy ĐANG CÓ VIDEO (>0 video) lũy kế trên sheet:** Tổng toàn bộ các máy đã có video từ trước đến nay (bao gồm cả các máy đã đăng hôm nay và các máy giữ số video cũ do chưa đăng thêm được).

## 4. Xử lý Tài khoản Rác / Không Đủ Thông tin trên Workbook TikN
- Khi audit phát hiện tài khoản trên `TikN.xlsx` mang username rác (ví dụ: chuỗi ký tự gõ phím ngẫu nhiên, link URL thay vì username chuẩn) và không có thông tin đăng nhập hợp lệ:
  - Tiến hành xóa trắng ô `ID TikTok` của máy đó trong workbook `TikN.xlsx` (đưa về `None`/trống).
  - Để máy ở trạng thái trống nick, chờ chuỗi Reg ban đêm (`night-chain-reg-gmail-tiktok`) cấp tài khoản mới sau.
  - Bỏ qua các máy ADB Offline trong các đợt recovery đăng video.
