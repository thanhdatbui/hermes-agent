# Quy định Vận hành: Dưỡng Sinh (Organic Rest), Nhịp Đăng Video & Cờ Upload (Cập nhật 2026-10-11)

## 1. Cờ Upload & Khung Giờ Đăng Video (User chốt 2026-10-11)
- **Luôn mở `-AllowUploadHook` ở CẢ 2 Phiên:**
  - Phiên 1 (06:00, 12:00, 18:00)
  - Phiên 2 (08:00, 14:00, 20:00)
- **Cơ chế chống đăng trùng:**
  - Hệ thống sử dụng sổ cái `shift_upload_history.json` (`_ShiftUploadLedger`).
  - Nếu Phiên 1 đăng video thành công, Phiên 2 cùng ca tự động phát hiện và bỏ qua (`status: skipped`).
  - Nếu Phiên 1 chưa kịp đăng (do mạng, hàng chờ), Phiên 2 tiếp tục thử đăng bù.

---

## 2. Bỏ Tỷ Lệ Dưỡng Sinh Ngẫu Nhiên (Organic Rest Ratio Disabled)
- **Thay đổi chính thức trong `multi_machine_feed_session.py` (commit `08cc160`):**
  - Đã loại bỏ hoàn toàn cơ chế băm ngẫu nhiên `(int(h[:8], 16) % 3) == 0`.
  - Hàm `_is_account_organic_rest_day` mặc định trả về `False` cho mọi tài khoản.
  - Nick **KHÔNG** còn bị rơi ngẫu nhiên vào ngày nghỉ dưỡng sinh 33% làm chặn oan luồng đăng video hoặc follow.
- **Deep Organic Rest chỉ áp dụng theo sổ cái can thiệp:**
  - `_is_account_organic_rest_day` chỉ trả về `True` khi nick nằm trong `force_rest_ledger` (can thiệp kỹ thuật chủ động).

---

## 3. Nhịp Đăng Video Tự Nhiên & Invariant Farm
- **Cấm chặn upload ngày nghỉ:** Invariant cốt lõi của Taadaa Farm — không dùng cơ chế nghỉ dưỡng nhân tạo để chặn upload của nick.
- **Tự cân bằng nhịp đăng:**
  - Farm chạy luân phiên cách nhật Chẵn / Lẻ (Row 1/3/5/7 ngày lẻ, Row 2/4/6/8 ngày chẵn).
  - Mỗi row tự nhiên có chu kỳ chạy cách nhau 48h (2 ngày / 1 lần).
  - Khi không bị chặn bởi dưỡng sinh ngẫu nhiên, nhịp đăng tự động duy trì chuẩn **2 ngày / 1 video** (hoặc 4 ngày nếu xui xẻo mạng lag/hết kho video).

---

## 4. Chống Bệnh Over-Engineering Khi Thiết Kế Farm Automation
- **Không tự vẽ ra "Quarantine bất tử / Bắt kiểm tra tay khi 0-view":** Video mới tải lên bị 0 view hay ít view là hiện tượng bình thường trên TikTok (do chậm index). Tuyệt đối không chặn đứng lịch đăng hay bắt người vận hành phải duyệt tay thủ công.
- **Không vẽ "Khóa 1 chiều toàn farm":** Các cơ chế lý thuyết suông gây phức tạp hóa hệ thống phải loại bỏ hoàn toàn.
- **Ngân sách Follow khi trưởng thành:** Luôn đọc đúng cấu hình máy (`config/machine*.yaml` — chuẩn farm là 10–20 follow/phiên), không trích dẫn lại comment cũ lỗi thời (6–10).
