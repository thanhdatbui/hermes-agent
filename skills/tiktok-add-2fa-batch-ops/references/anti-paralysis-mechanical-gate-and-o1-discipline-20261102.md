# Kỷ luật Chống Khóa Cơ Học Bại Liệt và Bản Chất O(1) Thực Dụng

## 1. Bối cảnh & Câu hỏi chất vấn của Operator
- **Câu hỏi của User:** *"Có gây over-engineer và bại liệt không? Khóa cơ học thì mày bảo over-engineer, rồi có gây bại liệt không?"*
- **Tình huống phát sinh:**
  1. Khi sửa `python_runner/run_batch_live_2fa.py` chuyển `freeze_targets()` sang SQLite `farm_master.db`, pipeline chạy canary máy thật bị văng `CANARY_FAILED: Máy 1 không có ảnh screencap nghiệm thu hợp lệ`.
  2. Nguyên nhân do `canary_runner.py` quy định cứng ảnh screencap phải `> 30,000 bytes`. Các màn hình AMOLED màu tối hoặc màn hình Splash của Android Samsung S7 nén PNG ra dung lượng nhỏ (~13KB–24KB) bị đánh rớt sai (false negative), gây kẹt pipeline và dừng thi công.
  3. Sau đó, khi `freeze_targets_from_sqlite()` được viết ban đầu, câu truy vấn SQL viết nhầm tên cột (`m.machine_no` thay vì `a.machine_id`, `m.serial` thay vì `COALESCE(m.device_serial, '')`) khiến câu lệnh văng `OperationalError` làm fallback rơi ngược lại vòng lặp đọc file Excel cũ.
  4. Lệnh test focused `pytest` bị timeout 600s do chạy bao trùm toàn bộ thư mục test dính test case UI mocking treo, thay vì chạy đúng file test tập trung của batch runner.

---

## 2. Bản chất: Khóa Cơ Học vs Over-Engineering & Bại Liệt

### A. Cái gì là "Bại liệt / Over-Engineering" (Bị cấm triệt để):
1. **Gate rác và Wrapper thừa thãi:** Viết thêm 3–4 script wrapper bên ngoài chỉ để bao bọc 1 lệnh cơ bản, bắt agent chạy vòng tròn xin phép / tạo ticket ảo mà không tạo ra giá trị kiểm chứng thực tế.
2. **Quét đĩa diện rộng mù quáng:** Chạy script lùng sục cả ổ cứng (`os.walk`, `find`, `grep -r`, `search_files`) để tìm file log hoặc kiểm tra xem worker có làm đúng không $\rightarrow$ Gây nghẽn đĩa I/O, cạn token context và treo phiên.
3. **Chốt chặn mù không có đường thoát (False Positives):** Đặt các ngưỡng số học cứng ngắc không có căn cứ thực tế (như ép ảnh screencap phải $> 30\text{KB}$ dù màn hình AMOLED tối nén PNG cực nhẹ chỉ 13KB) $\rightarrow$ Ép pipeline phải rollback và Agent đứng im chịu trận.
4. **Viết test đồ sộ lan man:** Chạy test suite toàn repo dính các test UI/Mocking giả lập cũ bị lỗi hoặc timeout khiến toàn bộ quy trình sửa đổi $O(1)$ bị tê liệt.

### B. Khóa Cơ Học Chuẩn $O(1)$ (Không bao giờ gây bại liệt):
1. **Khóa bằng Exit Code & Test Thật tại Điểm Nghẽn (Execution Bottleneck):**
   - Chỉ kiểm tra đúng kết quả đầu ra: Exit code $0$, assertion pass, read-back DB thật.
   - Test tập trung chạy đúng 1 file focused (< 5 giây), không mock bậy và không kéo theo toàn bộ test suite cồng kềnh.
2. **Khóa bằng CSDL SSOT:**
   - Cắt đứt hoàn toàn việc mở file Excel và khóa độc quyền `acquire_workbook_lock()` trong runtime loop.
   - Nạp mục tiêu trực tiếp từ SQLite SSOT (`D:/Taadaa/data/farm_master.db`), đối soát khớp chuẩn schema (`machine_id`, `twofa_secret`, `device_serial`).
3. **Nghiệm thu Thực Địa (Gate 6 & Vision Mắt Thật):**
   - Không tin worker self-report. Chạy `canary_runner.py` trên máy thật, chụp ảnh screencap thực tế (ngưỡng dung lượng $> 5\text{KB}$ bao trùm cả màn hình AMOLED tối) và bắt buộc gọi `browser_vision` soi mắt trước khi chốt phiên.

---

## 3. Quy trình Thi công Dứt điểm O(1) khi Sửa Code Repo Farm
1. **Sửa code bắt buộc qua Pipeline liên hoàn:**
   ```bash
   python D:/Taadaa/tools/unified_patch_pipeline.py run --repo "<repo>" --file "<file>" --task "<task>" --test-cmd "<focused_test>" [--canary-device <id>]
   ```
2. **Sau khi Pipeline hoàn tất Stage 4 (Canary Máy Thật):**
   - BẮT BUỘC gọi `browser_navigate` và `browser_vision` mở ảnh `canary_*.png` trong `D:/Taadaa/reports/` ra soi mắt kiểm tra (xác nhận giao diện app hoạt động thật, không đen màn hình, không lỗi popup).
   - Gọi lệnh chốt phiên:
     ```bash
     python D:/Taadaa/tools/unified_patch_pipeline.py confirm --run-id <run_id> --text "Done"
     ```
   - Xác nhận `closeout_gate.py` trả về `APPROVED (Score 100/100)`.
3. **Kiểm tra Readback Thực Tế:**
   - Chạy thử runner với cờ `--limit` để chứng minh log in ra nạp từ SQLite SSOT thành công 100% trước khi kết thúc ca.
