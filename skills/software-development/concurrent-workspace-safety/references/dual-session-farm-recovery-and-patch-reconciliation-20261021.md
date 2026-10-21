# Dual-Session Farm Alert Recovery & Patch Reconciliation (2026-10-21)

## 1. Bối Cảnh & Hiện Tượng Xảy Ra Dual-Session
Trong hệ thống điều phối đa kênh (Telegram topics / đa phiên song song):
- **Cùng một gốc sự cố được phân phối qua 2 kênh/alert khác nhau:**
  * Kênh 1: Cảnh báo khẩn cấp tức thời `🚨 [BATCH ALERT: LỖI HỆ THỐNG]` nhắm vào lỗi cá biệt P0 (Máy 24 kẹt Account Switcher). Kích hoạt Session 1 lúc 09:35.
  * Kênh 2: Báo cáo tổng kết ca từ cronjob `tiktok-feed-session-watchdog` (báo danh sách các máy fail toàn batch: M10, M24, M26, M30, M65, M74, M80). Kích hoạt Session 2 lúc 09:42 khi người dùng yêu cầu sửa lỗi.
- **Hậu quả vận hành:**
  * Cả hai Coordinator trong 2 session độc lập cùng nhận diện Máy 24 là đối tượng duy nhất bị lỗi logic, dẫn đến việc cả 2 cùng can thiệp vào máy thật `ce0117112b2a0e3a04` và cùng thực hiện Emergency Surgery trên repo `D:/Taadaa/Tiktok_Reg`.

---

## 2. Các Dấu Hiệu Nhận Biết Va Chạm Đa Phiên (Dual-Session Collision Signals)
1. **Va chạm Device Lock:**
   * Script đăng nhập hoặc đổi tên văng thông báo:
     `[device-lock] NEEDS_USER_DECISION: device lock active: path=...machine_24.lock.json pid=<PID> ... command=...`
   * Kiểm tra PID thấy tiến trình đang chạy thuộc về một lệnh được kích hoạt từ session khác.
2. **Thông báo tiến trình nền lạ (`proc_*`):**
   * Coordinator nhận được thông báo hoàn tất hoặc thoát của các tiến trình mà lượt trò chuyện hiện tại không theo dõi hoặc đã chạy ở lượt trước đó do cùng chia sẻ harness nền.
3. **Lịch sử Git xuất hiện các commit song song:**
   * `git log origin/main..HEAD --oneline` hiển thị nhiều commit `[L2-surgery]` được tạo ra cách nhau chỉ vài phút trên cùng một nhánh làm việc.

---

## 3. Quy Trình Đối Soát & Kiểm Chứng Không Xung Đột (Reconciliation & Non-Conflict Verification)

Khi phát hiện có 2 session cùng sửa code trên một repo để xử lý cùng 1 lỗi, Coordinator BẮT BUỘC thực hiện kiểm tra 4 tầng theo thứ tự sau:

### Tầng 1: Phân Rã & Phân Loại Hunk (Hunk Ownership & Scope Mapping)
Chạy lệnh kiểm tra tổng thể diff từ base gốc:
```bash
git diff origin/main..HEAD -w
```
Lập bảng đối soát mọi hàm và vị trí bị sửa đổi giữa 2 bên:
- **Disjoint / Orthogonal (Độc lập):** Sửa các hàm khác nhau trong cùng 1 file (ví dụ: Session 1 sửa `_tiktok_login_modal_present`, Session 2 sửa `_profile_tab_node`).
- **Complementary (Bổ trợ khép kín):** Sửa các mắt xích kế tiếp nhau trong flow (ví dụ: Session 1 sửa nút tap switcher mép đáy, Session 2 bổ sung đệm chờ xác thực mật khẩu qua proxy và tăng timeout chờ login thành công).
- **Identical (Trùng khớp):** Cùng sửa một logic giống hệt nhau (ví dụ: cùng clamp `safe_y <= 1835`).
- **Conflicting (Xung đột):** Sửa đè lên cùng một dòng hoặc thay đổi signature/kiểu trả về khiến luồng gọi của bên kia bị gãy.

### Tầng 2: Kiểm Chứng Cú Pháp & Biên Dịch Sạch
```bash
python -m py_compile social_reg_v1.py tiktok_login_v1.py
```
Đảm bảo mã nguồn hợp nhất không có lỗi cú pháp, thụt dòng (indentation) hay biến chưa được định nghĩa.

### Tầng 3: Unit Test Hàm Thuần Túy (Pure Function Mock Test)
Tạo script kiểm tra nhanh các hàm vừa được vá với các mẫu XML giả lập:
```python
# Kiểm tra bộ lọc loại trừ Settings không bị ngộ nhận là Login modal
assert not _tiktok_login_modal_present(xml_settings)
# Kiểm tra bộ lọc tab Hồ sơ không bị nhận nhầm đĩa nhạc video feed
node = _profile_tab_node(xml_tabs)
assert node['coord'] == (972, 1857)
```

### Tầng 4: Kiểm Chứng Canary Thực Tế Trên Thiết Bị Thật
Chạy trực tiếp 1 phiên canary test ngắn (ví dụ: 2 swipes) trên đúng máy xảy ra sự cố:
- Xác nhận thiết bị chuyển tài khoản thành công mà không bị kẹt hay văng exception.
- Soi mắt kiểm tra ảnh chụp màn hình in-app thực tế qua vision để xác nhận giao diện sạch và không còn popup cản trở.

---

## 4. Bài Học Điều Phối Chống Trùng Lặp Lãng Phí (Lessons Learned)
1. **Phòng ngừa:** Khi nhận thông báo batch alert hoặc cronjob report, Coordinator cần chạy `session_search(query='<machine_id_or_script>', sort='newest')` để xác định xem đang có session nào khác xử lý máy đó không trước khi spawn tiến trình mới.
2. **Nếu đã xảy ra:** Không vội vàng revert hay reset working tree làm hỏng checkpoint của session kia. Hãy bình tĩnh phân loại diff, hợp nhất các điểm bổ trợ tốt nhất của cả 2 bên và kiểm chứng bằng test/canary thực tế.

---

## 5. Sự Cố Sibling Session Chạy 'git checkout' Xóa Sạch Uncommitted Code (Incident 2026-10-21)
- **Hiện tượng:** Trong khi Session 1 vừa sửa xong 8 files và test pass 354/354, Session 2 (chạy song song từ broadcast prompt của User) mở closeout gate hoặc kiểm tra git thấy có file uncommitted nên tự ý chạy:
  `git checkout follow_runner/flows/verify_follow.py follow_runner/tests/test_verify_follow.py docs/farm-automation-cases.md ...`
  làm bốc hơi toàn bộ công sức và code đã test của Session 1.
- **Kỷ luật phòng ngự bắt buộc:**
  1. **Immediate Commit Invariant (Khóa commit ngay khi test pass):** Ngay khi code và focused test hồi quy đã pass 100% (`exit 0`), Coordinator BẮT BUỘC tạo commit Git ngay lập tức (`git commit -m "..."`). Tuyệt đối không để code nằm lơ lửng ở dạng uncommitted qua nhiều turns hỏi đáp/canary; chỉ khi đã vào commit history thì code mới an toàn trước các lệnh `checkout` của session khác.
  2. **Anti-Clobber Invariant:** CẤM TUYỆT ĐỐI mọi session chạy `git checkout -- <files>`, `git restore`, hay `git reset --hard` trên các file mình không trực tiếp tạo ra. Unrelated dirty files bắt buộc phải để nguyên hoặc cô lập qua git worktree riêng (`.worktrees/`).
