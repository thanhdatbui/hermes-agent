# Quy Chuẩn Render Đơn Luồng, Cào 20 Worker & Chống Trùng Nguồn Global Ledger

## 1. Nguyên Tắc Phân Bổ Video Dư Của Kênh (45 là Min, Không Tạo Folder Rác)
- **Quy tắc cốt lõi:** Khi tải được số lượng video lớn từ cùng một kênh (ví dụ 70-100 clip), **CẤM** tự ý tạo thêm các folder phụ lắt nhắt (như `*_goi_dau`, `*_dot2`).
- **Thực thi:** Đẩy toàn bộ video vào thẳng folder chính của nick/kênh đó (`D:\video goc\<folder>`).
- **Nguyên lý:** 45 clip là ngưỡng TỐI THIỂU (MIN) để đủ điều kiện nuôi acc 5 tháng, **KHÔNG PHẢI NGƯỠNG TỐI ĐA (MAX)**. Càng nhiều clip trong folder (60-80 clip) càng giúp nick được nuôi liên tục 8-10 tháng mà không phải can thiệp nạp bù.
- Phần dư từ các kênh khác nhau đổ vào `curated_pool` chỉ dùng khi là bể gộp chung cho các nick đa kênh, không dùng để chia nhỏ một kênh duy nhất.

---

## 2. Kỷ Luật Render Đơn Luồng (--parallel 1)
- **Quy định:** Mọi batch render (`random_batch_render.py` hoặc `render_kibe_under45.py`) trên cả Farm Kibe và Farm Admin **BẮT BUỘC đặt `--parallel 1`**.
- **Lý do:** Render video bằng ffmpeg với filter complex (rotate, scale, eq, noise, unsharp, loudnorm) chiếm tải CPU cực lớn (1 ffmpeg có thể ăn 150-300% CPU). Nếu để `--parallel 2` hoặc cao hơn, máy sẽ bị giật lag, nghẽn I/O ổ đĩa, ảnh hưởng trực tiếp đến các tiến trình farm khác (ADB, GPM, nuôi acc).
- **Cờ bắt buộc khi resume:** `--resume-verify-existing` để ffprobe kiểm tra và bỏ qua các file thành phẩm hợp lệ, chỉ render các file thiếu/hỏng.

---

## 3. Worker Cào Video (--parallel 20) & Cơ Chế Global Ledger
- **Cấu hình download:** Cào video theo niche chạy với `--parallel 20` để vét kho nhanh chóng.
- **Cơ chế chống trùng nguồn giữa Kibe và Admin:**
  - Định vị tại: `D:\OneDrive\SharedData\tiktok-video\global-ledger` (thư mục đồng bộ real-time).
  - Trước khi cào bất kỳ kênh nào, script bắt buộc gọi `claim_source(directory, machine_id, source_url, folder)`:
    - Nếu kênh đã được Kibe claim trong `Kibe.jsonl` $\rightarrow$ Admin sẽ thấy và tự động bỏ qua.
    - Nếu kênh đã được Admin claim trong `Admin.jsonl` $\rightarrow$ Kibe sẽ bỏ qua.
  - Triệt tiêu 100% rủi ro trùng lặp video và source giữa 2 dàn máy.

---

## 4. Bẫy Kỹ Thuật (Pitfalls & Recovery)
1. **SQLite WAL Disk I/O Error khi đa luồng (20 worker):**
   - Triệu chứng: `sqlite3.OperationalError: disk I/O error` tại `PRAGMA journal_mode = WAL`.
   - Khắc phục: Hàm `connect_state` trong `pipeline_common.py` phải bọc vòng lặp retry 5 lần (backoff 1s) và bắt `OperationalError` an toàn khi set WAL.
2. **Strict 80 Niches trong `niches_pool.txt`:**
   - `pipeline_common.py` kiểm tra cứng `len(niches) == 80`. CẤM append thêm niche dòng 81 (như thừa dòng `gaixinh`), nếu vi phạm script sẽ crash ngay lập tức (`ValueError: niches_pool phai co 80 niche`).
3. **Quản lý tiến trình nền trên Windows qua SSH:**
   - Lệnh `Get-Process` trên PowerShell từ xa không trả về trường `CommandLine` đầy đủ.
   - Để tìm và dừng chính xác tiến trình Python/ffmpeg render: Bắt buộc dùng `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '...' }` để lấy ProcessId và dừng triệt để, tránh sót tiến trình ngầm.
