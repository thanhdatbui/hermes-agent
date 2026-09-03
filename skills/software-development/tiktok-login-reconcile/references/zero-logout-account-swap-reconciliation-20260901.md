# Zero-Logout Account Swap & Excel Reconciliation (2026-09-01)

## Bối cảnh & Hiện tượng (Incident Máy 1 & Máy 6)
- Khi chạy phiên nuôi nick đa máy (`multi-machine-feed-session`), Máy 1 dừng phiên báo lỗi:
  `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`
- **Nguyên nhân**: Script tìm nick `janayerton71` (lịch nuôi Slot 5 - Tik5) trong Account Switcher nhưng không thấy.
- **Hiện trường thực tế**: Trên Máy 1 đã đạt giới hạn 6 tài khoản đăng nhập (`tranngan767`, `lipsellczaw`, `duongkien1202`, `ginnyhanstei80`, `ahmetsguthe17`, `buithudung2011`), trong đó `buithudung2011` là nick mới reg ngày 25/08 được lưu ở Slot 7 (Row 8) của Excel.
- Tương tự, trên Máy 6 đã có 6 nick đăng nhập sẵn (`voyen065`, `bch.ngc.ngc91`, `jorgebnstdk`, `thanhlee430`, `llameojyavc`, `alemafxjvxw`), trong đó `alemafxjvxw` là nick reg ngày 26/08 ở Slot 7.

## User Rule & Bài học cốt lõi (2026-09-01)
> *"xàm quá, h máy 1 thiếu nick nào thì lấy nick đó chuyển qua máy khac, sửa excel lại, t thấy hợp lí hơn, vừa tận dụng đc nick trên máy 1 đang có, chứ h log out ra vào nhiều vòng dễ chết hơn ấy"*

**Quy tắc bất biến:**
1. **Tuyệt đối KHÔNG thực hiện logout/login vòng vo trên thiết bị thật** khi máy đã có sẵn nick hợp lệ trong app TikTok. Thao tác logout/login liên tục trên cùng thiết bị dễ kích hoạt security checkpoint của TikTok, làm chết nick hoặc văng session hàng loạt.
2. **Ưu tiên điều chuyển dữ liệu trên Excel (Data-first Swap)** để khớp 100% với hiện trường thực tế của thiết bị:
   - **Đôn nick có sẵn**: Đưa nick đang có sẵn trong app TikTok vào đúng Slot cần nuôi (Slot 5 - Tik5) trên cả 3 bảng master.
   - **Dọn sạch slot cũ**: Xóa thông tin ở slot thừa (Slot 7) về `None` (chú ý gán trực tiếp `cell.value = None` trong openpyxl).
   - **Chuyển nick thiếu sang máy trống**: Gán nick bị thiếu (`janayerton71`) sang một máy khác đang có < 6 nick (ví dụ Máy 61 Slot 5) để quản lý nuôi sau.

## Quy trình 3 bước xử lý chuẩn

### Bước 1: Đối chiếu Account Switcher thật trên thiết bị
- Chụp screencap và đọc XML qua ATX Session (`capture_atx_session_ui`).
- Liệt kê chính xác 6 nick đang đăng nhập trong bottom sheet "Chuyển đổi tài khoản" (`id/pmf`).

### Bước 2: Cập nhật đồng bộ 3 file Excel
1. `taikhoan_dat_v2_updated .xlsx` (Sheet `Tài Khoản`):
   - Cập nhật dòng của máy nguồn: Slot 5 nhận thông tin nick có sẵn; Slot 7 xóa sạch về `None` (giữ nguyên Máy, Folder Video, Device ID).
   - Cập nhật dòng của máy đích: Gán nick bị dời vào Slot trống.
2. `taikhoan_run_safe.xlsx` (Sheet `Accounts`):
   - Cập nhật cột ID cho Máy nguồn và Máy đích khớp với Slot 5.
3. `Tik5.xlsx` (Sheet `TaiKhoan`):
   - Cập nhật cột ID và set `Kiểm Tra Dữ Liệu = OK` cho cả 2 máy.

### Bước 3: Resume phiên nuôi ngay tại chỗ
- Xóa stale device-lock file cũ nếu có trong `~/.codex/device-locks/`.
- Chạy lại lệnh canonical feed runner:
  `python run_tiktok.py --mode multi-machine-feed-session --machines <M> --account-row-index 5 --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --prepare-tiktok --recovery-test-swipes 2`
- Xác nhận `final_status: success` và profile identity khớp đúng nick vừa đôn.
