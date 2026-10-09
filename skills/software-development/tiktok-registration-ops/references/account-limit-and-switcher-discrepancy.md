# Account Limit & Switcher Discrepancy (Tiktok_Reg vs Farm Policy)

## 1. Bản chất lệch pha số lượng tài khoản (Audit vs App vs Policy)

Quy định farm: **Mỗi máy tối đa 6 tài khoản TikTok.**
Tuy nhiên thực tế máy có thể tích lũy 7-8 tài khoản trên app do sự lệch pha giữa 3 tầng:

### Tầng 1: Lập lịch Reg (`_detect_clean.py` / `tiktok_target_eligibility.py`)
- Kiểm tra `counts.get(stt, 0) >= max_accounts_per_machine` (mặc định 6).
- **Điểm yếu cốt lõi:** Bộ đếm chỉ đọc số dòng đã có `tiktok_id` theo `STT` trong file tracking `taikhoan_dat_v2_updated .xlsx`.
- Nó **hoàn toàn không kiểm tra thực tế trên app TikTok** của máy qua ADB/ATX.

### Tầng 2: Thực thi Reg (`social_reg_v1.py`)
- Script mở app → Hồ sơ → mở switcher tài khoản (`open_account_dropdown`) → bấm `tap_add_account`.
- **Hoàn toàn không có logic đếm số nick đang có trong switcher.**
- Nếu chạy thủ công `python social_reg_v1.py <stt>` hoặc khi bộ đếm Excel bị hụt, script vẫn tiếp tục bấm thêm tài khoản.

### Tầng 3: Cơ chế của app TikTok trên Android
- TikTok Android cho phép lưu tối đa **8 accounts** cùng lúc trong Account Switcher trước khi ẩn hoặc vô hiệu hóa nút "Thêm tài khoản".
- Do đó, dù máy đã có 6 hay 7 tài khoản, nút "+ Thêm tài khoản" vẫn tồn tại ở đáy menu switcher, cho phép đăng ký/đăng nhập thêm tài khoản thứ 7 và thứ 8 mà không bị app chặn.

---

## 2. Nguyên nhân máy bị dồn > 6 acc và lỗi downstream

1. **Audit Pending đánh dấu `TRACKING_REMOVED_NOT_LIVE`:**
   - Nếu một phiên audit không thấy nick tương ứng trên app (ví dụ do nick bị TikTok đổi sang default username dạng `user<số>` hoặc app bị lỗi hiển thị), audit chuyển nick đó vào pending hoặc loại khỏi đếm tracking.
   - Khi tracking bị giảm số lượng < 6, `_detect_clean.py` nhận định máy này "chưa đủ 6 acc" và tiếp tục cấp thêm email mới cho máy.

2. **Nick mặc định `user...`:**
   - Khi tài khoản mới reg chưa kịp đổi handle hoặc bị TikTok reset, app hiển thị `user11967923709...`.
   - Nick này vẫn nằm trong switcher của TikTok app (chiếm 1 slot), nhưng không khớp với username đã ghi trong workbook.

3. **Hệ quả cho quy trình Lướt Feed / Nuôi Acc (`tiktok-luot nuoi acc`):**
   - Khi runner feed session yêu cầu chuyển sang nick cụ thể (ví dụ `stevemgjqec`), bot mở Account Switcher nhưng chỉ thấy 7 nick khác (gồm cả `user...`), không thấy chuỗi exact mong đợi.
   - Ném blocker: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.

---

## 3. Quy tắc xử lý khi phát hiện máy > 6 acc

1. **Không tự ý reg thêm:** Luôn kiểm tra switcher thực tế trên máy trước khi chạy script reg thủ công.
2. **Đối chiếu nick trên app với tracking:**
   - Đọc danh sách text trong popup Account Switcher.
   - Xác định nick rác / nick `user...` thuộc về email nào trong tracking.
   - Đăng xuất (log out) các tài khoản dư thừa / die ra khỏi app TikTok để đưa máy về đúng chuẩn 6 tài khoản.
