# Phân tích & Phân loại Báo cáo Session Watchdog Nuôi Acc (TikTok Feed)

Khi nhận báo cáo Watchdog theo phiên/ca và user hỏi "Row X đi tù / fail hết à?":

## 1. Nguyên tắc cốt lõi
- **Tuyệt đối không kết luận nick bị ban / đi tù** chỉ dựa vào danh sách máy `Fail (N)`.
- Báo cáo Watchdog gom toàn bộ các máy không chạy trọn vẹn kịch bản (lướt đủ số video quy định) vào mục `Fail`.
- Tra cứu nhanh O(1) qua `multi_machine_summary` trong file `run_manifest.json` của session gần nhất:
  Path: `D:/Taadaa/runtime/<host>/live/<YYYY-MM-DD>/row-<ROW>-<HHMMSS>/<RUN_ID>/run_manifest.json`

## 2. 4 nhóm nguyên nhân thực tế
1. **Rớt phần cứng / USB / ADB / Wi-Fi (Chiếm phần lớn khi fail hàng loạt)**:
   - Lý do: `device offline or ADB/USB disconnected`, `dumpsys connectivity: Wi-Fi not connected`, `proxy is unreachable`.
   - Đánh giá: Tài khoản **hoàn toàn an toàn 100%**, script chưa đụng tới app TikTok do rớt kết nối vật lý từ trước.
2. **Kẹt UI / Popup / Mạng tải video chậm**:
   - Lý do: `feed not confirmed`, `contact_follow_suggestion dismissed...`, `unexpected popup/dialog marker detected`.
   - Đánh giá: Tài khoản **đã verify profile thành công** (`_verify_profile: true`), đã lướt được một số video nhưng kẹt popup hoặc mạng chậm timeout lúc load video tiếp theo. Tài khoản an toàn.
3. **Lệch Account Switcher / Mapping Sheet**:
   - Lý do: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
   - Đánh giá: TikTok chưa chuyển đúng slot hoặc tên đăng nhập trên máy lệch với `taikhoan_dat_v2`. Tài khoản không bị ban.
4. **Thực sự bị khóa / Checkpoint (Đi tù thật)**:
   - Dấu hiệu: Log có rõ `banned`, `suspended`, `account-suspended`, `violation`, hoặc dừng tại màn hình kháng nghị / yêu cầu verify SĐT.

## 3. Quy chuẩn phản hồi User
- **Khẳng định ngay lập tức**: Nick có bị ban/đi tù hay không.
- **Thống kê tỷ lệ thành công**: Bao nhiêu máy thành công / tổng số máy.
- **Bóc tách danh sách máy fail**:
  - Nhóm rớt phần cứng (USB / Wi-Fi).
  - Nhóm lỗi UI / Popup / mạng lag.
  - Nhóm lệch account switcher.
- Giữ thông tin súc tích, trực diện, không hoang mang.
