# Kỷ Luật Đối Soát Niche Nguồn Thực Tế vs Bẫy Anchor Bias Excel & Preflight Network Fail-Closed

## 1. Bài Học Xương Máu: Bẫy Anchor Bias Cột Keyword Trong Excel vs Video Thực Tế
- **Hiện tượng sự cố:**
  - Khi tra cứu toạ độ kênh (ví dụ: qua `lookup_channel.py` hoặc đọc `TikN.xlsx`), bảng tính ghi `Keyword: Xe` kèm bộ hashtag `#xe #xevietnam...`.
  - Coordinator bị thiên kiến neo (Anchor Bias) bởi nhãn Excel có sẵn, khi nhìn lướt thumbnail kênh vội vàng kết luận và cãi cố là ngách "Xe & Giao thông".
  - Người dùng chất vấn: *"Cái video cắn đề xuất là đi câu cá mà? Xe clmm à"*.
  - Đến khi cắt riêng từng thumbnail phóng to 3x và soi mắt qua `browser_vision` thì sự thật hiện trường mới lộ rõ: 100% video là cảnh bờ sông hồ, cắm cần giật cá ngoài trời (Ngách Câu Cá).
- **Quy tắc bất di bất dịch (Ground Truth Invariant):**
  - **Video thực tế trên kênh và trong kho video render mới là MỎ NEO CHÂN LÝ DUY NHẤT.**
  - Cột `Keyword` trong file Excel thường xuyên bị nhân viên lập bảng hoặc tool gán nhãn rập khuôn/sai lệch. Tuyệt đối **CẤM** lấy nhãn Excel làm bằng chứng kết luận ngách kênh khi người dùng đã nghi vấn.
  - Khi người dùng hỏi *"thuộc niche nào"*: BẮT BUỘC kiểm tra trực tiếp nội dung video trong kho render (`D:/TIKTOK-videonuoinick/<F_vid>` hoặc `admin` mirror) và soi mắt phóng to thumbnail thật trên kênh.

## 2. Kỷ Luật Preflight Network Bắt Buộc Trước Mọi Script Thao Tác Farm (Chống Chạy Mù)
- **Sự cố mất mạng dấu chấm than `!`:**
  - Máy bị rớt proxy (`timed out` hoặc dính `QUARANTINE_R3G`), Android hiển thị dấu `!` trên cột sóng Wi-Fi (`everValidated{false}`).
  - Script đổi tên/bio (`do_rename_canonical_runner.py`) do không tích hợp bước kiểm tra mạng nên vẫn thực thi mù quáng: mở app TikTok, gõ bio và bấm Lưu, dẫn đến TikTok nảy popup lỗi `Không thể lưu`.
- **Cơ chế Fail-Closed có sẵn trong `automation_core.preflight` (CẤM chế lại bánh xe):**
  - Hệ thống đã có sẵn hàm `require_android_vpn` trong `automation_core.preflight`:
    ```python
    from automation_core.adb import AdbClient
    from automation_core.preflight import require_android_vpn

    adb_client = AdbClient(host="192.168.110.119" if MACHINE_ID >= 200 else None, port=5037, serial=SERIAL)
    require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
    ```
  - **Tác dụng:**
    * Tự động probe `atx-agent curl` qua global proxy lấy Public IP ngoài Internet trong $\le 5s$.
    * Tự động kiểm tra cờ `VALIDATED` Wi-Fi, tóm gọn dấu `!` ngay tại giây đầu tiên.
    * Nếu mạng lỗi: Ngay lập tức ném lỗi, dừng toàn bộ tiến trình (`exit 2`), tuyệt đối không mở app, không gõ phím, bảo vệ tài khoản an toàn 100%.
