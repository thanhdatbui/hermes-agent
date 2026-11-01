# Bài Học Vận Hành: Bẫy Phán Đoán Ngách Qua Bảng Tính & Kỷ Luật Preflight Proxy Trên Mọi Script Farm (2026-11-01)

## 1. Bẫy Nguy Hiểm: "Tin Mù Vào Keyword Trong Excel" vs Mỏ Neo Chân Lý Video Thực Tế
- **Hiện tượng:**
  - Nhận task chuẩn hoá kênh `@hothanhlan873` (Máy 223 - Slot Tik 5 cụm Admin).
  - Tra cứu O(1) qua `lookup_channel.py` hoặc đọc `Tik5.xlsx` thấy ghi cột `Keyword Video: Xe`.
  - Agent bị **Anchor Bias (Ám thị thông tin cũ)**: Khi nhìn vào thumbnail, tự suy diễn hình ảnh mờ mờ thành góc quay đường phố/khoang lái xe ô tô, cố cãi với User rằng kênh làm về Xe cộ.
  - **Thực tế User phản bác:** *"Cái video cắn đề xuất là đi câu cá mà? Xe clmm à"*.
  - Cắt riêng thumbnail và phóng to 3x qua `browser_vision`: Rõ mồn một cảnh bờ sông hồ, cắm cần giật cá, dã ngoại sông nước (100% ngách Câu Cá).
- **Quy tắc bất di bất dịch (Ground Truth Invariant):**
  - **File Excel quản lý farm rất hay bị gán nhãn ẩu/sai lúc lập bảng (human error).**
  - CẤM TUYỆT ĐỐI lấy cột Keyword trong Excel làm chân lý để suy đoán nội dung kênh.
  - **MỎ NEO CHÂN LÝ DUY NHẤT:** BẮT BUỘC phải soi trực tiếp nội dung video đã đăng trên lưới Profile và video gốc trong kho đích (`D:\TIKTOK-videonuoinick-admin\<F_vid>`).
  - Khi User hỏi vặn về ngách ("có chắc không", "thuộc niche nào"), BẮT BUỘC kiểm tra ngược từ kho video nguồn vật lý, CẤM trích dẫn lại dòng text trong Excel để cãi cùn.

---

## 2. Sự Cố Rớt Proxy Dẫn Đến Wi-Fi Dấu Chấm Than (`!`) & Lỗi "Không Thể Lưu"
- **Hiện tượng:**
  - Khi chạy `do_rename_canonical_runner.py` để đổi tên/bio, runner nạp bio và bấm Lưu thì TikTok báo popup: `Không thể lưu`.
  - Trên thanh status bar của Android S7, cột sóng Wi-Fi có dấu chấm than (`!`).
  - Lệnh `dumpsys connectivity` báo `everValidated{false}`, `lastValidated{false}`.
  - Proxy `192.168.110.2:20223` (Sing-box R3G) đang bị timeout, mất kết nối ra Internet.
- **Nguyên nhân gốc rễ:**
  - Các script thao tác profile (đổi tên, nạp bio, avatar) trước đây **chỉ check ADB connection** chứ **KHÔNG CÓ BƯỚC PREFLIGHT NETWORK**.
  - Khi máy mất proxy/rớt mạng, runner vẫn mở TikTok, spam bàn phím và bấm Lưu trong vô vọng, dẫn đến lỗi app và rủi ro bị TikTok flag bất thường.

---

## 3. Kiến Trúc Chuẩn Bắt Buộc: Network Preflight Fail-Closed O(1)
- **Không chế lại bánh xe, không over-engineer:** Tận dụng 100% hàm chuẩn đã có trong `automation_core.preflight` (`require_android_vpn`).
- **Tích hợp vào mọi script thao tác profile/UI:**
  ```python
  from automation_core.adb import AdbClient
  from automation_core.preflight import require_android_vpn

  def _execute_rename_inner():
      # BƯỚC 0: PREFLIGHT CHECK BẮT BUỘC - FAIL-CLOSED
      adb_client = AdbClient(
          host="192.168.110.119" if MACHINE_ID >= 200 else None,
          port=5037,
          serial=SERIAL
      )
      try:
          require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
      except Exception as e:
          print(f"   [PREFLIGHT_FAIL] Network Preflight check that bai: {e}")
          return 2  # Dừng ngay lập tức ở giây đầu tiên, KHÔNG mở app TikTok
  ```
- **Hành vi Fail-Closed chuẩn:**
  1. Nếu proxy chết / Wi-Fi dính dấu `!` / không curl ra được Public IP: Ngắt ngay lập tức (`exit 2`).
  2. Không chạm màn hình, không mở TikTok, không gõ phím.
  3. Giữ an toàn tuyệt đối cho tài khoản, ngăn chặn triệt để hành vi chạy mù khi mất mạng.
