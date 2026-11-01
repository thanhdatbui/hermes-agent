# Kỷ Luật Đối Soát Niche Video Thật & Bắt Buộc Network Preflight Khi Chuẩn Hóa Profile

## 1. Bài Học Xương Máu: Niche Video Thực Tế Là Ground Truth Duy Nhất
- **Bẫy Anchor Bias từ file Excel:**
  - Cột `Keyword Video` trong các file `Tik<N>.xlsx` thường xuyên bị điền nhầm hoặc ghi theo mẫu cũ (ví dụ: ghi là `Xe` nhưng kho video 100% là cảnh câu cá dã ngoại).
  - **Hậu quả tai hại:** Khi điều phối viên (Coordinator) nhìn vào cột Keyword, não bộ bị ám thị rồi tự suy diễn hình ảnh mờ/thumbnail sang chủ đề xe cộ, dẫn đến việc cãi cùn với người dùng khi người dùng hỏi *"video cắn đề xuất thuộc niche nào"*.
- **Quy tắc bất biến:**
  - **CẤM TUYỆT ĐỐI** dựa vào nhãn Keyword trong Excel để phán đoán ngách kênh.
  - **BẮT BUỘC** cắt riêng từng thumbnail của các video đã đăng (`Published Grid`), phóng to và soi mắt trực tiếp qua `browser_vision` để xác nhận chủ thể thật 100% (cần câu, hồ nước, trang phục, hành động).
  - Khi người dùng phản hồi *"Cái video cắn đề xuất là đi câu cá mà? Xe clmm à"*, phải lập tức dừng ngay việc tranh luận, cắt to phóng đại hiện trường để soi lại thay vì cố chấp bảo vệ dữ liệu bảng tính.

## 2. Bắt Buộc Tích Hợp Network Preflight (Khử Dấu Chấm Than '!') Trước Mọi Thao Tác UI
- **Nguyên nhân gốc rễ lỗi "Không thể lưu" trên TikTok:**
  - Thiết bị S7 bị rớt kết nối proxy (proxy port bị timeout, dính quarantine hoặc chưa thông Internet), trên thanh Status Bar cột sóng Wi-Fi có **dấu chấm than (`!`)** (`everValidated{false}`).
  - Khi không có Internet qua proxy, app TikTok client không thể đồng bộ hồ sơ lên server ➔ nảy thông báo lỗi đen mờ `Không thể lưu` khi bấm nút Lưu Bio/Tên.
- **Lỗ hổng cũ của các runner độc lập:**
  - Script như `do_rename_canonical_runner.py` trước đây chỉ kiểm tra kết nối ADB (`adb devices`) mà bỏ qua bước kiểm tra mạng. Khi máy rớt proxy, runner vẫn mù quáng bấm mở TikTok, gõ phím, rồi bị chặn ở bước Lưu.
- **Giải pháp cơ giới hóa $O(1)$ Fail-Closed (Tái sử dụng có sẵn, không chế lại bánh xe):**
  - Tận dụng hàm chuẩn có sẵn từ `automation_core.preflight` (`require_android_vpn`):
    ```python
    try:
        from automation_core.adb import AdbClient
        from automation_core.preflight import require_android_vpn
    except ImportError:
        sys.path.insert(0, r"D:\Taadaa\automation-core\src")
        from automation_core.adb import AdbClient
        from automation_core.preflight import require_android_vpn

    adb_client = AdbClient(
        host="192.168.110.119" if MACHINE_ID >= 200 else None,
        port=5037,
        serial=SERIAL
    )
    try:
        require_android_vpn(adb_client, required=True, interface="wlan0", verify_live_ip=True)
    except Exception as e:
        print(f"   [PREFLIGHT_FAIL] Network Preflight check that bai: {e}")
        return 2
    ```
  - Cơ chế này tự động kiểm tra cờ `VALIDATED` của Wi-Fi và probe `atx-agent curl` qua proxy lấy Public IPv4 thật. Nếu proxy chết, script dừng ngay lập tức tại giây đầu tiên, không mở TikTok, không chạm vào UI máy.

## 3. Kỷ Luật Nghiệm Thu Đủ Bộ 4 Món (Không Bỏ Rơi Avatar)
- Chuẩn hóa kênh bao gồm đầy đủ 4 món:
  1. **Tên hiển thị (Nickname):** Tiếng Việt có dấu, chuẩn tên nhân vật.
  2. **Tiểu sử (Bio):** Tiếng Việt có dấu 100%, đúng ngách.
  3. **Ghim bài (Pin):** Ghim clip $\ge 1.000$ views (dưới 1k view thì giữ nguyên).
  4. **Avatar (Ảnh đại diện):** Bắt buộc phải đẩy lên profile thật qua runner chuyên biệt `run_avatar_batch_3accs.py` hoặc luồng Avatar-Only, chụp ảnh profile thật xác nhận avatar mới đã hiển thị trước khi báo hoàn tất. Cấm đổi xong Tên/Bio rồi bỏ quên Avatar.
