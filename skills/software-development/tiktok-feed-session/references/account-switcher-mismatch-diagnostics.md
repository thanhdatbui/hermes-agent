# Account Switcher Mismatch Diagnostics & Edge Pitfalls (Feed Session Smoke)

## 1. Bản Chất Lỗi "profile username still mismatched after switch"
Trong quy trình chạy `feed-session-smoke` (đặc biệt khi chuyển sang các ca sau như Ca 2 Row 8), runner thường xuyên gặp lỗi `profile username still mismatched after switch (expected='...', found='...')`.

Hiện tượng thực tế:
- Tài khoản kỳ vọng **đã đăng nhập sẵn** và hiển thị trong danh sách Bottom Sheet của Account Switcher TikTok.
- Runner nhận diện đúng node tài khoản, phát lệnh `input tap` vào tâm button của hàng tài khoản (`tap_expected_account`).
- Tuy nhiên, sau đó bước xác minh `profile_preflight_verify` vẫn phát hiện TikTok đang ở tài khoản của Ca trước (thường là Slot 7).

---

## 2. Bốn Căn Nguyên Kỹ Thuật Gốc Rễ (Root Causes)

### A. Kẹt Viền Mép Đáy Màn Hình (Bottom-Edge Clipping - Slot 8)
- Trên các thiết bị Samsung S7 (độ phân giải 1080x1920), bảng Account Switcher chứa 8 tài khoản có chiều cao mỗi hàng ~216px.
- Tài khoản thứ 8 (Slot 8) có bounds thường là `[0, 1788][1080, 1920]`. Tọa độ tâm tính toán: `x = 540, y = 1854`.
- **Cạm bẫy**: Tọa độ `y = 1854` nằm sát đáy màn hình (vùng viền ảo / navigation bar / touch exclusion margin), khiến lệnh tap qua `input tap` dễ bị hệ điều hành nuốt chửng hoặc không kích hoạt sự kiện click của hàng tài khoản nếu danh sách chưa được scroll nhẹ lên trên.

### B. Cạm Bẫy `KEYCODE_BACK` Hủy Switch Trong `_navigate_profile_for_preflight`
- Sau khi phát lệnh `tap_expected_account`, TikTok cần từ 2-5 giây để tải phiên đăng nhập và đóng Switcher Sheet.
- Nếu TikTok có độ trễ mạng hoặc Switcher chưa kịp biến mất, lệnh `_navigate_profile_for_preflight` chạy ngay sau đó sẽ quét tìm tab bottom nav "Hồ sơ" (`_profile_target()`).
- Do Switcher Sheet vẫn đang phủ lên giao diện, tab "Hồ sơ" không tồn tại trong XML dump.
- **Hệ quả dây chuyền**:
  1. `tap_navigation_target` kích hoạt cơ chế tự cứu: `action="navigation_target_not_found_back_recovery_1"`.
  2. Runner gửi `input keyevent 4` (KEYCODE_BACK) liên tiếp 1 - 2 lần.
  3. Phím BACK đóng lập tức Switcher Sheet và **hủy quá trình chuyển đổi session**, đưa ứng dụng trở lại Profile của tài khoản cũ.
  4. Sau đó runner mới tìm thấy tab "Hồ sơ", tap vào và đọc thấy username cũ, dẫn đến mismatch.

### C. False Positive Trong `tiktok_login_v1.py` (`auto_login_recovery`)
- Khi mismatch xảy ra 3 lần, runner gọi fallback `auto_login_recovery` qua lệnh:
  `python D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py <machine> --email <id> --ss --allow-parent-lock`
- Trong `tiktok_login_v1.py`:
  ```python
  if target_id in switcher:
      tap(device_id, *_coord, wait=D_LONG)
      time.sleep(D_LONG)
      return "already_logged_in"  # EXIT 0 NGAY LẬP TỨC!
  ```
- **Cạm bẫy**: `tiktok_login_v1.py` chỉ tap tọa độ rồi trả về `already_logged_in` (exit code 0) mà **hoàn toàn không verify lại UI Profile**. Runner mẹ nhận exit code 0 tưởng đã phục hồi thành công, thử lại và tiếp tục fail mismatch.

### D. Lệch Thứ Tự Slot Giữa `taikhoan_run_safe.xlsx` và `TikN.xlsx` (Row Drift)
- `Tik1.xlsx` .. `Tik8.xlsx` được map theo công thức chuẩn: `F_src = (Slot - 1) * 80 + m_idx`.
- File `taikhoan_run_safe.xlsx` được sinh từ `taikhoan_dat_v2_updated .xlsx`. Nếu các dòng của máy trong Master DAT không được sắp xếp theo đúng thứ tự Folder (ví dụ như trường hợp M76 bị đảo giữa Folder 602 và 608), Slot 8 trong file safe sẽ trỏ sang nick khác với file `Tik8.xlsx`.
- Runner đọc file safe sẽ đòi hỏi nick sai so với thực tế máy đang chạy, gây ra lỗi mismatch giả định.

---

## 3. Quy Trình Kiểm Chứng & Khắc Phục Chuẩn (Standard Triage Protocol)

1. **Trích xuất O(1) kiểm tra Switcher & Profile XML**:
   - Kiểm tra `artifacts/.../feed-session-smoke/profile_preflight_switcher_1_guard/attempt_1/ui.xml` để xác nhận tài khoản đích có nằm trong switcher không và bounds là bao nhiêu.
   - So sánh với `profile_preflight_verify_*/attempt_1/ui.xml` để xem handle thực tế đang dừng ở đâu.
2. **Khắc phục xử lý Switch Sheet**:
   - Nếu slot cần bấm có `bounds[3] >= 1780`: Phải thực hiện scroll nhẹ sheet lên trên (ví dụ swipe từ `(540, 1500)` lên `(540, 1100)`) trước khi lấy tọa độ tap.
   - Sau khi tap tài khoản, phải poll kiểm tra node `Chuyển đổi tài khoản` / Switcher Sheet đã biến mất khỏi màn hình trước khi gọi điều hướng về Profile, cấm gửi `KEYCODE_BACK` khi chưa xác định sheet đã đóng.
3. **Nghiệm thu sau `tiktok_login_v1.py`**:
   - Trong `tiktok_login_v1.py`, sau khi tap switcher row, bắt buộc dump XML Profile hoặc gọi `ensure_profile_completed_and_track` để đối soát handle thực tế khớp với target mới được return `already_logged_in`.
