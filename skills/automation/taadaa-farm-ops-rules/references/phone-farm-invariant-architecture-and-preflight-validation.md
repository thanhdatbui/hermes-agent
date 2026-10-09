# Ngăn Chặn Lỗi Lặp Lại & Thiết Kế Kiến Trúc Hybrid Phone Farm (Pragmatic Consensus)

## 1. Bối cảnh & Hiện tượng lỗi gốc rễ
Trong quá trình vận hành Phone Farm (80 máy, ~600 tài khoản), hệ thống thường xuyên gặp các lỗi tích tụ lặp lại:
1. **Write-without-read (Ghi mù không đối soát máy thật)**:
   - Script reg nick hoặc bù slot chỉ kiểm tra file Excel rồi cắm đầu login/reg nick mới trên thiết bị.
   - TikTok có trần cứng 8 tài khoản/thiết bị. Nếu máy đã đủ 8 nick, việc nhồi thêm nick thứ 9 sẽ khiến TikTok tự động đẩy nick cũ ra khỏi Switcher và lưu vào bộ nhớ cache Fast Login, trong khi nick mồ côi (parasite) vẫn chiếm chỗ.
   - Hậu quả: Excel ghi nhận một đằng, thiết bị máy thật chạy một nẻo, nick chính chủ biến mất khỏi ca chạy.
2. **Triple-write & Data Corruption**:
   - Dữ liệu bị ghi phân tán ở 3 nơi không có cơ chế transaction: File Excel, SQLite local state.db, và bộ nhớ app TikTok trên máy thật.
   - Excel không có schema validation hay ràng buộc UNIQUE cứng, dẫn đến việc người kéo chuột copy/paste hoặc script chạy lỗi ghi đè dữ liệu (ví dụ: gõ nhầm mật khẩu vào ô Folder Video, hoặc kéo đè Video Gốc khiến 5 cặp máy bị trùng content).
3. **Download trộn kênh (Mixed Channels) & bypass cờ chặn trùng**:
   - Downloader kiểm tra `COUNT(*) FROM folders WHERE source_channel=?` để chặn trùng kênh. Tuy nhiên, khi 1 folder cào nhiều kênh hoặc khi `folders.source_channel` bị để `NULL`, bộ đếm trả về 0 khiến downloader tiếp tục cấp kênh đó cho folder khác, gây trùng lặp avatar và nội dung nhận diện.

---

## 2. Các Quy Tắc Bất Biến (System Invariants) Bắt Buộc Enforce
Bất kể script nào can thiệp vào tài khoản, video, hoặc Excel đều phải tuân thủ 5 chốt chặn bất biến (fail-loud ngay nếu vi phạm):

1. **Invariant 1 (Trần cứng 8 nick/máy)**:
   `COUNT(slots) <= 8` trên mọi máy. Tuyệt đối không thực hiện thêm tài khoản nếu máy thật đang có $\ge 8$ nick trên Switcher.
2. **Invariant 2 (Độc bản Slot tài khoản)**:
   `UNIQUE(device_id, slot_position)` và `UNIQUE(account_id)` trên toàn bộ hệ thống Excel và thiết bị thật. Một tài khoản chỉ được gán duy nhất cho 1 máy, 1 slot.
3. **Invariant 3 (Folder Video độc bản & chuẩn công thức)**:
   `FolderVideo` render thành phẩm phải độc bản toàn farm, tuân theo công thức:
   $$\text{FolderVideo} = (\text{Máy} - 1) \times 8 + \text{Slot}$$
4. **Invariant 4 (Video Gốc độc bản & chuẩn công thức)**:
   Trong cùng 1 ca chạy (cùng file `Tik{slot}.xlsx`), không có 2 máy nào dùng chung một thư mục Video Gốc:
   $$\text{VideoGoc} = (\text{Slot} - 1) \times 80 + \text{Máy}$$
5. **Invariant 5 (1 Folder Video Gốc = 1 Kênh duy nhất)**:
   Một thư mục video gốc chỉ được phép chứa video từ đúng 1 kênh nguồn (source_channel), không nhồi nhiều kênh vào cùng một folder làm lẫn lộn nhận diện kênh.

---

## 3. Kiến Trúc Lai Thực Chiến (The Pragmatic Hybrid Design)
Đồng thuận kỹ thuật giữa System Engineering và Operation thực tế:

```
┌─────────────────────────────────────────────────────────────┐
│                    TAADAA FARM ARCHITECTURE                 │
│                   (Pragmatic Hybrid v2.0)                   │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  DATA LAYER  │ STATE LAYER  │ FEEDBACK     │ FAIL-SAFE      │
│              │              │ LOOP LAYER   │ LAYER          │
│  Excel +     │  Local JSONL │  JIT         │  5 Invariant   │
│  Preflight   │  (per-machine│  Reconcile   │  Guards        │
│  Validator   │  audit log)  │  (ATX/OCR    │  (pre-action   │
│              │  tránh lock  │  before act) │  checks)       │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

1. **Excel làm Control Plane có Preflight Validator bảo vệ**:
   - Vẫn giữ Excel để người vận hành kiểm tra, chỉnh sửa trực quan.
   - **BẮT BUỘC**: Chạy `python D:/Taadaa/tools/excel_preflight_validator.py` kiểm tra toàn bộ `Tik1..Tik8.xlsx` và `taikhoan_run_safe.xlsx` trước khi bấm chạy bất kỳ ca nào. Nếu có lỗi FAIL (lệch công thức, trùng nick, sai slot), validator sẽ chặn đứng pipeline ngay lập tức.
2. **Just-In-Time (JIT) Reconciliation thay vì Background Scan liên tục**:
   - Không chạy cron quét 80 máy liên tục làm nóng thiết bị, chai pin và nghẽn ADB.
   - Chỉ kích hoạt đọc Switcher (qua ATX-Agent dump XML hoặc WinRT OCR) **ngay trước và sau** hành động can thiệp:
     + *Trước khi login/bù nick*: Đọc Switcher máy thật, nếu đang có 8 nick $\rightarrow$ Chặn lại, yêu cầu logout nick mồ côi trước khi nạp.
     + *Sau khi login/bù nick*: Đọc màn hình Profile chính chủ để xác nhận nick đã vào máy thành công.
3. **Local JSONL Audit Log tránh lock file đa máy**:
   - Ghi nhận lịch sử can thiệp nick vào file log JSONL cục bộ trên từng máy host (`audit_log.jsonl`).
   - Tuyệt đối không dùng SQLite chia sẻ trực tiếp qua OneDrive giữa các máy Kibe và Admin để tránh lỗi `database is locked` làm crash pipeline.
