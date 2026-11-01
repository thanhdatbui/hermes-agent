# Anti-Reinventing ADB Automation, Pipeline Expansion & Anti-Whining Discipline (2026-11-01)

## 1. Bối cảnh & Hiện Tượng "Chế Lại Bánh Xe" (Reinventing The Wheel)
- **Hành vi sai lầm:** Khi cần chạy luồng thử nghiệm hoặc chức năng mới (như TikTok Lite), Agent tự dùng tool `write_file` tạo các script Python rời rạc ngoài luồng (`tiktok_lite_enter_email.py`, `tiktok_lite_canary_flow.py`) để gọi `adb shell input tap/swipe/text/keyevent` thủ công.
- **Hậu quả:**
  1. Phân mảnh logic điều khiển thiết bị trên farm.
  2. Bỏ qua các kỹ thuật chống phát hiện bot tinh vi đã được đúc kết trong canonical codebase `TikTok_Reg` (ví dụ: bẫy bấm Login chân trang trước khi Sign Up, xử lý keyboard tutorial, popup One-tap, v.v.).
  3. Gây lỗi Instant-Ban tài khoản hàng loạt và làm bẩn working tree.

---

## 2. Cơ Chế Chốt Chặn Cơ Học O(1) Tại Hook Boundary (`hooks/guard_broad_grep.py`)
Để triệt tiêu tận gốc việc tự chế script ADB mà không gây chậm hệ thống hay làm nghẽn các tác vụ hợp lệ, hệ thống thiết lập 2 tầng lọc tĩnh:

### Tầng 1: Fast-Pass Whitelist O(1) (<0.001s)
- Các đường dẫn thuộc: `tests/`, `reports/`, `logs/`, `config/`, hoặc tên file `test_*.py`, `*_test.py` ➔ **Cho qua ngay lập tức vô điều kiện**.
- Không kiểm tra các file phi thực thi (.txt, .json, .md).

### Tầng 2: Anti-Reinventing Intent Matcher & Actionable Redirect
- Quét các file script executable (`.py`, `.ps1`, `.bat`, `.sh`) nằm ngoài whitelist.
- Nếu chứa pattern gọi ADB input automation (`adb shell input tap|swipe|text|keyevent` hoặc `subprocess/os.system` gọi adb input):
  - **Chặn đứng ngay lập tức (`STATUS: BLOCK / GUARD_REINVENT_AUTOMATION_WHEEL`)**.
  - **BẮT BUỘC trả về Actionable Command (chỉ rõ canonical tool có sẵn để chạy)**:
    - Reg TikTok: `python D:/Taadaa/TikTok_Reg/tiktok_reg_live_email_v1.py <STT> --email <mail>`
    - Login TikTok: `python D:/Taadaa/TikTok_Reg/tiktok_login_v1.py <STT>`
    - Logout TikTok: `python D:/Taadaa/tools/do_logout_account.py <STT> <user> <serial>`
    - Soi máy farm: `python D:/Taadaa/tools/inspect_machine.py <N>`
  - Triệt tiêu bẫy Veto cộc lốc: Agent nhận được command có sẵn thì copy chạy tiếp ngay, không bị loay hoay hay rơi vào bẫy bại liệt.

---

## 3. Mở Rộng `unified_patch_pipeline.py` & `gate_b_planner.py` Cho Script Mới
- **Vấn đề cũ:** Pipeline trước đây bắt buộc `p.is_file()` tại S0 Precheck, khiến việc tạo script mới hợp lệ bị lỗi `Target file does not exist`, ép Agent phải dùng `write_file` chui ngoài luồng.
- **Giải pháp chuẩn hóa:**
  - `unified_patch_pipeline.py`: Cho phép target file chưa tồn tại trên đĩa (chỉ cần nằm trong repo, không path traversal).
  - `gate_b_planner.py`: Hỗ trợ tạo file mới với contract `old_string = ""` và `new_string = <nội dung script>`.
  - **Nguyên tắc:** Muốn tạo script mới BẮT BUỘC đi qua pipeline liên hoàn để được giám sát scope, chạy test và nghiệm thu Canary có ảnh đầy đủ.

---

## 4. Kỷ Luật Ứng Xử: Chống Khóc Lóc (Anti-Whining Invariant)
- **CẤM TUYỆT ĐỐI văn mẫu xin lỗi phòng thủ:**
  - Khi bị Guard chặn hoặc phát hiện lỗi sai, cấm dùng các câu chữ ẻo lả: *"Em nhận lỗi sâu sắc trước...", "Em chủ quan...", "Em thật sự xin lỗi sếp..."*.
  - Lời phân trần/xin lỗi bằng lời nói bị coi là biểu hiện của sự thoái thác và né tránh trách nhiệm.
- **Quy tắc Action-First:**
  - Nhận thấy sai ➔ Lẳng lặng đè code/lệnh ra sửa dứt điểm.
  - Phản hồi báo cáo ngắn gọn, bám sát sự thật khách quan và bằng chứng thực tế (log, OCR, media), không dông dài.
