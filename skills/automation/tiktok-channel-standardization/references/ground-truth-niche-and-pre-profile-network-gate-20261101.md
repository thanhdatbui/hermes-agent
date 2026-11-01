# Kỷ Luật Đối Soát Niche Kênh Thực Tế & Network Preflight Cho Thao Tác Hồ Sơ (2026-11-01)

## 1. Cạm Bẫy Neo Tâm Lý Vào Cột Keyword Trong Excel (The Excel Keyword Trap)
- **Bản chất sai lệch:** Cột `Keyword Video` trong các file `Tik<N>.xlsx` thường được lập trình viên điền hàng loạt theo mẫu hoặc copy-paste từ template.
- **Hậu quả tai hại:** Khi user gửi ảnh kênh nhờ chuẩn hoá, nếu Coordinator tra cứu file Excel thấy ghi `Keyword: Xe` rồi vội vàng nhìn lướt thumbnail suy diễn thành xe cộ/khoang lái mà không soi mắt đối soát kỹ lưỡng, dẫn đến việc cãi cùn và đối đầu với nhận định đúng của User.
- **Quy tắc bất biến (Ground Truth Invariant):**
  * **Video đã đăng trên kênh và video trong kho F_src/F_vid là MỎ NEO CHÂN LÝ DUY NHẤT.**
  * BẮT BUỘC dùng `browser_vision` cắt riêng từng thumbnail phóng to 2x-3x để soi tận mắt chủ thể (ví dụ: cần câu, mặt nước, bờ sông thay vì xe cộ).
  * Nếu video thực tế lệch với Excel: **Nội dung video THẮNG tuyệt đối**, lập tức cập nhật lại cột Keyword & Hashtag trong Excel theo đúng video thực tế.

## 2. Điểm Mù Preflight Mạng Trước Khi Thao Tác Hồ Sơ (Pre-Profile Network Check Blind Spot)
- **Hiện tượng:** Runner thực hiện đổi tên, bio, avatar (`do_rename_canonical_runner.py`) nhưng app TikTok bung lỗi `Không thể lưu` hoặc treo nút lưu.
- **Nguyên nhân gốc rễ:**
  * Runner chỉ kiểm tra kết nối ADB (`adb devices`) chứ hoàn toàn không kiểm tra máy có kết nối Internet thật qua proxy hay không.
  * Khi proxy bị timeout (như cụm 32 máy Admin đang bị cách ly Quarantine R3G), Android S7 bị mất mạng, trên thanh trạng thái xuất hiện biểu tượng Wi-Fi có **dấu chấm than (`!`)**.
  * Ở trạng thái này, app TikTok client không thể đồng bộ request lên server nên từ chối lưu.

## 3. Tận Dụng Module Có Sẵn `automation_core.preflight` (Chống Chế Lại Bánh Xe & Anti-Overengineering)
- **Không đẻ thêm gate rác, không viết lại script mới:** Hệ thống farm đã có sẵn module kiểm tra mạng chuẩn mực được kiểm chứng qua hàng ngàn ca nuôi feed tại `D:/Taadaa/automation-core/src/automation_core/preflight.py`.
- **Chốt chặn Fail-Closed đúng 3 dòng $O(1)$:**
  Bất kỳ script thao tác profile nào (đổi tên, nạp bio, đổi avatar, ghim bài) đều bắt buộc tích hợp bước kiểm tra mạng bằng hàm có sẵn ngay trước khi mở app TikTok:
  ```python
  from automation_core.adb import AdbClient
  from automation_core.preflight import require_android_vpn, ConsumerPreflightError

  # Chặn đứng chạy mù khi rớt mạng / Wi-Fi dính dấu !:
  adb_client = AdbClient(host="192.168.110.119" if MACHINE_ID >= 200 else None, port=5037, serial=SERIAL)
  require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
  ```
- **Hành vi Fail-Closed chuẩn:**
  * Hàm `require_android_vpn()` tự động đối soát `dumpsys connectivity` (bắt dấu `!` Wi-Fi không Validated) và bắn `atx-agent curl` kiểm tra Egress IP qua proxy.
  * Nếu proxy chết hoặc Wi-Fi mất mạng: Script ngắt ngay tại giây đầu tiên (`ConsumerPreflightError`), thoát an toàn, không mở TikTok và không spam bàn phím.
