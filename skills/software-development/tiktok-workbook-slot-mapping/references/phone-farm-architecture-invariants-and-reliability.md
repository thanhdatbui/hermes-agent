# Phone Farm Architecture & Reliability Playbook: Root Cause Analysis & System Invariants

## Bối cảnh & Hiện tượng (2026-09-17)
Trong quá trình vận hành farm 80 máy / ~600 tài khoản TikTok, hệ thống liên tục phát sinh các lỗi tái diễn:
1. **Nick bị văng khỏi Switcher 8 nick trên máy thật**: Nick chính chủ `duongkien1202` (Máy 1) bị biến mất khỏi Switcher 8 nick, thay vào đó là nick mồ côi `ahmetsguthe17`. Nguyên nhân: Script reg/bù nick chạy mù, nhồi nick mới vào mà không đối soát giới hạn 8 nick trên app thật, khiến TikTok tự động đẩy nick cũ ra vùng cache Fast Login.
2. **Gán trùng Video Gốc trong Workbook (`Tik3.xlsx`)**: 5 cặp máy (M64-M65, M66-M70, M67-M71, M68-M72, M69-M73) bị trỏ chung vào cùng 1 thư mục video gốc do con người / script thao tác copy dòng thủ công trên Excel mà không có Schema Validation.
3. **Nghi vấn trùng kênh nguồn trong Downloader (`download_by_niche.py`)**: Pipeline tải video cũ trong tháng 8 từng trộn nhiều kênh vào 1 folder khi kênh chính thiếu video, hoặc chia 1 kênh cho nhiều folder khác nhau.

---

## 1. Phân tích Nguyên nhân Gốc rễ (System & Reliability Engineering)

### Căn bệnh Triple-Write & Write-Without-Read
Hệ thống tồn tại 3 nguồn dữ liệu song song nhưng thiếu cơ chế đồng bộ (Synchronization) và đối soát 2 chiều:
```
[Excel Files (Tik1..8, Safe)] <--- KHÔNG SYNC ---> [SQLite state.db] <--- KHÔNG SYNC ---> [Thiết bị thật (Phone App)]
            ↑                                               ↑                                           ↑
        Con người                                        Scripts                                    TikTok App
         gõ tay                                          ghi vào                                   tự quản lý
```
- **Write-Without-Read Anti-Pattern**: Scripts ghi đè trạng thái vào Excel/DB mà không đọc lại trạng thái thực tế từ thiết bị thật.
- **Excel làm Control Plane**: Excel chỉ là công cụ tính toán và hiển thị (View), thiếu hoàn toàn các tính năng database cốt lõi:
  + Không có `UNIQUE` constraint (cho phép duplicate key vật lý: trùng slot, trùng video gốc, trùng kênh).
  + Không có Foreign Key (nick không bị ràng buộc bắt buộc phải thuộc về 1 máy thật).
  + Không có Atomic Transactions (thất bại giữa chừng để lại dữ liệu dở dang / corrupted state).
  + Concurrency kém (dễ dính Windows file-lock `PermissionError` trên OneDrive).

---

## 2. Các Quy tắc Bất biến (System Invariants) bắt buộc Enforce

Mọi script trong chuỗi tự động hóa (Reg, Login, Feed, Render, Upload) BẮT BUỘC phải cài đặt các Guard Clauses chặn đứng lỗi (Fail-Loud), không log warning rồi tiếp tục:

### I-1: Giới hạn Slot Vật lý (Physical Capacity Invariant)
- **Quy tắc**: Trước khi thực hiện bất kỳ hành động Reg nick mới hoặc Login nick vào thiết bị, script BẮT BUỘC đọc trực tiếp Switcher qua ATX-Agent / UI Automator.
- **Điều kiện**: Nếu `len(current_accounts) >= 8` ➔ **DỪNG NGAY LẬP TỨC (ABORT)** với mã lỗi `MACHINE_FULL_8_ACCOUNTS`. Tuyệt đối CẤM bấm thêm tài khoản khi máy đã full 8 nick.

### I-2: Độc bản Video Gốc (Unique Video Source Invariant)
- **Quy tắc**: Mỗi folder video gốc trong `D:\video goc` chỉ được gán cho duy nhất 1 nick trên toàn farm.
- **Công thức bất biến cho Tik N**:
  $$\text{Video Gốc} = (N - 1) \times 80 + \text{Máy}$$
- **Kiểm tra trước khi lưu**: Script kiểm tra toàn bộ bảng `Tik1..Tik8.xlsx`, nếu phát hiện `COUNT(video_goc) > 1` ➔ Raise `AssertionError` và chặn ghi file.

### I-3: Độc bản Kênh Nguồn (1 Folder = 1 Kênh duy nhất)
- **Quy tắc**: Một folder video gốc CHỈ ĐƯỢC tải từ duy nhất 1 kênh nguồn (`source_channel`).
- **Chặn đứng Downloader**: Nếu một kênh không đủ `min_videos`, script phải đánh dấu `insufficient_pool` và chuyển sang kênh khác, TUYỆT ĐỐI CẤM cào thêm kênh thứ 2, thứ 3 nhồi vào cùng 1 folder làm loãng nhận diện và lẫn lộn avatar.

### I-4: Bảo toàn Dòng Vật lý trong Master Workbook
- **Quy tắc**: Master Workbook `taikhoan_dat_v2_updated .xlsx` có cấu trúc cứng 80 máy × 8 hàng (640 dòng).
- Dòng vật lý của Máy $m$, Slot $k$ luôn cố định:
  $$\text{target\_row} = 1 + (m - 1) \times 8 + k$$
- TUYỆT ĐỐI CẤM append dòng mới xuống đáy sheet (dòng > 640).
- Cột B (`STT_Tik` / `Folder Video`) là số toàn cục `(m - 1) * 8 + k`, TUYỆT ĐỐI KHÔNG so sánh hoặc gán đè thành số slot $k$.

---

## 3. Lộ trình Cải tổ Kiến trúc Bền vững (Modernization Roadmap)

1. **Giai đoạn 1 (Ngay lập tức - Guard Clauses)**:
   - Chèn các hàm assert kiểm tra I-1, I-2, I-3 vào đầu các script `social_reg_v1.py`, `reconcile_tiktok_accounts.py`, `download_by_niche.py`.
2. **Giai đoạn 2 (Reconciliation Watchdog 2 chiều)**:
   - Xây dựng worker chạy định kỳ (mỗi 30-60 phút): Đọc danh sách tài khoản thực tế trên Switcher 80 máy thật qua ADB/ATX và so khớp với `taikhoan_run_safe.xlsx`. Phát hiện lệch nick/mất nick phát alert Telegram ngay.
3. **Giai đoạn 3 (Database làm Single Source of Truth)**:
   - Di chuyển toàn bộ cấu hình sang SQLite (`taadaa_farm.db`) với các ràng buộc cứng:
     ```sql
     UNIQUE(device_id, slot_position)
     UNIQUE(assigned_folder)
     UNIQUE(source_channel)
     ```
   - Các file Excel (`Tik1..8`, `taikhoan_run_safe`) chuyển thành **Read-Only Views** (chỉ xuất ra để xem/báo cáo), toàn bộ luồng ghi phải qua Database API.
