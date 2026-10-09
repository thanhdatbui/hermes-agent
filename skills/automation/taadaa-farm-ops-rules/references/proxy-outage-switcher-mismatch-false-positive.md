# Root Cause Triad: Proxy Downstream Outage vs Account Switcher Mismatch (False Positive)

## Bối cảnh & Hiện tượng
Khi nhận được Batch Alert diện rộng (>5 máy, ví dụ 9/80 máy lỗi) với signature:
`script-blocker:profile username still mismatched after switch`
trên các máy như M34, M36, M37, M72, M73, M77, M78, M79, M80...

## Phân tích Triad (Kiểm tra 3 bước O(1))

1. **Kiểm tra thiết bị (Hardware/ADB):**
   - Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` hoặc lệnh ADB trực tiếp theo serial máy.
   - Thường thiết bị vẫn trực tuyến và ở màn hình bình thường (`LauncherActivity` hoặc `com.zhiliaoapp.musically`).

2. **Kiểm tra hạ tầng Proxy (Sing-box 200xx / Upstream 51xx):**
   - Đoán định lỗi `switcher mismatch`: Khi chuyển account, app TikTok cần kết nối mạng để đồng bộ thông tin profile, avatar, username mới.
   - Nếu proxy chết (DEAD/CLOSED), kết nối timeout hoặc trả về lỗi mạng, app không tải được username mới -> Script so sánh username mong đợi với UI hiện tại và ném lỗi `profile username still mismatched after switch`.
   - Quét socket O(1) kiểm tra port proxy `20000 + M#` trên 127.0.0.1.
   - Nếu >30% cổng (hoặc 100% như trong phiên này) DEAD -> Đây là **False Positive do sự cố Proxy mạng**, KHÔNG PHẢI lỗi code automation hay logic chuyển account.

3. **Kỷ luật Điều phối (Coordinator Invariant):**
   - **CẤM TUYỆT ĐỐI debug code hay sửa script/flow khi proxy sập.**
   - Kích hoạt **Circuit Breaker** ngay lập tức: Khóa batch, dừng phân rã và không dispatch worker sửa code.
   - Báo cáo rõ root cause hạ tầng: Tiến trình Sing-box bị tắt hoặc nguồn upstream proxy gián đoạn.
   - Khôi phục hạ tầng proxy -> Canary test xác thực trên 1 máy -> Mở khóa batch sau khi canary thành công.
