# Account Switcher Missing Expected Account Diagnosis & Recovery

## Bối cảnh & Hiện tượng
Khi chạy `multi-machine-feed-session` hoặc reconcile, thiết bị dừng phiên kèm alert:
`Lý do: account switcher requires manual review` (hoặc `account-switcher-missing-expected`).

## Nguyên nhân
1. Script cần chạy tài khoản ở Slot X (ví dụ Slot 2: `laquyen2601`), mở bảng "Chuyển đổi tài khoản" (Account Switcher modal).
2. App TikTok trên thiết bị chỉ đang đăng nhập một tài khoản khác (ví dụ Slot 3: `djricnvy2ez`) và không có tài khoản Slot X trong danh sách.
3. Script dừng phiên an toàn theo quy định để giữ hiện trường, tránh thao tác sai làm checkpoint nick.

## Quy trình chẩn đoán chuẩn
1. **Map serial chuẩn xác**:
   - Tra cứu số máy $N$ trong `D:\Taadaa\runtime\kibe\device_mapping.json` để lấy serial thiết bị.
   - Tuyệt đối CẤM quét đệ quy `find`/`grep` trong `.ai-runs/runtime` làm timeout session.
2. **Kiểm tra hiện trường thực tế**:
   - Chụp screencap và dump UI XML để xác nhận nick nào đang thực sự active trên màn hình.
3. **Đối chiếu danh sách Slot**:
   - Mở `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` kiểm tra 6 Slot của máy.
   - Kiểm tra xem nick đang active trên máy thuộc Slot nào và nick cần chạy đang ở trạng thái nào (live/die).

## Hướng xử lý
- **Phương án 1 (Login bổ sung)**: Nếu máy còn chỗ (< 6 nick) và cần chạy đúng nick Slot X, thực hiện login tự động bằng pass và 2FA từ `taikhoan_dat_v2_updated .xlsx`.
- **Phương án 2 (Chạy Slot có sẵn)**: Nếu nick active trên máy hợp lệ (ví dụ Slot 3), có thể chỉ định chạy phiên cho Slot 3 qua `--account-row-index 3`.
- **Phương án 3 (Zero-Logout Account Swap)**: Nếu máy đã đủ 6 nick từ đợt reg trước nhưng lệch thứ tự Slot, thực hiện đôn nick trên Excel theo tài liệu `references/zero-logout-account-swap-reconciliation-20260901.md`.
