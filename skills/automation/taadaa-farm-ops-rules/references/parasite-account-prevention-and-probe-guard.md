# Chống Nick Ký Sinh (Parasite Account Prevention) & Kỷ Luật Probe/Reg

> Phê chuẩn sau sự cố 2026-09-23: Coordinator dùng Máy 201 để test mail `odessostuffen14@hotmail.com`, khi TikTok báo "Bạn đã đăng ký" (thực chất nick `@lethanhlan14` đã được reg thành công trên Máy 22 từ 13:30 trưa nay), Coordinator đã tự ý bấm Tiếp tục và nạp mã OTP từ Graph API vào, khiến nick bị đăng nhập đồng thời lên Máy 201 tạo thành nick ký sinh (parasite account).

---

## 1. NGUYÊN TẮC BẢO VỆ TỐI CAO (HARD INVARIANTS)

1. **KIỂM TRA SOURCE OF TRUTH TRƯỚC TIÊN (CHECK-BEFORE-PROBE):**
   - Trước khi đem bất kỳ email/tài khoản nào đi test reg hoặc probe, **BẮT BUỘC** kiểm tra xem nó đã tồn tại trong file tracking (`taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `tiktok_tracker.db` hoặc `social_reg_log.txt`) chưa.
   - CẤM TUYỆT ĐỐI suy diễn màn hình "Bạn đã đăng ký" là lỗi bên bán mail khi chưa đối soát lịch sử reg của chính Farm.

2. **CẤM BIẾN TOOL REG THÀNH TOOL LOGIN (ANTI-REG-HIJACKING):**
   - Luồng Đăng ký (`social_reg_v1.py`) CHỈ có nhiệm vụ tạo nick mới.
   - Khi TikTok phản hồi:
     - `"Bạn đã đăng ký"`
     - `"You've already registered"`
     - Hoặc xuất hiện màn hình yêu cầu OTP đăng nhập cho tài khoản đã có:
     👉 **BẮT BUỘC DỪNG NGAY (ABORT) & BÁO CÁO KÈM ẢNH CHỨNG MINH.**
     👉 **CẤM TUYỆT ĐỐI** bấm *"Tiếp tục"* hoặc gọi Graph API lấy OTP nạp vào để mở phiên đăng nhập trên tool reg!

3. **RÀNG BUỘC MÁY - TÀI KHOẢN 1:1 (ACCOUNT-MACHINE BINDING GUARD):**
   - Mỗi tài khoản TikTok (ID, email) CHỈ được phép đăng nhập trên đúng STT máy được phân bổ trong file tracking.
   - Hành vi đăng nhập tài khoản của Máy A lên Máy B bị coi là **Vi phạm bảo mật nghiêm trọng (Parasite Account Violation)** vì gây trùng phiên trên 2 thiết bị vật lý / 2 IP khác nhau, dẫn đến checkpoint hàng loạt.

---

## 2. PHÂN BIỆT 3 LUỒNG NGHIỆP VỤ (KHÔNG CHẶN NHẦM)

| Luồng nghiệp vụ | Tool sử dụng | Cơ chế kiểm tra Guard |
|---|---|---|
| **Batch Reg tự động (Pool)** | `social_reg_v1.py <STT>` | **Hard Block 100%**: Nếu mail bốc ra đã thuộc máy khác hoặc đã reg -> Bỏ qua ngay lập tức. |
| **Canary Test (Operator chỉ định)** | `social_reg_v1.py <STT> --email <mail> --ss` | **Warn & Audit Log**: Khi có cờ `--email` đích danh, Guard ghi nhận log cảnh báo và cho phép test, không chặn nhầm canary của User. Gặp "Bạn đã đăng ký" -> Stop & chụp ảnh, cấm tự login. |
| **Re-login nick bị văng** | `tiktok_login_v1.py <STT> --email <ID/mail>` | **Cho phép 100%** nếu target STT trùng với STT máy đã gán của nick đó trong tracking. Re-login đúng máy không bao giờ bị cản trở. |
| **Migration (Chuyển máy do máy cũ hỏng)** | `tiktok_login_v1.py <new_STT> --override-machine` | Yêu cầu cờ `--override-machine` hoặc cập nhật số máy mới trong file Excel tracking trước khi chạy. |

---

## 3. CHECKLIST XỬ LÝ KHI NGHI NGỜ NICK KÝ SINH
Nếu phát hiện một nick bị login nhầm sang máy khác:
1. Mở Profile tab (1001, 1868) $\rightarrow$ Menu hồ sơ 3 gạch (1002, 144) $\rightarrow$ `Cài đặt và quyền riêng tư`.
2. Cuộn xuống đáy trang $\rightarrow$ Bấm nút `Đăng xuất` $\rightarrow$ Xác nhận Đăng xuất tại popup.
3. Chụp ảnh màn hình Switcher xác nhận nick đã biến mất khỏi danh sách tài khoản của máy.
4. Trả máy về Launcher Home an toàn.
