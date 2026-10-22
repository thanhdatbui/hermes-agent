# Watchdog Report Anti-Parrot Protocol & USB Case Invariant Protection

## 1. Kỷ Luật Tiếp Nhận Watchdog Report (Anti-Parrot Invariant)
- **CẤM TUYỆT ĐỐI:** Nhại lại, dịch nghĩa, tóm tắt lại văn bản của bản tin watchdog report / alert trên Telegram cho Operator.
- **HÀNH ĐỘNG BẮT BUỘC:** Report ném vào chat = **LỆNH ĐIỀU TRA KỸ THUẬT VÀ TỰ GIÁC SỬA LỖI TẬN GỐC NGAY LẬP TỨC**.
- **Quy trình chuẩn O(1):**
  1. Trích xuất ngay `run_manifest.json` và `log.jsonl` tại `D:/Taadaa/runtime/<cluster>/live/<date>/<run_dir>/<subrun>/run_manifest.json`.
  2. Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` kiểm tra 2-3 máy đại diện của từng nhóm lỗi xem thiết bị có online thật trên ADB hay không.
  3. Bóc tách 3 tầng: (a) Phần cứng/nguồn/cáp USB thật, (b) Bug code logic/preflight/detector, (c) Treo ứng dụng/quảng cáo TikTok.
  4. Nếu là bug code: Tự giác kích hoạt L1/L2 sửa ngay, chạy focused test < 30s và commit, không đứng im chờ ra lệnh.

## 2. Bảo Vệ Thông Số Vàng Case 162 (Chống Regression Loop USB Timeout)
- **Triệu chứng:** Máy mất hẳn cáp USB giữa chừng bị ngâm 50 phút (`run plan max_duration_seconds exceeded`) do chuỗi retry nhiều bước ADB liên tiếp.
- **BẪY HỒI QUY TAI HẠI:** Hạ `connection_wait_timeout` (từ 20s xuống 4s) hoặc hạ `connection_retry_attempts` trên `AdbClient` để "fail-fast cho đỡ ngâm".
- **Hậu quả:** Phá vỡ **Case 162** (13/09/2026). Khi USB Hub công nghiệp bị sụt tải tạm thời (micro-drop 5-10s), thiết bị cần tối thiểu 15-20s và 5 lần retry để re-enumerate. Nếu hạ timeout, các máy giật điện nhẹ sẽ bị khai tử đồng loạt, làm sập cả mẻ batch.
- **Quy tắc bất biến:**
  * `connection_wait_timeout = 20.0s`, `connection_retry_attempts = 3`, `ADB_ONLINE_ATTEMPTS = 5` kèm progressive backoff là **THÔNG SỐ VÀNG BẢO VỆ PHẦN CỨNG**, CẤM TUYỆT ĐỐI HẠ XUỐNG.
  * Khi máy đứt hẳn kết nối vật lý, việc runner dừng sau deadline 50 phút là cơ chế an toàn fail-closed chuẩn của hệ thống; giải pháp duy nhất là cắm lại cáp/nguồn tổ ong, KHÔNG ĐƯỢC sửa code hạ timeout để che giấu triệu chứng.

## 3. Pitfall ADB Shell `check=False` Bỏ Sót Retry Trong Preflight
- **Hiện tượng:** Khi hàng chục máy khởi động cùng lúc, daemon ADB bị nghẽn socket tạm thời khiến lệnh `settings get global http_proxy` trả về `adb.exe: device '<serial>' not found`.
- **Nguyên nhân bug:** Lệnh gọi qua `adb.shell(..., check=False)`. Vì `check=False`, `AdbClient.run()` trả về `AdbResult(returncode=1, stderr="device not found")` mà KHÔNG ném Exception.
- **Hậu quả:** Khối `try...except` không bắt được exception, code rơi thẳng vào lệnh `break` ngay ở attempt 0, hoàn toàn bỏ qua vòng lặp retry 2 lần. Sau đó kiểm tra `is_connection_lost(p_err)` thấy True liền ném `ConsumerPreflightError`, loại oan hàng chục máy đang online bình thường.
- **Giải pháp chuẩn:** Khi dùng `check=False` trong vòng lặp retry, BẮT BUỘC kiểm tra cả `is_connection_lost(p_err)` trong khối `try`. Nếu có lỗi kết nối, phải gọi `adb.reconnect()` và `continue` sang attempt tiếp theo, cấm `break` sớm.

## 4. Pitfall Nhận Diện Đơn Ngữ Trên Màn Hình TikTok (Edit Name / Subpage Overlays)
- **Hiện tượng:** Máy TikTok hiển thị màn hình sửa tên ("Add your preferred name") do chạm lệch tọa độ, nhưng classifier trả về `unknown TikTok state` và kẹt ở `manual-needed`.
- **Nguyên nhân:** Hàm `detect_edit_name_subpage` trong `core/benign_popup.py` chỉ kiểm tra chuỗi tiếng Việt (*"thêm tên bạn mong muốn"*, *"chỉ có thể đổi tên"*). Khi máy farm chạy ngôn ngữ tiếng Anh/Đức, detector trả về `None`.
- **Giải pháp chuẩn:** Mọi hàm detector trong `core/benign_popup.py` và `flows/benign_popup_registry.py` bắt buộc phải hỗ trợ đầy đủ các token tiếng Anh (*"add your preferred name"*, *"changed once every 7 days"*, *"add name"*) và tiếng Đức (*"füge deinen bevorzugten namen hinzu"*).
