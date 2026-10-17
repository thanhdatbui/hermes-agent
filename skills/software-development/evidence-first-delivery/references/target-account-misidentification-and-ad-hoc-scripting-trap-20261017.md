# Target Account Misidentification & Ad-Hoc Scripting Trap (2026-10-17)

## 1. Bối Cảnh Sự Cố & Phản Ứng Của User
- **Yêu cầu của User**: Chuẩn hoá kênh `@huy010822` (Máy 18): khóa tên không cho đổi, giữ bio, đổi ghim video (nhả video 1.6K, ghim video 4.3K).
- **Hành vi sai trái của Coordinator**:
  1. Thay vì dùng tool canonical `pin_top_videos.py` (vốn đã có sẵn parser `UNPIN_BUTTON_LABELS`), Coordinator tự ý viết các script ad-hoc vụn vặt (`do_unpin_step1.py`, `do_unpin_step2.py`, `capture_m18.py`) để tap tọa độ mù.
  2. Khi chạy chụp ảnh nghiệm thu, Coordinator không kiểm tra xem app TikTok trên Máy 18 đang đứng ở tài khoản nào. Máy 18 đang nuôi nhiều nick và tài khoản active lúc đó là `@hollybsulliv33` (`Ly Bé`), không phải `@huy010822`.
  3. Coordinator chụp ảnh profile `@hollybsulliv33`, gọi `browser_vision` nhưng không đối soát username đích, sau đó gửi ảnh đính kèm `MEDIA:D:/Taadaa/reports/m18_profile_current.png` và tuyên bố đã ghim xong kênh cho User!
- **Hậu quả**: User nhận được ảnh một tài khoản hoàn toàn khác (`@hollybsulliv33`) và nổi trận lôi đình:
  > *"Bữa có đóng gói tool ghim r, h thêm nhả ghim nx chứ. Mày giỡn mặt tao hả"*
  > *"K những đi đẻ script ngu học, mày còn gửi tao cái kênh khác đéo liên quan kênh t yêu cầu sửa lúc đầu"*

---

## 2. Nguyên Nhân Cốt Lõi (Root Causes)

1. **Vi phạm kỷ luật REUSE > EXTEND > NEW (Bệnh đẻ script bừa bãi)**:
   - Tool `D:/Taadaa/tools/pin_top_videos.py` đã được đóng gói hoàn chỉnh với ATX-agent, Account Switcher integration và parser đầy đủ cho cả `PIN` lẫn `UNPIN`.
   - Khi phát sinh nhu cầu "nhả ghim" (unpin/swap), phản xạ đúng đắn DUY NHẤT là **mở rộng trực tiếp tool canonical** (`pin_top_videos.py`), bổ sung nhánh auto-swap hoặc unpin. Việc viết script con ad-hoc ngoài luồng là hành vi "chữa cháy bẩn", làm rác workspace và vi phạm nghiêm trọng kỷ luật Farm.

2. **Target Account Desync (Mù tài khoản active trên máy đa nick)**:
   - Mỗi máy trên Farm chạy luân phiên 8-10 nick (được quản lý qua `taikhoan_dat_v2_updated .xlsx` và Switcher).
   - Khi nhận lệnh thao tác cho một nick cụ thể (`@huy010822`), Coordinator KHÔNG ĐƯỢC PHÉP mặc định rằng máy đang mở sẵn nick đó.
   - Việc screencap trực tiếp mà không đi qua bước định danh `open_target_profile(serial, account)` dẫn đến việc thao tác và chụp nhầm nick của ca chạy trước.

3. **Thẩm định thị giác hình thức / Mù đối soát Username (Perfunctory Vision Inspection)**:
   - Coordinator có gọi `browser_vision`, nhưng câu hỏi và nhận thức chỉ tập trung vào việc "có thấy các video và huy hiệu ghim không", hoàn toàn bỏ quên bước kiểm tra sống còn: **"Username trên đầu profile có đúng là `@huy010822` không?"**.

---

## 3. Quy Tắc Kỷ Luật Bắt Buộc (Invariants)

### A. Kỷ luật mở rộng Tool Canonical (Anti-Ad-hoc Scripting)
- **CẤM TUYỆT ĐỐI** tự tạo các script con dạng `do_unpin_step*.py`, `temp_pin.py`, `capture_m*.py` khi đã có tool nghiệp vụ chuẩn (`pin_top_videos.py`, `inspect_machine.py`, `run_avatar_batch_3accs.py`).
- Mọi yêu cầu mới liên quan đến ghim/nhả ghim BẮT BUỘC phải tích hợp trực tiếp vào `pin_top_videos.py`:
  - Cơ chế **Auto-Swap Pin**: Khi kênh đã ghim tối đa 3 video, nếu có video chưa ghim đạt view cao hơn video đang ghim có view thấp nhất, tool tự động thực hiện chuỗi hành động: `Unpin video thấp nhất` -> `Pin video mới lên` -> `Verify cả 2 bước`.

### B. Kỷ luật định danh tài khoản bắt buộc (Target Account Assertion Gate)
- Trước khi thực hiện bất kỳ thao tác UI nào (ghim video, đổi avatar, sửa bio, kiểm tra profile), BẮT BUỘC phải assert đúng tài khoản đích:
  ```python
  # Phải verify username trên profile khớp 100% với tài khoản mục tiêu
  assert current_username.lstrip("@").lower() == target_account.lstrip("@").lower()
  ```
- Nếu tài khoản active trên máy khác với target: BẮT BUỘC gọi `automation_core.tiktok.account_switcher` mở Switcher và chuyển đúng sang target account trước khi thao tác tiếp.

### C. Kỷ luật đối soát Username trước khi gửi `MEDIA:` (Username Cross-Check Invariant)
- Trong mọi bức ảnh Profile được gửi kèm thẻ `MEDIA:`, Coordinator BẮT BUỘC phải đọc và xác nhận rõ ràng:
  1. Tên hiển thị và Handle (`@<username>`) trên ảnh CÓ KHỚP VỚI KÊNH MỤC TIÊU CỦA USER HAY KHÔNG.
  2. Nếu phát hiện sai lệch tài khoản (dù chỉ 1 ký tự) ➔ **VETO NGAY LẬP TỨC**, cấm gửi ảnh, cấm tuyên bố hoàn thành.
  3. Lời bình trong tin nhắn trả lời User BẮT BUỘC phải ghi rõ: *"Vision đã đối soát đúng tài khoản `@<username>` trên Máy `<M>`, các thay đổi gồm..."*.
