# Bảo Toàn Profile GPM & Quản Lý Sổ Cái Gmail DIE

## 1. Nguyên Tắc An Toàn Tối Cao (Invariant)
- **CẤM TUYỆT ĐỐI xoá Profile GPM khi Gmail bị DIE / BAN / SUSPENDED**:
  - Profile GPM chứa session đăng nhập, cookie, token và tài khoản OpenAI / ChatGPT / Codex đã được nạp tiền thuê SIM số điện thoại (5sim / SMS OTP) để verify.
  - Khi Gmail bị Google vô hiệu hoá, tài khoản OpenAI/ChatGPT tạo bằng Email + Pass vẫn đăng nhập và sử dụng bình thường. Xoá profile GPM sẽ làm mất trắng tài sản này.
  - Trong `scripts/sync_gpm_lifecycle.py` (cả repo và runtime cronjob), logic gọi API `profiles/delete/{pid}?mode=2` đối với Gmail DIE đã bị vô hiệu hoá hoàn toàn (`deleted_count = 0`).

## 2. Sổ Cái Quản Lý Gmail DIE (`master_gmail_manager.xlsx`)
- **Tách biệt hoàn toàn tài khoản LIVE và DIE**:
  - Các sheet hoạt động thường (`Master_All`, `Gmail_Dat`, `Kibe_Farm_S7`, `Admin_GPM_Pool`) CHỈ chứa 100% tài khoản `LIVE`. Toàn bộ các dòng DIE đã được dọn sạch để máy farm và batch script không login nhầm.
  - Tạo sheet chuyên biệt **`Gmail_DIE_Archive`** lưu trữ toàn bộ tài khoản DIE.
- **Bảo tồn toàn bộ 16 cột thông tin**:
  - `STT`, `Email`, `Password`, `Recovery_Email`, `2FA_Secret`, `SDT` (SĐT đã thuê SIM ver), `Trạng Thái` (DIE), `ChatGPT_Reg` (trạng thái reg ChatGPT/Codex), `Số Máy Farm`, `Model Điện Thoại`, `Serial Thiết Bị`, `Proxy Đang Dùng`, `Tên Profile GPM`, `Nguồn`, `Ghi Chú`, `Cập Nhật`.
- **Khả năng phục hồi tài khoản (Rescue)**:
  - Rất nhiều Gmail DIE (như kho Gmail Đạt) thực chất là checkpoint verify SMS. Vì cột `SDT` đã lưu chính xác số điện thoại cũ từng verify, có thể dùng lại số đó hoặc luồng recovery để mở lại tài khoản sống bình thường.
