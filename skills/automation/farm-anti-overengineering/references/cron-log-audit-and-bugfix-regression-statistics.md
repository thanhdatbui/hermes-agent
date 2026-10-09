# Quy Chuẩn Quét Log Cron Dài Ngày & Thống Kê Hồi Quy (Bugfix Regression Audit)

## 1. Bối cảnh & Yêu cầu thực tế
Khi người dùng yêu cầu kiểm tra quá trình chạy cron dài ngày để phát hiện hiện tượng "sửa xong lỗi A nhưng sau đó do chạy code sửa lỗi B mà lỗi A bị lại" (Code Fix Regression / Hồi quy mã nguồn):
- Dữ liệu log tích lũy qua nhiều tuần (ví dụ `D:/Taadaa/runtime/kibe/live` chứa 20+ ngày, hàng trăm batch runs, hàng nghìn thư mục máy).
- Mỗi thư mục chứa rất nhiều artifact nặng (XML dump 60-100KB, screenshot PNG 100KB-2MB, `log.jsonl`).
- Nếu quét đĩa không kiểm soát (`os.walk` diện rộng, `grep -rn` toàn ổ đĩa), agent sẽ ngay lập tức dính cạm bẫy **Timeout 900s**, làm nghẽn I/O và sập session.

## 2. Kỷ luật Phân vai (Coordinator vs Worker)
- **Coordinator (Session chính):**
  - Tuyệt đối KHÔNG viết script Python cào dữ liệu hay parse log trực tiếp tại session chính (tránh bloat context hàng chục ngàn dòng kết quả khiến agent compaction rụng chỉ thị).
  - Chỉ xác định O(1) cấu trúc thư mục chứa log (`D:/Taadaa/runtime/kibe/live/<YYYY-MM-DD>/*/*/summary.txt`) và danh mục đối chiếu (`docs/farm-automation-cases.md`, git log).
  - Gửi 1 Dispatch Receipt rõ ràng, cấm `[SILENT]`.
  - Dispatch ngay 1 Worker subagent (Tier 0: Read/Inspect) với mục tiêu đóng gói chặt chẽ.
- **Worker Subagent (Task Read/Inspect):**
  - Ngân sách: <= 10 tool calls, thời gian < 10 phút.
  - CẤM sửa code, CẤM commit, CẤM chạy test suite.
  - Chỉ đọc có chủ đích và trả về bảng thống kê đối chiếu chuẩn xác.

## 3. Quy tắc Truy xuất Log O(1) Phân tầng (Targeted Log Extraction)
1. **Chỉ đọc `summary.txt` ở cấp Run & Machine:**
   - Mỗi lần chạy cron đều sinh ra file tóm tắt `summary.txt` ở 2 cấp:
     + Cấp Run: `live/<YYYY-MM-DD>/<batch_name>/<timestamp>/summary.txt`
     + Cấp Machine: `live/<YYYY-MM-DD>/<batch_name>/<timestamp>/machines/<machine_id>/<timestamp>/summary.txt`
   - Chỉ parse các trường cần thiết:
     + `start_time` / `end_time`
     + `device_serial` / `machine`
     + `account`
     + `status` / `final_status`
     + `stop_reason` / `reason` / `message`
   - **CẤM:** Tuyệt đối không đọc `xml_path`, `screenshot_path` hay mở `log.jsonl` trừ khi cần đào sâu 1 ca duy nhất.
2. **Thuật toán quét an toàn:**
   - Dùng script Python lặp trực tiếp qua danh sách thư mục ngày đã biết (`os.listdir(LIVE_ROOT)`), lọc định dạng `YYYY-MM-DD`.
   - Trong từng ngày, dùng `os.scandir` duyệt 2 tầng thư mục để tìm đúng file `summary.txt`.
   - Thu thập vào dictionary/SQLite tạm để gom nhóm thống kê theo `stop_reason` và ngày.

## 4. Phương pháp Luận Xác Định Hồi Quy (Regression vs Variant)
Đối chiếu dòng thời gian xuất hiện của lỗi với `docs/farm-automation-cases.md` và `git log --oneline`:
1. **Clean Fix (Sửa dứt điểm):**
   - Lỗi A xuất hiện trước ngày $T$, được sửa ở Commit $C_A$ (Case $N$).
   - Sau ngày $T$, `stop_reason` của lỗi A biến mất hoàn toàn trên toàn bộ dàn máy farm.
2. **New Variant / Edge Case (Biến thể mới, không phải hồi quy):**
   - Triệu chứng bề ngoài có vẻ tương tự (ví dụ cùng là "focus lost" hoặc "mismatched username").
   - Nhưng khi đối chiếu traceback và UI element: lỗi xảy ra ở một activity khác (ví dụ: `com.android.systemui` vs `com.google.android.packageinstaller`), hoặc component mới (ví dụ modal "Thông tin về AI" vs popup "Follow bạn").
   - Đây là trường hợp chưa bao phủ (Uncovered Edge Case), không phải do code fix B phá vỡ code fix A.
3. **True Regression (Hồi quy thực sự):**
   - Lỗi A đã được khắc phục ở Commit $C_A$.
   - Sau khi deploy Commit $C_B$ (sửa lỗi B), lỗi A lại tái phát trên cùng kịch bản, cùng component.
   - Nguyên nhân thường gặp:
     + Ghi đè file hoặc revert nhầm do merge/rebase.
     + Code fix B làm thay đổi thứ tự ưu tiên (priority order) trong registry (ví dụ `BENIGN_POPUP_REGISTRY`).
     + Thụt lề sai (Indentation bug) hoặc biến cục bộ bị đặt ngoài scope try/except (Case 126).
     + Timeout hoặc điều kiện retry bị siết quá chặt khiến recovery của lỗi A không kịp kích hoạt.

## 5. Cấu trúc Báo cáo Thống kê Chuẩn
Báo cáo gửi người dùng BẮT BUỘC theo cấu trúc 3 phần:
1. **Bảng phân bổ lỗi theo mốc thời gian:** Tần suất các mã lỗi chính qua các ngày trước và sau các mốc commit sửa lỗi.
2. **Bảng đối chiếu từng Case đã xử lý:**
   - Case ID / Mã lỗi.
   - Ngày fix / Commit hash.
   - Tình trạng sau fix (Đã sạch 100% / Xuất hiện biến thể mới / Có dấu hiệu hồi quy).
3. **Kết luận dứt khoát:** Trả lời trực diện câu hỏi của người dùng: Có hay không có hiện tượng fix B làm lỗi A tái phát? Kèm bằng chứng cụ thể.
