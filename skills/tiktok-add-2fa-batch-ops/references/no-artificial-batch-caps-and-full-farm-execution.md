# Triệt Tiêu Giới Hạn Máy Nhân Tạo (No Artificial Batch Caps) & Quy Tắc Khai Thác Tối Đa Phone Farm

*Ngày ghi nhận: 14/09/2026*  
*Nguồn chỉ đạo: User ("Mà vì sao phải đặt giới hạn cứ để script chạy đi chứ. Sửa cái vụ đặt giới hạn đó đi, cả ở script khác")*

---

## 1. Bản Chất Vấn Đề & Anti-Pattern Cũ
- Trong nhiều script tự động hóa (như `run_all.ps1` bên Reg Gmail, `run_batch_live_2fa.py` bên Add 2FA TikTok), các phiên bản cũ thường đặt các rào cản trần cứng nhân tạo:
  - `maxMachines = 15` (kèm logic `if ($maxMachines -gt 15) throw ...`).
  - `MAX_BATCH_SIZE = 40` (chặn trần nửa dàn máy).
  - Tự ý truyền `--limit 15` vào caller/watchdog vì sợ không kịp giờ.
- **Hệ quả tiêu cực:**
  - Dàn có 80 máy nhưng mỗi đợt chạy chỉ tận dụng được 15 máy, 65 máy còn lại ngồi chơi dù thời gian nghỉ giữa các ca lên tới 2–3 tiếng.
  - Các tài khoản xếp ở phía sau không bao giờ đến lượt chạy, gây ứ đọng và kéo dài thời gian hoàn thành mục tiêu toàn farm.

---

## 2. Quy Tắc Vận Hành Mới Được Phê Duyệt

### 2.1. Không Giới Hạn Số Máy Mục Tiêu (Uncapped Targets)
- `maxMachines = 0` (0 = không giới hạn, quét và chạy toàn bộ máy thỏa mãn điều kiện cooldown/preflight trên toàn farm).
- `MAX_BATCH_SIZE = 80` (bao phủ toàn bộ 80 máy của dàn farm).
- Tuyệt đối không thêm cờ `--limit <N>` vào các cron watchdog tự động trừ khi có lệnh explicit bằng văn bản từ Operator.

### 2.2. Kiểm Soát Tải Bằng Worker Pool Cuốn Chiếu (Chuẩn Concurrency 40 Workers)
- Việc kiểm soát nghẽn mạng, tránh sập USB/ADB và điều tiết tài nguyên máy tính được thực hiện thông qua **Concurrency / Worker Cap**: Thống nhất giữ cấu hình **40 workers song song** (`maxWorkers = 40`, `--max-workers 40`, `DEFAULT_MAX_WORKERS = 40`) trên toàn bộ chuỗi pipeline, **KHÔNG PHẢI** bằng cách cắt giảm số máy tham gia hay bóp nghẹt worker pool xuống 10.
- Cơ chế ThreadPoolExecutor cuốn chiếu: 40 máy khởi chạy so le -> máy nào xong sớm thì nhả lock về màn hình Home nghỉ ngơi -> máy tiếp theo trong hàng đợi lập tức nhảy vào chạy.

### 2.3. Sắp Xếp Độ Ưu Tiên Đúng Trọng Tâm
- Khi chạy batch đa mục tiêu (như Add 2FA), phải xếp các tài khoản **CHƯA CÓ 2FA** (`password_only=False`) lên đầu danh sách `freeze_targets`:
  `candidates.sort(key=lambda item: (item.password_only, not item.has_journal, item.source_row))`
- Tránh để các tài khoản phụ (đã có 2FA nhưng cần xoay pass) chen hàng làm chiếm hết slot máy của tài khoản mới.

### 2.4. Mở Rộng Khung Giờ Watchdog (Không Cắt Giờ Cứng 17:30)
- Watchdog chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) không được cắt giờ sớm lúc 17:30 khi mà Ca 3 tận 18:30–19:00 mới bắt đầu.
- Cửa sổ chạy được mở rộng đến **18:30** (`(15 <= now.hour <= 18 and (now.hour < 18 or now.minute <= 30))`) để tận dụng trọn vẹn thời gian nhàn rỗi giữa Ca 2 và Ca 3.

---

## 3. Quy Định Phân Tách Giữa Reg Gmail và TikTok 2FA (Hiệu Chỉnh 14/09/2026 Theo Lệnh User)
- **LƯU Ý CỐT LÕI TỪ OPERATOR ("gmail reg giữ nguyên, t chỉ bảo bỏ cái limit time thôi mà"):**
  1. **`register gmail` (`D:/Taadaa/register gmail/run_all.ps1`):** **GIỮ NGUYÊN GỐC 100%** (duy trì `$maxMachines = 15` mặc định). Đây là hạn mức có chủ đích để bảo vệ độ bền proxy và cooldown tài nguyên Gmail, tuyệt đối không tự ý gỡ bỏ.
  2. **"Bỏ limit" = BỎ GIỚI HẠN THỜI GIAN (Time Limit):**
     - Áp dụng vào **khung giờ watchdog** (`post_noon_chain_watchdog.py`): Mở rộng từ 14:30 - 17:30 thành **14:30 - 18:30** để không bị cắt giờ sớm trước Ca 3.
     - Áp dụng vào **TikTok 2FA batch**: Nâng `MAX_BATCH_SIZE = 80`, giữ nguyên **40 workers** song song (`--max-workers 40`), ưu tiên nick hoàn toàn chưa có 2FA lên trước. Không tự ý bóp số worker xuống 10 hay gán `--limit 15` vì sợ thiếu thời gian.
