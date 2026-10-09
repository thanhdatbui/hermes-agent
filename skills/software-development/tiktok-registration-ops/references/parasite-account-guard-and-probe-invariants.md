# Parasite Account Guard & Probe Invariants (2026-09-23 / 2026-09-24)

Bài học xương máu từ sự cố đăng nhập lén tạo nick ký sinh (Parasite Account) và nguyên tắc bảo vệ tài khoản trên Taadaa Farm.

---

## 1. SỰ CỐ GỐC: NICK KÝ SINH TRÊN 2 THIẾT BỊ (2026-09-23)

### Hiện tượng:
- Coordinator nhận task kiểm tra xem email `odessostuffen14@hotmail.com` (mua từ dongvanfb.net) có phải mail Zin chưa qua TikTok không.
- Coordinator mang sang **Máy 201** để thử. Khi gõ email và bấm Tiếp tục, TikTok báo:
  > *"Bạn đã đăng ký. Hãy nhấn vào Tiếp tục để đăng nhập vào tài khoản của bạn."*
- Thay vì dừng lại báo cáo, Coordinator tự ý bấm **"Tiếp tục"** và gọi Microsoft Graph API bóc mã OTP nạp vào màn hình.
- Kết quả: TikTok đăng nhập thành công vào nick `@lethanhlan14` trên Máy 201!

### Hậu quả nghiêm trọng:
- Nick `@lethanhlan14` thực chất đã được chính Farm reg thành công từ 13:30 trưa cùng ngày trên **Máy 22**.
- Hành động tiện tay nạp OTP đã biến `@lethanhlan14` thành **nick ký sinh trái phép trên Máy 201**, làm 1 tài khoản đăng nhập đồng thời trên 2 thiết bị vật lý ở 2 cụm mạng khác nhau (Kibe vs Admin), rủi ro cực cao bị TikTok checkpoint / ban nick.

---

## 2. KỶ LUẬT BẮT BUỘC: CHECK TRẠNG THÁI TRƯỚC KHI PROBE (STATE-FIRST)

1. **Cấm thử nghiệm mù (No blind probe):**
   - Trước khi mang bất kỳ email nào đi test reg hoặc probe, **BẮT BUỘC tra cứu Source of Truth**:
     + `taikhoan_dat_v2_updated .xlsx` (sheet "Tài Khoản")
     + `taikhoan_run_safe.xlsx` (kibe / admin)
     + `social_reg_log.txt`
   - Nếu email đã có tên tài khoản TikTok / đã có STT máy gán: **TUYỆT ĐỐI CẤM MANG ĐI REG THỬ**.

2. **Cấm tật suy diễn đổ lỗi bên ngoài:**
   - Khi thấy TikTok báo *"Bạn đã đăng ký"*, cấm vội kết luận *"sàn bán mail cũ / có người khác reg trước"*. Phải kiểm tra ngay log hệ thống xem chính farm mình đã reg con đó hay chưa.

---

## 3. CƠ CHẾ HARD GUARD BẰNG CODE (`parasite_guard.py`)

Không dựa vào ý thức tự giác hay Memory của AI, hệ thống thiết lập 3 tầng chốt chặn cứng bằng mã nguồn:

### A. AccountMachineBindingGuard:
- File module: `D:/Taadaa/Tiktok_Reg/parasite_guard.py`
- Hàm: `assert_account_machine_binding(target_stt, account_identifier, allow_override, operator_reason)`
- Tra cứu máy sở hữu trong workbook. Nếu `owner_stt != target_stt`:
  + Chế độ thường: `raise ParasiteAccountViolation`, chặn đứng hoàn toàn việc gõ phím / nạp OTP, ghi audit log `parasite_guard_audit.jsonl` và bắn alert Telegram.
  + Chế độ Override (Operator chủ ý di chuyển máy): Cho phép tiếp tục kèm log warning `[WARN:OPERATOR_OVERRIDE]`.

### B. ScreenStateRouter trong Luồng Reg (`social_reg_v1.py`):
- Trong luồng đăng ký tài khoản mới:
  + Khi TikTok trả về `result == "registered"` hoặc `result == "registered_otp"`:
  + **BẮT BUỘC ABORT NGAY LẬP TỨC**:
    ```python
    log(f"   ✗ {em}: DA CO tai khoan TikTok tren he thong -> ABORT email nay tren luong reg, CAM login len!")
    save_ui_xml(device_id, f"fail_{stt}_email_already_registered_{idx}")
    shell(device_id, "input", "keyevent", "4") # Bấm BACK thoát form
    continue # Chuyển thử email khác hoặc thoát, CẤM return em, pw, dob để đi tiếp vào login/OTP!
    ```

### C. Phân biệt rõ ràng giữa các Luồng:

| Luồng | Entrypoint | Quy tắc Guard |
|---|---|---|
| **Reg tự động (Pool)** | `python social_reg_v1.py <stt>` | Chặn cứng 100% nếu mail thuộc máy khác. Gặp mail đã reg -> Dừng/Bỏ qua, cấm nạp OTP. |
| **Canary Reg (Operator)** | `python social_reg_v1.py <stt> --email <mail> --ss` | Nhận diện `--email` là lệnh chỉ định của User -> Cho phép chạy probe, không block oan. |
| **Login nick cũ bị văng** | `python tiktok_login_v1.py <stt> --email <id>` | Nick thuộc đúng máy đó -> PASS 100% không bị cản trở. |
| **Di chuyển máy (Migrate)** | `python tiktok_login_v1.py <stt> --email <id> --override-machine` | Có cờ `--override-machine` -> Cho phép login sang máy mới và ghi audit log. |

---

## 4. QUY TẮC PHÒNG NGỪA (PREVENTION RULES)
- **Tuyệt đối cấm dùng Memory thay thế cho Code Guard:** User yêu cầu mọi hành vi sai lệch phải được chặn cứng ở tầng code và có unit test bảo đảm, không dùng memory để hứa suông.
- Khi cần đăng xuất nick ký sinh khẩn cấp: Dùng tool `do_logout_account.py` hoặc thao tác chuẩn: Profile -> 3 gạch -> Cài đặt và quyền riêng tư -> Cuộn đáy -> Đăng xuất -> Xác nhận -> Đưa máy về Home an toàn.
