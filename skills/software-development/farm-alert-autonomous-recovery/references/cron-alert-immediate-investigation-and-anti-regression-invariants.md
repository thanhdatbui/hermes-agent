# Điều Tra Sự Cố Cron Alert Tức Thời & Chống Vòng Lặp Regression Giữa Các Phiên

## 1. Bản Tin Cron Alert Là LỆNH ĐIỀU TRA KỸ THUẬT NGAY LẬP TỨC

Khi Operator ném bản tin Cronjob Response / Watchdog Report vào phiên làm việc:
- **CẤM TUYỆT ĐỐI:** Ngồi đọc lại, diễn giải, tóm tắt các gạch đầu dòng có sẵn trong alert hoặc đưa ra lời khuyên chung chung "script không cần sửa". Hành vi này bị coi là né tránh trách nhiệm kỹ thuật và câu giờ vô nghĩa.
- **BẮT BUỘC THỰC THI O(1) NGAY LẬP TỨC:**
  1. **Kiểm tra thiết bị thật:** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` trên các máy đại diện trong danh sách lỗi để xác định thực trạng phần cứng / ADB socket ngay lúc này.
  2. **Đọc hiện trường gốc:** Mở trực tiếp `run_manifest.json` và `log.jsonl` tại thư mục live mới nhất `D:/Taadaa/runtime/<cluster>/live/<date>/<run_id>/` (lấy từ Run ID gắn trên header report).
  3. **Bóc tách lỗi đa tầng:**
     - *Phần cứng đứt thật vs Rớt giả:* Phân biệt máy mất kết nối ADB vật lý thật (cáp/nguồn hub sập) với máy vẫn online trên ADB nhưng bị script preflight loại nhầm do nghẽn socket.
     - *Sự cố ứng dụng:* Đơ SplashActivity, bị LMK kill, hay dính popup lạ chưa hỗ trợ (ví dụ màn hình "Edit Name" giao diện tiếng Anh).
     - *Dịch vụ nền:* Treo daemon ATX-agent (port 7912) hay lỗi touch input.
  4. **Tự giác khắc phục:** Nếu phát hiện bug logic/preflight/popup: tự giác kích hoạt L1/L2 sửa ngay theo đúng quy trình O(1) kèm focused test < 30s; nếu là lỗi phần cứng: chỉ đích danh danh sách máy kèm bằng chứng cho Operator.

---

## 2. Chống Vòng Lặp Mất Trí Nhớ Giữa Các Phiên (Session-to-Session Amnesia / Flip-Flop Loop)

### Bẫy Con Lắc Phổ Biến
- **Session A:** Gặp sự cố USB hub công nghiệp bị sụt tải tức thời (micro-drop 5–10s) làm rớt hàng loạt máy $\rightarrow$ Nâng `connection_wait_timeout = 20.0s`, `connection_retry_attempts = 3`, `ADB_ONLINE_ATTEMPTS = 5` kèm progressive backoff (ghi nhận Case 162).
- **Session B (vài tuần sau):** Thấy máy bị rút hẳn cáp USB ngồi chờ retry đến 50 phút mới hết deadline $\rightarrow$ Agent táy máy hạ `connection_wait_timeout` xuống 4.0s để "cho đỡ ngâm lâu" $\rightarrow$ Phá vỡ hoàn toàn cơ chế bảo vệ của Case 162, tạo ra vòng lặp sửa ngược nhau giữa các session!

### Quy Tắc Bất Biến Ngăn Chặn Regression
1. **Kiểm Tra Case Catalog Trước Khi Chạm Vào Timeout/Retry:**
   Trước khi sửa bất kỳ thông số kết nối, timeout (`connection_wait_timeout`, `DEFAULT_DEVICE_TIMEOUT_SECONDS`), số lần thử (`attempts`, `ADB_ONLINE_ATTEMPTS`), hoặc cơ chế nhả lease lock: BẮT BUỘC tra cứu `docs/farm-automation-cases.md`.
2. **Cấm Chữa Triệu Chứng Mù Quáng:**
   Khi cụm máy mất kết nối vật lý, việc worker kiên nhẫn chờ retry theo đúng deadline là hành vi mong muốn để cứu các máy giật cáp nhẹ. Tuyệt đối không được hạ timeout của tầng kết nối ADB để chữa triệu chứng "chờ lâu", vì sẽ giết oan toàn bộ các máy micro-drop tạm thời.
3. **Cơ Giới Hóa Bằng Invariant Test Thay Vì Tài Liệu Văn Bản:**
   Mỗi Case quan trọng trong `docs/farm-automation-cases.md` (như Case 162) bắt buộc phải có file test tương ứng (ví dụ `test_case162_...`) assert cứng các ngưỡng thông số vàng (`assert connection_wait_timeout >= 15.0`). Nếu chỉ ghi tài liệu mồm, regression gate của Closeout sẽ hoàn toàn mù lòa vì các test chức năng thông thường vẫn xanh.
