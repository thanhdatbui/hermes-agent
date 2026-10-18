# Stale Upload Watchdog & Tracker DB Drift Triage Protocol (12/10/2026)

Hướng dẫn đối soát và xử lý khi nhận cảnh báo tiến độ upload toàn farm (`daily-stale-upload-accounts-watchdog` - job_id `5ad19a65f7ef`).

---

## 1. Hiện tượng & Bản chất Lệch Dữ liệu (DB Drift / Stale Timestamp)
- **Hiện tượng:** Bản tin đối soát gửi về Telegram hiển thị ngày tham chiếu cũ trong ngoặc `(2026-10-10)` dù thời điểm chạy thực tế là ngày hôm nay (`12/10/2026`).
- **Nguyên nhân cốt lõi:**
  - Script audit `D:/Taadaa/tools/audit_stale_upload_accounts.py` cấu hình mặc định:
    ```python
    DEFAULT_DB_PATH = r"D:/OneDrive/TaadaaData/tiktok_tracker.db"
    FALLBACK_DB_PATH = r"D:/Taadaa/data/tiktok_tracker.db"
    ```
  - Trong thực tế vận hành, Single Source of Truth thời gian thực được cronjob cào dữ liệu `cron_tiktok_daily_tracker.py` ghi nhận là **`D:/Taadaa/data/tiktok_tracker.db`**.
  - File trên OneDrive chỉ là bản sao lưu tĩnh cũ hơn (dừng ở ngày 10/10). Do `DEFAULT_DB_PATH` tồn tại trên đĩa, script không bao giờ kích hoạt fallback, dẫn tới tính toán `days_stale` và số lượng active/stale bị kẹt theo mốc thời gian quá khứ.

---

## 2. Quy trình Đối soát Nhanh O(1) (Instant Sanity Check)
1. **Chạy trực tiếp canonical audit script (CẤM dùng `python -c` subprocess):**
   * Guard Coordinator chặn `python -c` có subprocess/file cache hoặc scan đệ quy `Path()`. Chạy thẳng lệnh CLI có sẵn:
   ```bash
   python D:/Taadaa/tools/audit_stale_upload_accounts.py --days 7 --critical-days 14
   ```
   *(Lưu ý: Script trả exit code 1 khi phát hiện có tài khoản stale >14d — đây là exit contract cảnh báo hợp lệ, stdout chứa toàn bộ báo cáo tóm tắt sạch sẽ).*
   * Nếu cần trích xuất và phân tích JSON mà không bị Guard chặn subprocess/scan:
   ```bash
   python D:/Taadaa/tools/audit_stale_upload_accounts.py --days 7 --critical-days 14 --json > %TEMP%/stale_audit.json
   ```
   Sau đó đọc file bằng `python -c "import json; ..."` thuần túy (không gọi subprocess hay quét đĩa).
2. **Đối soát DB SQLite thời gian thực (`D:/Taadaa/data/tiktok_tracker.db`):**
   * Schema: Bảng `farm_account_info` (`username`, `may`, `tik`, `host_id`) map với bảng `snapshots` (`username`, `video`, `timestamp`).
   * Truy vấn O(1) nhanh kiểm tra 8 slot của máy:
   ```sql
   SELECT f.tik, f.username, s.video, s.timestamp
   FROM farm_account_info f
   LEFT JOIN (
       SELECT username, video, timestamp, MAX(timestamp)
       FROM snapshots GROUP BY username
   ) s ON f.username = s.username
   WHERE f.may = ? AND f.host_id = 'kibe'
   ORDER BY f.tik;
   ```
3. **Kiểm tra hiện trường phần cứng máy nghi ngờ:**
   * Dùng lệnh chuyên dụng O(1):
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <N>
   ```
   * Nếu ADB báo `device '<serial>' not found`: thiết bị đã rớt cáp USB / mất nguồn vật lý dài ngày (như M10, M30), cần cắm lại phần cứng, không phải lỗi runner.
4. **Kỷ luật dọn file tạm (Safe Cleanup Invariant):**
   * Coordinator bị chặn lệnh `rm` bởi Default-Deny Guard.
   * Mọi file debug tạm thời tạo trong `D:/Taadaa/tools/` BẮT BUỘC dọn qua:
   ```bash
   python D:/Taadaa/tools/safe_recycle.py <path_to_temp_file>
   ```

---

## 3. Quy tắc Phân loại 4 Tầng khi Triage Top Nick Bị Đóng Băng (>14 ngày)

Khi nhận danh sách cảnh báo các nick không tăng video >14 ngày, **CẤM** suy diễn vội vàng hoặc sửa mò code upload. Bắt buộc phân loại theo 4 nhóm nguyên nhân độc lập:

### Tầng 1: Lỗi Phần cứng / ADB Thiết bị (Hardware Disconnect vs Temporary EHCI Drop)
- **Kiểm tra:** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` cho các máy xuất hiện trong top đầu (ví dụ Máy 10, Máy 30, Máy 44, Máy 55, Máy 69).
- **Dấu hiệu:** ADB trả về `device not found` hoặc `offline` (tuột cáp USB, sập nguồn, treo hub, hoặc nghẽn bus USB EHCI sau 24h).
- **CẢNH BÁO QUY KẾT NHẦM (User Correction 13/10/2026):**
  - CẤM vội vàng quy kết nick kẹt >14 ngày là do offline phần cứng chỉ vì lúc kiểm tra thấy máy rớt ADB.
  - Phải kiểm tra chéo các slot khác (Tik 1..8) của máy trong database/Excel: Nếu các slot khác vẫn đăng video trong vài ngày qua, máy hoàn toàn online bình thường, việc rớt ADB chỉ là nghẽn bus EHCI tạm thời (sẽ tự phục hồi sau reboot 11:35). Lỗi kẹt nick thuộc về logic workflow của riêng slot đó (xem Tầng 4).
- **Kết luận:** Chỉ kết luận lỗi phần cứng dài ngày khi TẤT CẢ các slot trên máy đều dừng cùng một mốc thời gian và máy không có bất kỳ log run nào thành công trong suốt thời gian đó. Cần thao tác vật lý (cắm lại cáp/bật nguồn), không phải lỗi runner.

### Tầng 2: Quy hoạch Cụm Máy / Trạng thái Dưỡng (Cohort / Host Status)
- **Kiểm tra:** Gom nhóm danh sách stale theo `host_id` (`kibe` vs `admin`) và phân bố số ngày kẹt.
- **Dấu hiệu:** Phần lớn nick stale (ví dụ >80%) tập trung ở cụm `admin` (Máy 201–280), đều dừng ở mức 1–2 clip và cùng kẹt đúng một mốc số ngày (ví dụ 22–23 ngày).
- **Kết luận:** Đây là các tài khoản thuộc nhóm test ban đầu của Farm Admin. Admin media độc lập với Kibe và hiện tại cụm Admin đang trong giai đoạn download & render video gốc (`last_render_stats.json` chưa đủ 45 video/folder, Tik 6–8 là 0%), chưa mở batch upload toàn cụm. Tài khoản đang ngâm dưỡng chờ nguồn video, hoàn toàn bình thường.

### Tầng 3: Lệch giữa Public Scraping Tracker vs File Sổ Cái Excel (Scrape Drift)
- **Kiểm tra:** Mở file `Tik<slot>.xlsx` tại dòng máy tương ứng, đọc cột `Video Đã Đăng` (cột 8) và so sánh với trường `video` trong database snapshot.
- **Dấu hiệu:**
  - Database snapshot ghi: `1 video`.
  - File Excel ghi: `3 video` hoặc `7 video` (trạng thái `OK`).
- **Kết luận:** Tracker cào dữ liệu qua web public TikTok (`__UNIVERSAL_DATA_FOR_REHYDRATION__`). Các clip mới đăng có thể đang bị xét duyệt, gắn cờ giới hạn hoặc đặt riêng tư nên không hiển thị công khai trên web. Thiết bị thực tế đã hoàn thành upload theo đúng sổ cái.

### Tầng 4: Phân lập Slot Đơn Lẻ trên Máy Kibe Đang Online (Single-Slot Isolation)
Khi một máy Kibe vật lý đang **ONLINE** nhưng chỉ có 1–2 nick/slot bị cảnh báo stale (ví dụ M13 Tik 1, M19 Tik 1, M21 Tik 7, M54 Tik 7, M80 Tik 5):
- **CẤM TUYỆT ĐỐI** kết luận máy bị kẹt hoặc runner sập.
- **Đối soát đa tầng qua 8 slot (Tik 1..Tik 8):**
  1. Kiểm tra toàn bộ 8 file `Tik<N>.xlsx` của máy: Nếu các slot khác (T2–T8) vẫn tăng số video đều đặn (ví dụ M13 T2 đạt 19v, T3 đạt 12v; M19 T2 đạt 16v, T3 đạt 15v; M54 T2, T4, T6 đăng đều) -> Máy và runner hoàn toàn khỏe mạnh.
  2. Phân loại nguyên nhân của slot đơn lẻ:
     - **Slot kết thúc chu kỳ thường quy (Tik 1 / Tik 2):** Tik 1 và Tik 2 không còn chạy upload tự động hàng ngày; các nick đạt ngưỡng trần giai đoạn (ví dụ M19 T1 đạt 27 clips) được giữ nguyên ngâm dưỡng.
     - **Lỗi nhận diện UI nút tạo video (`[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`):** App TikTok bị lag, popup che hoặc nút `[+]` ở giữa thanh điều hướng không nhận diện được -> run trả về `MANUAL_REVIEW` (ví dụ M21). Cần restart app / dismiss popup.
     - **Slot nick mới ngoài ca quay vòng hiện tại:** Nick mới tạo hoặc mới đăng 1–2 clip thử nghiệm (ví dụ M54 T7, M80 T5), đang chờ xếp lịch theo parity/cohort.
     - **Mạng VPN / Tun0 chập chờn (Network Flutter):** Kết nối ADB hoặc interface `tun0` bị timeout lúc khởi động (ví dụ M74).
  3. **Bẫy nhận diện thư mục Batch Runs:** Trong `D:/CodexRuntime/tiktok-video/batch-runs`, các thư mục dạng `batch_tik<N>_list_80_<timestamp>` nhưng `eligible_machines` chỉ có 2–4 máy là batch của watchdog avatar (`-ForceAvatarMachineList`), **không phải** batch upload video toàn farm. Đọc `report.json` và `execution.log` trong `D:/CodexRuntime/tiktok-video/runs/` để thấy chính xác ca upload gần nhất của từng serial.

---

## 4. Giải pháp Khắc phục Triệt để (L2 Emergency Surgery & Closeout Gate Remediation)
- **Patch Contract trong `audit_stale_upload_accounts.py`:**
  - Hoán đổi ưu tiên: đặt `DEFAULT_DB_PATH = r"D:/Taadaa/data/tiktok_tracker.db"` (runtime) và `FALLBACK_DB_PATH = r"D:/OneDrive/TaadaaData/tiktok_tracker.db"` (OneDrive backup).
  - Bổ sung cơ chế auto-mtime check: nếu file fallback có mtime mới hơn file default, tự động chuyển `real_db` sang file mới hơn để phòng ngừa trường hợp sync OneDrive được cập nhật tươi hơn.
  - **Telemetry & Safe Exception Handling (Reviewer Hard Invariant):** CẤM nuốt generic `Exception` âm thầm. Bắt buộc bắt cụ thể `OSError as exc` kèm log warning (`DB mtime check failed: %s`). Đồng thời log INFO `audit_upload_freshness selected_db=%s` và bổ sung trường `"selected_db": real_db` vào dict kết quả để telemetry minh bạch tại runtime.
- **Quy trình nghiệm thu Live Cronjob sau fix:**
  - Chạy `python -m py_compile D:/Taadaa/tools/audit_stale_upload_accounts.py` kiểm tra cú pháp < 5s.
  - Commit audit trail theo chuẩn `[L2-surgery]`.
  - Kích hoạt chạy ngay watchdog qua `cronjob(action="run", job_id="<job_id>")` để xác nhận `last_status: ok` và tin nhắn báo cáo gửi đúng đích Telegram mà không cần chờ đến lịch hẹn ngày hôm sau.
- **Quy chuẩn Vượt Closeout Gate (Reviewer Gate Remediation):**
  - Khi Reviewer chấm trượt (< 85) với finding thiếu telemetry / nuốt exception / thiếu test chứng minh nhánh fallback DB:
    1. Kích hoạt Sol High (`python D:/Taadaa/tools/sol_repair.py`) độc quyền tạo patch proposal O(1).
    2. Coordinator áp dụng diff Sol, nghiệm thu `git diff --numstat <= 30 dòng`, commit `[L2-surgery]`.
    3. Dispatch Worker bổ sung file test focused (`tests/test_audit_stale_upload_accounts.py`) mock 100% offline bao phủ 8 nhánh: basic metrics, drift mismatch, missing ID, fallback mtime, OSError handling, selected_db telemetry.
    4. Chạy lại `closeout_gate.py` với test suite focused mới để đạt APPROVED.

---

## 5. Quy Chuẩn Giải Mã & Phản Hồi Khi User Thắc Mắc Báo Cáo ("Chưa hiểu cái báo cáo này")
Khi User nhận báo cáo `daily-stale-upload-accounts-watchdog` trên Telegram và phản hồi chưa hiểu ý nghĩa:
1. **Giải mã 5 chỉ số cốt lõi bằng ngôn ngữ nghiệp vụ, không dùng thuật ngữ code thuần túy:**
   - **Tổng nick quản lý:** Toàn bộ slot nick được phân bổ trên 2 cụm máy Kibe (M1–M80) và Admin (M201–M280), mỗi máy 8 slot Tik.
   - **Đang đăng đều (≤ 7 ngày):** Dàn nick khỏe mạnh, bot vẫn đẩy clip và view tăng đều đặn theo chu kỳ ca.
   - **Nick mới warm-up (0 video):** Nick mới reg/mới tạo gần đây, đang trong giai đoạn ngâm dưỡng sinh (lướt feed thuần nuôi trust) chưa đăng clip đầu tiên.
   - **Cảnh báo trễ (7 – 14 ngày):** Nick đã có video nhưng tạm thời không tăng thêm trong 1–2 tuần gần nhất (trúng nhịp hoán vị chu kỳ nuôi 4 ngày N1–N4, hoặc kho video nguồn của slot đó vừa hết đang chờ batch render).
   - **Nguy cơ đóng băng (> 14 ngày):** Nhóm bị đọng lâu nhất (> 20 ngày). BẮT BUỘC phân định rõ tỷ trọng:
     - *Nhóm Admin (~75–80%):* Đăng thử 1–2 clip rồi tạm dừng upload để tập trung render kho video gốc, nick đang ngâm dưỡng chờ nguồn, không phải lỗi.
     - *Nhóm Kibe (~20–25%):* Do phần cứng rớt USB (M10, M30), kẹt draft trap trong app TikTok, hoặc vướng lỗi script upload đã/đang được khắc phục.
2. **Disambiguation Guard (Phòng ngừa lệch ngữ cảnh):**
   - Luôn kèm lời nhắc: nếu User đang nhìn báo cáo khác (Sổ tay bệnh án Follow trên Dashboard :1905, Báo cáo Rolling Rename đổi tên, hoặc Farm Alert lỗi script upload), mời User gửi tên báo cáo hoặc ảnh chụp màn hình để giải mã đúng trọng tâm.
3. **Kích hoạt Advisor Sol:** Tuân thủ `advisor-dual-answer-orchestration` để đính kèm góc nhìn đánh giá độc lập từ Advisor Sol ở cuối phản hồi.
