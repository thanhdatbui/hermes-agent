---
name: tiktok-workbook-slot-mapping
description: "Quy tắc mapping Tik1/Tik2/tik3 workbook ↔ taikhoan_dat_v2 (REG) + hashtag theo folder nguồn + render random. Dùng khi đồng bộ, sửa, tạo file Tik, điền hashtag, render."
version: 1.0.0
metadata:
  hermes:
    tags: [tiktok, workbook, mapping, xlsx, render, hashtag]
    category: software-development
---

# TikTok Workbook Slot Mapping (Tik1/Tik2/tik3 ↔ REG)

## 🛑 STOP GATE
Tuân thủ skill `taadaa-farm-ops-rules`: screencap nghiệm thu `MEDIA:<path>` trước teardown.

## Tài liệu tham khảo bổ trợ:
- `references/tiktok-id-validation-and-sync-drift.md`: Kỷ luật validate ID TikTok regex, cấm blacklist substring ("in") drop nhầm nick có dấu chấm (`vo.my.hanh94`), audit 1:1 Master DAT ↔ Tik1-Tik8.
- `references/niche-hashtag-sync-and-drift-reconciliation.md`: Đối soát & sync 3 tầng khi lệch niche/hashtag.
- `references/backfill-excel-drift-investigation.md`: Đối soát & backfill khi alert báo Máy đủ 8 acc, dọn tàn dư ký sinh. Cảnh báo bẫy ngộ nhận "đã hết ký sinh" khi chỉ nhìn Excel PASS, và bẫy substring blacklist trong `sync-tik-workbooks.py` vô tình xóa nhầm nick thật khiến nick dừng đăng video dài ngày. kèm danh mục chuẩn 14 cặp nick bốc trùng mail lịch sử toàn farm và kỹ thuật cuộn đáy Switcher.
- `references/farm-admin-video-download-and-deduplication.md`: Cào video Admin, xử lý 0MB đĩa, niche Douyin/ASMR, Parallel=2, swap dọn 2 đầu, SSH detached.
- `references/account-video-investigation-and-folder-swap.md`: Điều tra & đổi nguồn video, dọn 2 đầu, pipeline swap_single_folder_pipeline.py.
- `references/safe-workbook-schema-ngay-tao-projection.md`: Mở rộng Safe Workbook cột "Ngày Tạo", date parsing `_parse_date_iso`, dynamic header verify.
- `references/excel-process-lock-and-onedrive-reversion-triage.md`: Xử lý Excel lock (`PermissionError`), kiểm tra ID trực tiếp, atomic write và OneDrive sync.
- `references/excel-sync-performance-and-serial-invariants.md`: Chống treo openpyxl read_only (`iter_rows`), invariant serial phần cứng 8 slot và gỡ lỗi duplicate accounts.
- `references/ensure-row-accounts-stale-isolation-and-telemetry.md`: Chống nuốt stale artifact (`batch_start_time`), guard Telegram test env.
- `references/tiktok-dashboard-machine-mapping-and-sync.md`: Xử lý nick thiếu số máy trên Dashboard (port 1905) và đồng bộ SQLite `farm_account_info`.
- `references/safe-workbook-slot-mapping-modulo8.md`: Quy tắc mapping 8 slot theo Folder Video modulo 8, tránh dồn ép slot trên Admin Remote cluster.
- `references/resolving-duplicate-accounts-preflight.md`: Xử lý lỗi duplicate account giữa Tik*.xlsx và taikhoan_dat_v2, PASS preflight validator.
- `references/excel-preflight-validator-conflict-resolution.md`: Tự động xử lý xung đột preflight validator, Coordinator chủ động truy vết DB và patch.

## Bối cảnh & nguồn chuẩn (2026-08-11, đã xác nhận với user)



- **Workbook trên PC kibe** = `D:\OneDrive\TaadaaData\kibe\` (toàn bộ workbook Tik/REG của PC này); không dùng đường dẫn cũ `D:\OneDrive\Tiktok` hoặc `D:\OneDrive\Tiktok_Reg`. Live config m74 dùng `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`. Sheet REG/master là `Tài Khoản`.

- Folder kibe chứa: `Tik1.xlsx`, `Tik2.xlsx` (đã copy bổ sung 2026-08-12), `tik3.xlsx` (CHỮ THƯỜNG), `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `gmail_clean_v2.xlsx`, `PROXYgandienthoai.xlsx`.

- **Muốn biết file nào còn trỏ đường cũ sau khi dời** → xem `references/path-migration-audit-20260812.md` (ma trận 7 repo + kỹ thuật quét rg tránh timeout + nguyên tắc git-shared giữ canonical cũ fail-closed).

- REG là **master/nguồn chuẩn**. Các file Tik (Tik1/Tik2/tik3) là bảng con 1 dòng/máy.

- **Đồng bộ MỘT CHIỀU**: master → Tik. File Tik KHÔNG đẩy dữ liệu ngược vào REG.

- **QUY TẮC ĐỒNG BỘ 1-CHIỀU ID & SERIAL TỪ `taikhoan_dat_v2` SANG `Tik1..Tik6.xlsx` (`sync-tik-workbooks.py`, 2026-08-26 - cập nhật 2026-09-02)**:
  1. **Tự động hóa qua Cron (mỗi 5 phút)**: Tích hợp vào `hermes_taikhoan_sync_cron.py` để khi chuỗi Reg nạp nick mới hoặc user xóa nick die/ban trong `taikhoan_dat_v2_updated .xlsx`, ID TikTok và Serial thiết bị sẽ tự động được đồng bộ và chuẩn hóa sang file Tik tương ứng (`scripts/sync-tik-workbooks.py`).
  2. **Mapping Slot & Khóa Cứng Serial Chuẩn**:
     - Slot 1 (`(m-1)*8 + 1`) ➔ `Tik1.xlsx` (cột ID)
     - Slot 2 (`(m-1)*8 + 2`) ➔ `Tik2.xlsx` (cột ID)
     - Slot 3 (`(m-1)*8 + 3`) ➔ `tik3.xlsx` (cột ID)
     - Slot 4 (`(m-1)*8 + 4`) ➔ `Tik4.xlsx` (cột ID)
     - Slot 5 (`(m-1)*8 + 5`) ➔ `Tik5.xlsx` (cột ID)
     - Slot 6 (`(m-1)*8 + 6`) ➔ `Tik6.xlsx` (cột ID)
     - **Tự động đối soát Cột B (`device ID`)**: Script tổng hợp `canonical_serials` từ `Tik1.xlsx` và `EXTRA_MACHINES` (khóa cứng serial cho máy 75..80). Mọi file `TikN.xlsx` bị lệch/swap serial phần cứng sẽ được tự động sửa về đúng serial chuẩn, ngăn ngừa triệt để lỗi upload tra cứu nhầm nick của máy khác (`[ACCOUNT_SWITCHER_FAILED] ACCOUNT_MISSING`).
  3. **Bảo toàn tuyệt đối cột tiến độ**: Cột `Folder Video` và cột `Video Đã Đăng` của các file TikN BẮT BUỘC giữ nguyên 100%, tuyệt đối CẤM reset hay ghi đè.
  4. **Đồng bộ 1-chiều 2 chiều Nick Mới & Xóa Nick Die/Ban (Master là chân lý)**:
     - **Có nick mới trong DAT**: Cập nhật nick mới sang `TikN.xlsx` (cột ID) và set `Kiểm Tra Dữ Liệu = OK`.
     - **DAT trống / Xóa nick die/ban**: BẮT BUỘC xóa trắng ô ID (`cell.value = None`, `cell.hyperlink = None`) trong `TikN.xlsx` và chuyển `Kiểm Tra Dữ Liệu = MISSING_ID`. Tuyệt đối không giữ lại username cũ khi master đã bị xóa.
     - **Dọn rác/placeholder**: Tự động dọn sạch placeholder (`http://`, `https://`, `ghjfghj`, `none`, `null`). **CẤM hardcode blacklist username thật/substrings (như `vo.my`, `ngomai.ly`) vào hàm check hợp lệ `is_valid_tiktok_id`**, vì sẽ làm xóa nhầm username hợp lệ của nick thật (như `ngomai.ly` M22, `vo.my.hanh94` M69) thành `MISSING_ID` và chặn upload. Regex username chuẩn: `^[a-zA-Z0-9_.]{2,24}$` kết hợp loại trừ link `http` và dấu chấm ở đầu/cuối.
  5. **PITFALL openpyxl Clear Cell**: Trong openpyxl, gọi `ws.cell(r, c, None)` KHÔNG xóa giá trị hiện có nếu ô đã có text! Bắt buộc phải gán `cell = ws.cell(r, c); cell.value = None; cell.hyperlink = None` trực tiếp để xóa triệt để cả text lẫn hyperlink object của Excel.
  6. **Tách biệt Lock Timeout cho Shift Upload Ledger**: Quá trình kiểm tra và đặt chỗ upload theo ca (`_ShiftUploadLedger.claim_reservation`) sử dụng `lock_timeout` riêng biệt (180s kèm jitter backoff) thay vì bind chung vào deadline toàn phiên (`hard_deadline_monotonic`) để chống timeout hàng loạt (`shift_upload_lock_timeout_fail_closed`) khi 80 máy đồng loạt hoàn tất lướt feed.

- **QUY TẮC XỬ LÝ LỆCH NICK / THIẾU NICK TRÊN MÁY (User Rule 2026-09-01, đính chính 2026-09-02)**:
  - **Trường hợp máy thiếu nick (< 6 nick)**: Khi script chạy nuôi/feed gặp lỗi `account-switcher-missing-expected` (không thấy tài khoản mong đợi trên Account Switcher) và máy chưa đủ 6 nick:
    + **BẮT BUỘC tự động kích hoạt `tiktok-log-in` (`reconcile_tiktok_accounts.py`)** để đăng nhập nick thiếu vào thiết bị.
    + **TUYỆT ĐỐI CẤM tự ý đôn slot hay chuyển nick thiếu sang máy khác** khi máy chưa full 6 nick.
  - **Trường hợp máy ĐÃ FULL ĐỦ 6 NICK nhưng dính nick thừa ở slot phụ (Slot 7/8)**:
    + Chỉ áp dụng swap/re-map trên Excel khi máy thực tế đã đăng nhập full 6 nick mà trong đó có nick hợp lệ ở slot phụ (7/8) và thiếu 1 nick ở slot chính (1..6). Lúc này mới đôn nick phụ lên slot chính và chuyển nick thiếu sang máy trống để tránh logout/login churn.
  - **Lưu ý openpyxl Clear Cell**: Gán trực tiếp `cell.value = None` cho từng ô thay vì truyền `value=None` qua `cell()`.

- **QUY TẮC GMAIL_CLEAN_V2 & CHECK-LIVE (user rule 2026-08-22, bổ sung 2026-09-01)**:
  1. `gmail_clean_v2.xlsx` là **kho mail live** của farm (KHÔNG phải hàng đợi tạm để xóa sau khi reg). Email reg xong VẪN GIỮ TRONG KHO.
  2. **Bảo toàn Read-Only tuyệt đối khi Sync**: Mọi script quét/sync từ `gmail_clean_v2.xlsx` sang các file tổng (như `gmail_live_tong.txt`) BẮT BUỘC mở ở chế độ `read_only=True`, tuyệt đối KHÔNG can thiệp hay sửa đổi/ghi đè file gốc `gmail_clean_v2.xlsx`.
  3. **Quy tắc File Tổng (Chỉ giữ LIVE, không lưu DIE)**: Danh sách Gmail tổng hợp nhất lưu tại `D:\OneDrive\TaadaaData\kibe\gmail_live_tong.txt` CHỈ lưu trữ các tài khoản Gmail LIVE. Tuyệt đối KHÔNG duy trì hay lưu trữ file `gmail_die_tong.txt` (mail die thì xóa bỏ, không giữ).
  4. **Cơ chế Tự động Đồng bộ (Sync Watchdog)**: Sử dụng Cron job (`sync-gmail-clean-v2-to-tong`, script `sync_gmail_clean_v2_to_tong.py`) theo dõi SHA-256 hash của `gmail_clean_v2.xlsx` để tự động bốc và bổ sung Gmail mới vào `gmail_live_tong.txt` một cách im lặng.
  5. Khi chạy check-live Gmail:
     - Nếu mail die/mất khỏi máy VÀ **chưa có ID TikTok** trong `taikhoan_dat_v2` ➔ **Xóa khỏi `gmail_clean_v2.xlsx`** (hoặc cách ly) để tool detect không bốc lại làm target rác.
     - Nếu mail die/mất khỏi máy nhưng **ĐÃ CÓ ID TikTok** trong `taikhoan_dat_v2` ➔ **BẮT BUỘC GIỮ LẠI**, không được xóa vì còn phục vụ quản lý/nuôi acc TikTok đó.
  6. **Quy tắc bảo toàn ID ↔ Mail trong `taikhoan_dat_v2`**: ID TikTok và Mail gốc đăng ký BẮT BUỘC phải nằm cùng 1 hàng (Cột C `ID` ↔ Cột F `GMAIL`). CẤM ghi đè Hotmail hoặc mail khác vào hàng của Gmail gốc gây data drift khiến detector tưởng Gmail chưa reg rồi tiếp tục bốc lại làm target.
  7. **Quy tắc xóa hàng trùng ID TikTok do lỗi reg (2026-08-27, cập nhật 2026-09-01)**: Khi dọn các hàng bị trùng ID do reg nhầm profile cũ:
     - Giữ lại hàng có đầy đủ thông tin chuẩn (có Pass TikTok, 2FA, đúng Mail gốc).
     - **Bẫy trùng ID do HOA / thường (Case Insensitivity)**: Lọc trùng handle bắt buộc dùng `.strip().lower()` (ví dụ `Samnga2403` vs `samnga2403`). Bộ lọc Excel mặc định phân biệt chữ hoa/thường dễ làm sót hàng trùng.
     - Với hàng trùng bị loại bỏ: **Xóa sạch toàn bộ thông tin tài khoản (Cột 3..9: ID, PASS, 2FA, GMAIL, PASS MAIL, DOB, CREATED)**. BẮT BUỘC giữ nguyên Cột 1 (`Máy`), Cột 2 (`Folder Video`), Cột 10 (`device ID`) để bảo toàn cấu trúc chuẩn 8 slot/máy. Sau khi xóa, đồng bộ ngay sang `taikhoan_run_safe.xlsx` và `TikN.xlsx` (chuyển sang `MISSING_ID` chờ cấp nick mới). Info mail gốc vẫn có trong `gmail_clean_v2.xlsx` để phục vụ reg lại.

- REG hiện có **80 máy × 8 dòng** (640 dòng). Mỗi máy 8 slot account; slot 7-8 trống (2 dòng đã bị xóa hồi 14/07, đã thêm lại 2026-08-11 với folder +7,+8, device ID copy từ máy).
- **LƯU Ý LỆCH CẤU TRÚC 6 HÀNG VS 8 HÀNG Ở DẢI MÁY MỚI (M76..M79, 2026-09-13)**:
  - Do lịch sử nhập liệu / mở rộng, cụm máy 76..79 từng chỉ có 6 hàng vật lý trong `taikhoan_dat_v2_updated .xlsx` (khiến toàn bộ sheet chỉ có 633 hàng thay vì 640 hàng, Máy 80 bị kéo lên từ hàng 626).
  - Quy chuẩn bắt buộc khi nới rộng về 8 hàng/máy:
    1. Mỗi máy M76..M79 phải đủ 8 dòng vật lý. Folder video cho Slot 7 là `(m-1)*8 + 7`, Slot 8 là `(m-1)*8 + 8`.
    2. Đẩy Máy 80 về đúng vị trí vật lý chuẩn (hàng 634..641, Slot 1..8 tương ứng Folder 633..640).
    3. Serial phần cứng copy đồng nhất từ các slot trước của chính máy đó (`9885b64d56305a3731` cho M76, `ce05160595e7953b04` cho M77, `ce0916090a9d320a01` cho M78, `ce0516059d279f3e03` cho M79).
    4. Sau khi nới rộng và nạp nick mới (VD: Row 7 của M77 và M78), chạy ngay `sync-safe-workbook.py` (với token `TAADAA_ALLOW_OVERWRITE_TOKEN`) để `taikhoan_run_safe.xlsx` cập nhật đúng 640 dòng (80 máy x 8 hàng).

- **BẪY TRA CỨU FARM THIẾU TIK7 & TIK8 (User Invariant 2026-09-13: "mở rộng farm ra tik 7 tik8 r mà kiểm tra chỗ nào thiếu dữ liệu mà k biết")**:
  - **Triệu chứng & Sai lầm**: Khi kiểm tra thiếu dữ liệu hoặc quét acc/avatar, chỉ duyệt các file `Tik*.xlsx` hiện có trên đĩa (`Tik1..Tik6.xlsx`), từ đó ngộ nhận rằng farm chỉ có 6 Tik và bỏ sót toàn bộ dữ liệu của Slot 7 & Slot 8.
  - **Bản chất thực tế**: Master `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx` đã kích hoạt đủ 8 slot (Slot 7 đã có 36 nick, Slot 8 đã có 4 nick). Kho render `run_kibe_slot7_slot8_render.ps1` và video gốc `481..640` đã hoạt động.
  - **Quy tắc bắt buộc**:
    1. Kiểm tra tồn tại/trạng thái farm BẮT BUỘC đọc từ Master `taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`) và `taikhoan_run_safe.xlsx` qua công thức `(idx % 8) + 1` cho đủ cả 8 Slot.
    2. Không được lấy danh sách file `Tik1..Tik6.xlsx` làm chặn trên của farm. Khi farm mở rộng Slot 7 & 8, phải đồng bộ khởi tạo `Tik7.xlsx` và `Tik8.xlsx` và cập nhật `TIK_SLOT_MAP` trong `sync-tik-workbooks.py` / `sync-safe-workbook.py`.


- **QUY CHUẨN 480 SLOT TOÀN FARM & BỎ QUA DÒNG DƯ TRONG DAT (User Rule 2026-09-03)**:
  1. Farm Kibe chuẩn đúng **80 máy x 6 slot = 480 slot** (tương ứng `taikhoan_run_safe.xlsx` và 6 file `Tik1..Tik6.xlsx`).
  2. Mọi dòng slot dư (slot 7-8 hoặc ngoài 480 dòng) trong `taikhoan_dat_v2_updated .xlsx` **hoàn toàn bỏ qua, không tính vào số lượng thiếu**.
  3. Quy tắc đếm nick thiếu: Chỉ đếm các ô ID trống trong phạm vi 480 slot của `taikhoan_run_safe.xlsx` (hoặc slot 1..6 của 80 máy). Máy nào đủ 6/6 nick xem như hoàn thành 100%, tự động dừng reg cho máy đó và chỉ tập trung reg bù cho các máy chưa đủ 6 nick.

- **QUY CHUẨN MỞ RỘNG TRẦN 8 NICK & DÀNH SLOT 7/8 LÀM PHÔI TRẮNG CHUYỂN GIAO (User Rule 2026-09-06)**:
  1. **Nâng trần reg lên 8 nick**: `MAX_ACCOUNTS_PER_MACHINE = 8` (trong `_detect_clean.py` và `tiktok_target_eligibility.py` repo `Tiktok_Reg`) để tận dụng dải proxy Kibe dồi dào reg bù nick cho farm Admin (3 máy/1 IP khó reg).
  2. **Slot 7 & 8 là Phôi Trắng (Incubator - FEED ONLY, CẤM UPLOAD)**: Tuyệt đối không tạo folder video, không map vào pipeline upload tại Kibe để tránh lệch kho video khi chuyển giao sang Admin.
  3. **Không chuyển nóng (Anti-Hot-Transfer)**: Reg xong BẮT BUỘC nuôi đệm tại Kibe tối thiểu 2-3 ngày để tích lũy session/cookie và trust score. Trước khi login vào máy Admin (IP Đà Nẵng), cho nick nghỉ cooldown 6-12h.
  4. **Chuỗi ca đêm linh hoạt (Night-Chain Pivot, cập nhật 2026-09-07)**: Ca đêm 01:00 (`run_night_chain_pipeline.py`) ưu tiên Reg. Nếu không còn target reg (máy đã full 8 nick / `Total targets: 0`), tự động chuyển đổi thành ca lướt feed nuôi nick Slot 7 hoặc 8 theo ngày chẵn/lẻ (`ZoneInfo("Asia/Ho_Chi_Minh")`: ngày lẻ Slot 7, ngày chẵn Slot 8). **QUAN TRỌNG**: Phase 3 (Add 2FA) VẪN TIẾP TỤC CHẠY BÌNH THƯỜNG SAU ĐÓ để quét bù 2FA cho các nick tồn/deferred, không được bỏ qua. Chi tiết kiến trúc: `references/eight-slot-incubator-and-night-chain-feed-fallback.md`.



## WORKBOOK = NGUỒN SỰ THẬT DUY NHẤT (avatar/upload batch, 2026-08-15 — user yêu cầu lưu rule, "đừng tự chế")



- **Workbook (Tik1.xlsx / Tik2.xlsx / tik3.xlsx) là nguồn sự thật duy nhất** cho mapping máy → device → ID account → Folder Video → avatar source. **CẤM tự suy luận/chế mapping, CẤM cần config riêng từng máy** — workflow đọc trực tiếp từ workbook theo flag `-Tik <N>`.

- Mỗi workbook có sẵn cột: `Máy`, `device ID`, `ID`, `Folder Video`, `video gốc`. Chạy `run_tiktok_upload_avatar.ps1 -Tik 1` / `-Tik 2` là workflow tự resolve ID + Folder Video + avatar. Sai lầm đã phạm: tưởng cần config/workbook riêng từng máy → tự chế manifest thiếu máy (máy 39 Tik2 bị sót) → user bác.

- **`taikhoan_run_safe.xlsx` = nguồn nick THẬT (cột: `Máy`, `Device ID`, `ID`) — mỗi máy có NHIỀU row nick (2-5 nick/máy, vd máy 29 có 4 nick, máy 35 có 5 nick).** User tạo 1 Tik cho mỗi nick: **Tik1 = nick row 1 mỗi máy, Tik2 = nick row 2 mỗi máy** (Tik1.xlsx/Tik2.xlsx là view của row tương ứng). **KHÔNG phải "mỗi máy 2 nick"** — sai model này từng làm đếm lệch 2 lần trong 1 session (user bác: "Đéo phải chỉ 2 nick đâu, trong file taikhoanrunsafe cả đống nick đó").

- **PITFALL "Mở file Tik đọc là biết" (user correction 2026-08-16):** khi user hỏi "máy nào đã/chưa làm TikN" — **ĐỪNG đếm từ report.json** (tốn thời gian, dễ nhầm nick vì run SUCCESS của nick khác cùng device). **Mở thẳng `TikN.xlsx` đọc cột `Video Đã Đăng`** (cột 8): giá trị trống/0 = chưa đăng video nào cho nick đó; `MISSING_ID` ở cột `Kiểm Tra Dữ Liệu` = workbook thiếu ID (không chạy được, báo user điền). Cột này là acceptance data của nick.

- **PITFALL ĐỐI CHIẾU NICK THEO ROW/SLOT (user correction 2026-08-28):** Khi kiểm tra máy đã có nick cho Row cụ thể (VD Row 2 / Tik2) hay chưa:
  - **Quy ước hỏi "row bn của máy đó"**: Khi user hỏi "acc/nick đó là row mấy của máy đó", họ đang hỏi **thứ tự slot/ca của máy đó (Row 1..8 của Máy M trong sheet `Tài Khoản`)**, KHÔNG PHẢI số dòng toàn cục của Excel (vd dòng 563). Phải trả lời rõ: `Row K của Máy M (Slot K / Ca K, Tik XXX)`.
  - BẮT BUỘC tra cứu đối chiếu cả 3 nguồn: (1) `taikhoan_dat_v2_updated .xlsx` (bảng tổng master), (2) `taikhoan_run_safe.xlsx` (bảng feed live), và (3) `TikN.xlsx` (bảng upload con).
  - Nguồn chuẩn duy nhất quy định máy có nick chạy hay không là `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2`. Tuyệt đối không tự chế dữ liệu hay suy đoán thiếu nick khi bảng chính đã có ID.
  - Nếu `taikhoan_dat_v2` và `taikhoan_run_safe` ĐÃ CÓ ID (vd máy 73 đã có `yeisiearet4` ở Row 2) nhưng `Tik2.xlsx` còn trống/`MISSING_ID` hoặc `hermes_cron_source_config.json` chưa reload $\rightarrow$ máy sẽ bị cron bỏ qua do config chưa sync, nhưng thực tế máy ĐÃ ĐƯỢC REG nick. TUYỆT ĐỐI KHÔNG kết luận máy chưa có ID nếu chưa kiểm tra bảng master `taikhoan_dat_v2`.
  - Cột `device ID` ở dòng mới reg có thể bị ghi nhầm chuỗi ngày tháng (vd `23/08/2026`) thay vì serial phần cứng — cần kiểm tra và chuẩn hóa serial từ `PROXYgandienthoai.xlsx`.

- **PITFALL BẪY ALERT WATCHDOG HARDCODE `-Row 1` & BÁO SAI NICK CA NUÔI (user correction 2026-09-07: "ủa sao cái này là row 1 đc nhỉ, mà cái farm alert thông báo cũng ngu nữa làm gì phải row 1. Làm luôn. Báo đúng nick"):**
  - **Triệu chứng & Sai lầm**: Watchdog/alert khi bắt lỗi farm sinh mẫu lệnh B4 bị hardcode cứng `-Row 1` (`run-feed-session.ps1 -Machines <M> -Row 1 ...`) và in nick default của Row 1.
  - **Bẫy**: Chạy canary theo lệnh hardcode `-Row 1` sẽ switch nhầm sang account của Slot 1, test sai nick của ca gặp lỗi thực tế (ví dụ ca 2 lúc 14:39 ngày lẻ là Row 3), và báo cáo kết quả sai lệch.
  - **Quy tắc giải quyết**:
    1. Coordinator/Worker BẮT BUỘC suy luận ca chạy từ timestamp của alert và bảng Parity Schedule:
       + Ngày lẻ: Ca 1 (06:00) $\rightarrow$ Row 1; Ca 2 (12:30) $\rightarrow$ Row 3; Ca 3 (19:00) $\rightarrow$ Row 5.
       + Ngày chẵn: Ca 1 (06:00) $\rightarrow$ Row 2; Ca 2 (12:30) $\rightarrow$ Row 4; Ca 3 (19:00) $\rightarrow$ Row 6.
    2. Lệnh Canary Test B4 BẮT BUỘC thay `-Row <K>` bằng đúng row của ca đó (ví dụ `-Row 3`).
    3. Tra cứu và đối soát đúng username từ `taikhoan_run_safe.xlsx` cho `(Máy, Row)` trước khi báo cáo kết quả nghiệm thu cho user. Chi tiết: `references/canary-parity-row-resolution-and-event-space-overlay.md`.

- Mỗi file Tik đều có cột: `Máy`, `device ID`, `ID`, `Folder Video`, `video gốc`, `Keyword Video`, `Hashtag Pool`, `Video Đã Đăng`, `Kiểm Tra Dữ Liệu`, `Render Status`, `Render MP4`, `Render Updated`. Muốn biết trạng thái nick → đọc các cột này trực tiếp, không suy diễn.

- **PITFALL PHÂN BIỆT NICK KHI ĐẾM (user bác 2026-08-15: "mày biết phân biệt tik 1 và tik2 k?")**: report.json mỗi run có field `account`. Run `status=SUCCESS` của nick Tik1 KHÔNG tính cho nick Tik2 — cùng device nhưng khác nick. Khi đếm "máy nào đã đăng video" / "máy nào chưa", phải so khớp `report.account` == ID workbook của nick đang xét (vd account == Tik2 ID thì mới tính cho Tik2). Đếm mù theo status SUCCESS sẽ báo sai (10 máy từng bị báo đã đăng nhưng thực ra chỉ mới đăng Tik1).

- **Avatar source chuẩn**: `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg` (đã generate sẵn khi render video cho từng folder output). CẤM lấy avatar theo `D:\video goc\<Folder Video>\avatar.jpg` vì `Folder Video` (1..640) không cùng namespace với `video gốc` (1..480). Lỗi `AVATAR_SOURCE_MISSING: ...\TIKTOK-videonuoinick\<folder>` = folder render chưa được tạo hoặc thiếu avatar.jpg.
- **PITFALL: TRÙNG AVATAR DO XUNG ĐỘT NAMESPACE FOLDER VIDEO VỚI VIDEO GỐC & CACHE THIẾT BỊ (2026-09-11)**:
  - **Triệu chứng**: Các nick Row 5/6 mới bị dính avatar của các nick Row 1 cũ (ví dụ: nick Row 5 Máy 1 `buithudung2011` có `Folder Video = 5` bị dính avatar "bà mập" của Row 1 Máy 5 có `video gốc = 5`; hoặc dính avatar của Row 1 trên cùng máy `lipsellczaw`).
  - **Nguyên nhân cốt lõi**:
    1. `resolve_avatar_path()` trong `path_resolver.py` duyệt cả `D:\TIKTOK-videonuoinick` lẫn `D:\video goc` theo `folder_value`. Số `Folder Video` của Tik5 (`5, 13, 21...`) lại trùng đúng dải số `video gốc` của Tik1 (`1..80` bằng số máy), dẫn tới việc bốc nhầm avatar nguồn của nick Row 1 máy khác.
    2. Trên cùng 1 thiết bị, file avatar cũ của nick Row 1 còn tồn trong `/sdcard/DCIM/Camera/` hoặc `/sdcard/Download/` khiến Media Picker hiển thị tile cũ, tap mù gây gán nhầm.
  - **Quy tắc chuẩn hóa**:
    1. BẮT BUỘC resolve avatar từ output render: `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`, CẤM fallback sang `D:\video goc\<Folder Video>`.
    2. Trước khi push avatar mới: dọn sạch file ảnh cũ trên thiết bị (`rm -f /sdcard/DCIM/Camera/avatar* /sdcard/Download/avatar* /sdcard/_ss*.png`) và kích hoạt `MEDIA_SCANNER_SCAN_FILE`.
    Chi tiết xem: `references/avatar-namespace-collision-and-cache-drift.md`.

- **PITFALL: POWERSHELL CLI SWITCH PARAMETER TRAP (2026-09-11)**:
  - **Triệu chứng**: Khi gọi script con từ PowerShell CLI (`powershell.exe -File script.ps1`), các tham số kiểu `[switch]$AvatarOnly` bị truyền dưới dạng string `-AvatarOnly True` (từ hashtable `@splat`), gây lỗi `ParameterArgumentTransformationError: Cannot convert value "System.String" to type "System.Management.Automation.SwitchParameter"`.
  - **Nguyên nhân**: `[switch]` parameter trong PowerShell chỉ nhận bare switch (`-AvatarOnly`) hoặc boolean native (`$true`/`$false`/`1`/`0`), KHÔNG nhận string `"True"`. Hashtable splatting qua subprocess tự động chuyển `$true` thành string `"True"`.
  - **Quy tắc chuẩn hóa**:
    1. Khi gọi subprocess `powershell.exe`, **BẮT BUỘC** build mảng argument `$batchArgs` với bare switch `-AvatarOnly` (không kèm value string) thay vì truyền hashtable `@splat`.
    2. Mẫu chuẩn:
       ```powershell
       $batchArgs = @(
           "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $batchLauncher,
           "-Tik", $Tik, "-MaxParallel", $MaxParallel, "-HostConfigPath", $HostConfigPath,
           "-AvatarOnly",  # bare switch, KHÔNG có "True" sau nó
           "-ForceAvatarMachineList", $ForceAvatarMachineList,
           "-MachineStartStaggerMs", $MachineStartStaggerMs
       )
       if ($AssignmentManifest -and $WorkerId) {
           $batchArgs += @("-AssignmentManifest", $AssignmentManifest, "-WorkerId", $WorkerId)
       }
       & powershell.exe @batchArgs
       ```
    Chi tiết xem: `references/powershell-switch-argument-trap.md`.

    - **PITFALL: Avatar Media Picker bị dính ảnh chụp màn hình OTP/UI cũ (`_ss.png`) (hit 2026-08-20)**:

- Sau khi chạy avatar theo `-Tik <N>`, tổng hợp trạng thái phải đọc report.json từng run (status `AVATAR_SMOKE_SUCCESS` = thành công); launcher summary có thể báo sai khi verifier cũ.

- Manifest batch: `resources` phải KHỚP `-ForceAvatarMachineList` — manifest 2 máy mà list 1 máy → `INVENTORY_ERROR: assignment preflight failed` ngay.



- **Avatar Launcher (`run_tiktok_upload_avatar.ps1`) & Quy trình dọn dẹp sau Up Avatar (2026-08-21)**:
  1. Chạy độc lập qua: `echo RUN | powershell.exe -File run_tiktok_upload_avatar.ps1 -Tik <N> -AssignmentManifest <path> -WorkerId <id> -ForceAvatarMachineList "<machines>" -MaxParallel 1 -HostConfigPath D:\Taadaa\machine-config\kibe.yaml`.
  2. `AssignmentManifest` chuẩn (automation-core v1) bắt buộc gồm các trường:
     `{"schema_version": 1, "assignment_id": "...", "owner_id": "...", "resources": ["machine:XX"], "reviewed_at": "<ISO-UTC-timestamp>"}`.
  3. **Quy tắc đóng app & về Home sau Up Avatar**: Sau khi cập nhật avatar thành công và chụp màn hình xác nhận, code trong `state_machine.py` (`_handle_ensure_avatar_impl`) BẮT BUỘC thực hiện `am force-stop com.zhiliaoapp.musically; am force-stop com.ss.android.ugc.trill; input keyevent 3` để đóng app và đưa máy về màn hình chính, tránh treo app hoặc xung đột ca nuôi tiếp theo.
  4. **Cơ chế Đánh Dấu Video vs Avatar (Cập nhật 2026-09-06)**:
     - **Đăng Video**: CÓ cột đánh dấu rõ ràng trong Excel (`Video Đã Đăng` trong `TikN.xlsx` cột 8 và `taikhoan_run_safe.xlsx` cột 4) làm monotonic cursor (`next_video = Video Đã Đăng + 1`), kết hợp Idempotency ledger SHA-256 (`D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/`).
     - **Up Avatar (Cột Avatar & Auto-Pending Launcher)**:
       + Đã bổ sung cột **`Avatar`** trên `Tik1..Tik6.xlsx` và durable ledger `D:/CodexRuntime/tiktok-video/idempotency/avatar-ledger.jsonl`.
       + Nick đã up avatar thành công được đánh dấu `Avatar = "OK"`.
       + **Bẫy sót avatar ở Video 2+**: Workflow upload tự động CHỈ kích hoạt `ENSURE_AVATAR` ở Video #1 (`video_number == 1`). Với nick Video 2+ hoặc dàn nick mới Row 5/6 đang nuôi lướt feed 0 video, dùng launcher độc lập `run_tiktok_upload_avatar.ps1 -Tik <N>`.
       + **Auto-Resolve Máy Chưa Có Avatar**: Khi chạy `run_tiktok_upload_avatar.ps1 -Tik <N>` mà không truyền `-ForceAvatarMachineList`, launcher gọi helper script Python riêng `scripts/resolve_avatar_pending_machines.py` (tránh bẫy PowerShell CLI inline parsing lỗi f-string/dấu ngoặc), tự động mở đúng workbook (`tik3.xlsx` chữ thường cho Tik 3, `TikN.xlsx` cho các Tik khác), lọc các máy có ID hợp lệ mà cột `Avatar` chưa `OK` (bao gồm đầy đủ các máy có nick hợp lệ, KHÔNG tự ý loại trừ Máy 38), và kích hoạt batch cho các máy còn thiếu (hỗ trợ `-WhatIf` preflight). Khi up xong tự động cập nhật `Avatar = "OK"` vào Excel và ledger.
       - **CẤM SUY LUẬN `Video Đã Đăng >= 1` $\rightarrow$ `Avatar = OK` (Hit 2026-09-08)**: Tuyệt đối không dùng logic đếm video để gán khống trạng thái Avatar trong workbook. Dàn nick có thể đã đăng 4 video nhưng chưa từng chạy flow avatar (như toàn bộ Row 4 Tik4). Chỉ gán `Avatar = "OK"` khi có log/ledger xác nhận (`avatar-ledger.jsonl`) hoặc verify trực tiếp qua CDN (`avatarLarger` không chứa mã placeholder `1594805258216454`). Xem chi tiết: `references/avatar-status-tracking-and-pending-batch-resolver.md`.
       Chi tiết xem: `references/avatar-namespace-collision-and-cache-drift.md`.

       - **Tiến trình Render Tik4 (`run_tik4_random_render.ps1`) & Cơ chế Continue on Lacking Source (2026-08-21)**:
  Chi tiết xem: `references/avatar-namespace-collision-and-cache-drift.md`.

  - **PITFALL: Avatar Media Picker bị dính ảnh chụp màn hình OTP/UI cũ (`_ss.png`) (hit 2026-08-20)**:
  Khi push avatar mới và mở picker TikTok, nếu trên máy còn sót file ảnh chụp màn hình OTP/social cũ (`/sdcard/_ss.png`, `/sdcard/_ss_social.png` hoặc cache screenshots), MediaStore có thể index các ảnh này lên đầu album "Gần đây". Việc chọn mù tile đầu tiên `(180, 320)` sẽ làm set nhầm ảnh tin nhắn OTP/màn hình lỗi làm avatar thay vì ảnh chân dung người thật.
  **Quy tắc phòng ngừa & khắc phục:**
  1. Trước khi upload avatar: dọn sạch các file ảnh chụp màn hình tạm (`rm -f /sdcard/_ss.png /sdcard/_ss_social.png`).
  2. Push file avatar chuẩn từ folder render (`D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`) vào `/sdcard/DCIM/Camera/` và trigger `android.intent.action.MEDIA_SCANNER_SCAN_FILE`.
  3. Trong Media Picker: BẮT BUỘC visual check (vision analysis hoặc correlation similarity) để xác nhận tile chọn là ảnh chân dung người thật / chủ thể nghệ thuật, CẤM tap mù ô đầu tiên khi chưa verify.

## QUY LUẬT FOLDER VIDEO — anchor từ Tik1 (đã đăng video thành công)

- **BẮT BUỘC ĐỊNH DẠNG TÊN SỐ `1.mp4..N.mp4` TRONG OUTPUT RENDER (`D:\TIKTOK-videonuoinick`)**:
  - `path_resolver.py` của upload workflow đọc cột `Video Đã Đăng` từ workbook và resolve đường dẫn tuyệt đối dạng `{media_source_root}/{Folder Video}/{video_number}.mp4` (`video_number = Video Đã Đăng + 1`).
  - **Cơ chế chọn Video khi Upload**: Upload chạy TUẦN TỰ (`1.mp4` -> `2.mp4` -> `N.mp4`), KHÔNG random thứ tự file trong folder.
  - **Cơ chế Random khi Render (`random_batch_render.py`)**: Trong cùng 1 folder, MỖI video (`1.mp4`, `2.mp4`...) đều có `seed` ngẫu nhiên độc lập (`compute_seed` tính từ `seq` + `source_relative`), áp dụng bộ filter hình ảnh, âm thanh, GOP khác nhau để phá mã băm (MD5 / Perceptual Hash).
  - Nếu file render mang tên dài/prefix (vd: `tik_tik3-stt347...mp4` hay `Tiêu đề [id].mp4`), upload sẽ lập tức văng `PathResolverError: Video file not found: ...\1.mp4` $\rightarrow$ **dừng ca nuôi, không upload được**.
  - Toàn bộ video trong mỗi folder render `D:\TIKTOK-videonuoinick\<Folder Video>` PHẢI được đánh số tuần tự `1.mp4`, `2.mp4`... `N.mp4`.
  - **Quy chuẩn triển khai Code trong `scripts/random_batch_render.py`**:
    1. `RenderTask` dataclass: Bổ sung trường `relative_output: Path` (giữa `relative_source` và `output`) để lưu giữ tên tệp output dạng số tuần tự.
    2. `make_tasks()`: Gán `relative_output = relative_source.parent / f"{seq}.mp4"` (bảo toàn cấu trúc thư mục cha `relative_source.parent`, chỉ đổi stem thành `{seq}.mp4`), truyền `relative_output=relative_output` vào `RenderTask`.
    3. `render_one()`: Dùng trực tiếp `relative_output = task.relative_output` thay vì phái sinh từ `relative_source.with_suffix(".mp4")`, đảm bảo skip-check và log message khớp đúng tên output tuần tự.
    4. Unit test: `test_output_mirrors_source_structure` trong `scripts/test_random_pipeline.py` đối soát `tasks[0].output == output_root / "group_a" / "nested" / "1.mp4"`.

```text

Folder Video của slot k (k=1..8) của máy m = (m-1)*8 + k



Tik1 (slot 1): 1, 9, 17, 25, ... 633   (đã render + đã đăng)

Tik2 (slot 2): 2, 10, 18, 26, ... 634   (đã render)

tik3 (slot 3): 3, 11, 19, 27, ... 635   (đã render xong 80/80 folder >=45 mp4)

Tik4 (slot 4): 4, 12, 20, 28, ... 636   (đã render xong 80/80 folder 2026-08-27)

Tik5 (slot 5): 5, 13, 21, 29, ... 637   (đã render xong 80/80 folder 2026-08-29)

Tik6 (slot 6): 6, 14, 22, 30, ... 638   (tạo workbook + đang render 2026-08-30)

Tik7 (slot 7): 7, 15, 23, 31, ... 639   (80 folder output; nguồn 481..560, workbook Tik7.xlsx)

Tik8 (slot 8): 8, 16, 24, 32, ... 640   (80 folder output; nguồn 561..640, workbook Tik8.xlsx)

- Chi tiết mở rộng kho render Tik7/Tik8 xem `references/tik7-tik8-mapping-and-render-pipeline.md`.
- Bản phân tích kiến trúc gốc rễ, cạm bẫy Excel control plane và 4 quy tắc bất biến (System Invariants) từ Claude Code: `references/phone-farm-architecture-invariants-and-reliability.md`.
- Bản đồng thuận kiến trúc Claude CLI & Sol Planner: chống bệnh write-without-read làm văng nick, 4 System Invariants, JIT Reconciliation qua WinRT OCR/ATX, và Excel Preflight Validator chặn trùng video gốc (17/09/2026): `references/architecture-consensus-write-without-read-and-excel-preflight.md`.
- Hướng dẫn vận hành bộ kiểm tra 5 Invariant Rules cho toàn bộ file Excel của Farm (`excel_preflight_validator.py`): xem `references/excel-preflight-validator-and-5-invariant-rules.md`.
- Hướng dẫn tích hợp Preflight Validator chốt chặn vào Cron Sync (`hermes_taikhoan_sync_cron.py`): xem `references/excel-preflight-validator-cron-sync-integration.md`.
- **CƠ CHẾ FAIL-CLOSED PREFLIGHT VALIDATOR TRONG CRON SYNC (`hermes_taikhoan_sync_cron.py`, 2026-09-17)**:
  + Chốt chặn tại Bước 2.5: Trước khi chuyển sang Bước 3 (`generate_config_from_safe_workbook`), cron sync BẮT BUỘC gọi `excel_preflight_validator.py` kiểm tra 5 Invariant Rules trên toàn bộ file Excel.
  + Nếu có bất kỳ lỗi FAIL nào (như trùng lặp tài khoản giữa các slot/file Tik, sai mapping Folder Video/Video Gốc), validator trả về exit code khác 0 $\rightarrow$ cron sync lập tức đánh dấu `failed = True`, ghi log cảnh báo và HỦY BỎ hoàn toàn việc cập nhật `hermes_cron_source_config.json`, giữ an toàn cho Farm không bị nạp cấu hình lỗi.
- Quy tắc scrape TikTok public (bẫy SlardarWAF vs DIE/NOT_FOUND, nạp proxy_pool_67.txt) & Windows Firewall chặn Inbound Python 3.12 (bắt buộc dùng Python 3.11 khi host web mobile) xem `references/tiktok-tracker-public-scrape-and-windows-firewall-python-rules.md`.
- Chi tiết cơ chế theo dõi số liệu và tăng trưởng tài khoản TikTok (Follower, Like, UID, Cắn đề xuất) từ workbook xem `references/tiktok-farm-tracking-and-workbook-delta.md`.
- Hệ thống theo dõi thống kê TikTok Farm (Follower, Like, Video, Cắn đề xuất), bẫy SlardarWAF và Web Dashboard mobile: `references/tiktok-farm-account-tracking-and-dashboard.md`.
- Kỷ luật quét public profile TikTok chống SlardarWAF, nguồn chuẩn proxy pool 67, tích hợp web kibe:2310 và Sol Plan trước dispatch: `references/tiktok-public-profile-tracking-and-proxy-pool-rules.md`.
- **PITFALL: SLARDARWAF VS NOT_FOUND FALSE POSITIVE KHI TRACKING PUBLIC PROFILE (2026-09-17)**:
  + Khi quét dồn dập nhiều tài khoản TikTok từ 1 IP, TikTok kích hoạt SlardarWAF challenge (~1400 bytes HTML không có hydration JSON).
  + Không coi thiếu JSON là `NOT_FOUND`/`DIE`, phân loại `RATE_LIMITED` và xoay 67+ Proxy 4G. Dashboard: port 20130 (`tiktok_dashboard.py`).
- Auto-sync Keyword/Hashtag toàn farm xem `references/tik7-tik8-all-tik-keyword-sync-and-avatar-watchdog-20260913.md` & `references/hashtag-safety-shield-and-all-tik-niche-audit-20260927.md`.
- Kiến trúc khởi tạo khung workbook Tik7/Tik8 trước và dùng cron auto-sync keyword/hashtag từ state.db xem `references/tik7-tik8-creation-and-keyword-sync.md`.

```



- Folder video = thư mục trong `D:\TIKTOK-videonuoinick\<folder>` (đã render, 45 mp4/folder cho slot đã chạy).

- **PITFALL \"số folder trùng giữa Tik ≠ conflict\" (user phạt 2 lần 2026-08-16: \"mày bị lú quá\"):** Folder Video Tik3 máy 1-20 = 3, 11, 19, ... 155 — trông GIỐNG folder Tik1/Tik2 nhưng là DẢI OUTPUT RIÊNG của Tik3 (mỗi Tik có dải riêng trong TV). Folder Video = folder OUTPUT (kết quả render); `video gốc` = folder NGUỒN trong `D:\video goc`. Luôn đọc cặp (Folder Video ↔ video gốc) từ chính workbook, KHÔNG suy luận từ số folder. `D:\video goc` folder ≥305 có thể rỗng (chỉ avatar.jpg) — đó là folder output Tik3, video thật nằm trong TV.

- Cột `Tik` trong REG **đã được đổi tên thành `Folder Video`** (2026-08-11). Giá trị = mã folder D, **KHÔNG phải số thứ tự dòng/STT toàn cục**.

- ID trong file Tik lấy theo **đúng vị trí dòng (slot)** trong REG của máy đó: Tik1=slot 1, Tik2=slot 2, tik3=slot 3, Tik4=slot 4, Tik5=slot 5. Slot không có ID → để trống, status `MISSING_ID`.

- **QUY TẮC RENDER KHI THIẾU ID (User Rule 2026-08-27)**: Máy thiếu ID (`MISSING_ID`) VẪN RENDER BÌNH THƯỜNG vào đúng `Folder Video` theo mapping. Không được skip hay chặn render máy thiếu ID; ID tài khoản được nạp và sync sau vào workbook. Chi tiết xem `references/tik5-creation-and-sequencing.md`.

Chi tiết xem: `references/avatar-namespace-collision-and-cache-drift.md`.

- **Tiến trình Render Tik4 (`run_tik4_random_render.ps1`) & Cơ chế Continue on Lacking Source (2026-08-21)**:



```text

video gốc Tik1 = máy            (1..80)    -> D:\video goc\<máy>

video gốc Tik2 = 80 + máy       (81..160)  -> D:\video goc\<80+máy>

video gốc tik3 = 160 + máy      (161..240) -> D:\video goc\<160+máy>

video gốc Tik4 = 240 + máy      (241..320) -> D:\video goc\<240+máy>

video gốc Tik5 = 320 + máy      (321..400) -> D:\video goc\<320+máy>

video gốc Tik6 = 400 + máy      (401..480) -> D:\video goc\<400+máy>

```

- **Quy tắc Import trong Upload Hook (`multi_machine_feed_session.py`)**:
  Khi import `upload_preflight`, bắt buộc dùng khối try/except fallback (`from python_runner.flows.upload_preflight import ...` rồi fallback `from flows.upload_preflight import ...`) để tránh `ModuleNotFoundError: No module named 'flows'` khi gọi qua các runner entrypoint khác nhau.
  Đồng thời khi mở file `.xlsx` trên OneDrive trong `upload_preflight`, cần retry 3 lần kèm `time.sleep(1.5)` để tránh file-lock `PermissionError` do OneDrive sync. Kiểm tra post verification stdout bằng chuỗi lowercase (`post verification passed`, `upload video success`, `upload completed`).

- **Proxy URL-Encoding cho Downloader (`download_by_niche.py`)**:
  Proxy pool 38 cổng di động (`PROXYgandienthoai.xlsx`) mật khẩu có ký tự đặc biệt `#` và `!` (`TaadaaMobi#2026!`). Bắt buộc dùng `urllib.parse.quote(..., safe="")` để URL-encode user/pass (`TaadaaMobi%232026%21`) trước khi đưa vào URL `http://user:pass@host:port` cho `yt-dlp` để tránh lỗi parse URL và `407 Proxy Authentication Required`. Hỗ trợ chạy `--parallel 16` song song an toàn nhờ Global Whisper Lock.

- **Tiến trình lưu trữ dữ liệu Download Pool (`D:\video goc`)**:
  Toàn bộ video tải về được ghi tự động vào `D:/CodexRuntime/tiktok-video/state.db` (SQLite) và `D:/OneDrive/SharedData/tiktok-video/global-ledger/Kibe.jsonl` (Global Ledger) để chống tải trùng giữa các máy trong hệ thống. Sheet `Kiểm tra nguồn` trong các file workbook (`Tik1..Tik4.xlsx`) được cập nhật đồng bộ sau các batch render và nghiệm thu mapping.



- CẢNH BÁO: tik3 từng bị copy `video gốc` của Tik2 (81..160) — phải sửa thành 160+máy.

- D:\video goc mỗi folder có 55-65 mp4 (đủ), `data/niches_pool.txt` là pool niche (81 dòng: group\tslug\tlabel\tallow_no_speech).



## HASHTAG — theo KEYWORD CỦA FOLDER NGUỒN (KHÔNG theo máy!)



- **Sai lầm đã sửa 2026-08-11**: hashtag từng bị lấy theo máy (copy Tik1 cùng máy) — user bác: phải theo niche của folder nguồn.

- Cách đúng:

  1. Niche slug của folder nguồn f lấy từ DB: `D:\CodexRuntime\tiktok-video-downloader\state-real-1-tiktok-final.db` (bảng `folders`: folder_num → niche).

  2. Label tiếng Việt từ `data/niches_pool.txt` (slug → label).

  3. Hashtag: nếu niche đã có trong Tik1 sheet `Hashtag theo Folder` → copy nguyên pool của folder Tik1 cùng niche; niche mới → tạo pool chuẩn `#<slug> [+ extras] #<slug>vietnam #<slug>moingay #tiktokvietnam #xuhuong #fyp #videohay` (9-13 tag).

- Điền vào CẢ cột `Keyword Video` + `Hashtag Pool` (sheet TaiKhoan) lẫn sheet `Hashtag theo Folder` (cột Keyword/Niche + Hashtag Pool).

- Script đăng (`hashtag_selector.py`) đọc cột `Hashtag Pool` từ workbook; nếu trống → fallback `#fyp #viral #tiktok...` (KHÔNG theo niche, không nên).



## RENDER RANDOM (Tik2/Tik3/Tik4/Tik5)

- **Tik5 Mapping chuẩn**: Slot 5 (`(m-1)*8+5`), nguồn `320+m` (321..400), workbook `D:\OneDrive\TaadaaData\kibe\Tik5.xlsx`, launcher `run_tik5_random_render.ps1`.
- **Tik6 Mapping chuẩn**: Slot 6 (`(m-1)*8+6`), nguồn `400+m` (401..480), workbook `D:\OneDrive\TaadaaData\kibe\Tik6.xlsx`, launcher `run_tik6_random_render.ps1`.
- **Quy tắc Xếp hàng Render (Chained Sequential Queue, 2026-08-27)**:
  - Khi chạy nối tiếp các batch render (như Tik4 -> Tik5 -> Tik6), **CẤM chạy đồng thời hai batch render** vì sẽ làm quá tải CPU và tranh chấp file log/FFmpeg.
  - Sử dụng script supervisor nối tiếp (`scripts/tik4_then_tik5.py`) để đợi batch trước hoàn tất 100% (80/80 folder hợp lệ), sau đó mới tự động kích hoạt batch tiếp theo.
- **Quy tắc Render khi Thiếu ID (`MISSING_ID`, 2026-08-27)**:
  - Máy thiếu ID vẫn render bình thường vào đúng `Folder Video`. Không skip/chặn render máy thiếu ID; ID tài khoản được bổ sung sau vào workbook trước khi upload.
- **Pipeline Anti-Detection & Auto-Aspect Nâng cấp (2026-08-27/29)**:
  - Chi tiết kiến trúc xem `references/random-render-antidetect-pipeline.md`.
  - **Auto-Aspect Detection cho Video Ngang 16:9 (`fit_pad`)**: Tự động phát hiện $DAR > 1.0$ (kết hợp SAR và rotation trực giao), chuyển từ `fill_crop` sang `fit_pad` viền đen trên dưới (`scale=trunc(iw*sar/2)*2:ih,setsar=1,scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1`), giữ 100% hình ảnh không bị cắt xén hai bên.
  - **Đồng bộ A/V Trim & Limiter**: Tích hợp A/V sync temporal trim trước speed warp ($audio\_tempo = speed\_factor / pitch\_factor$), In-line audio noise floor (`aeval`), Adaptive Nyquist lowpass ($\le 0.45 \times target\_sample\_rate$) và `alimiter` latency compensation kèm `apad` + `atrim=0:D_out` khóa chính xác endpoint thời lượng.
- Launcher: `run_tik2_random_render.ps1`, `run_tik3_random_render.ps1`, `run_tik4_random_render.ps1`, `run_tik5_random_render.ps1`, `run_tik6_random_render.ps1` (có `-AutoRun` để skip confirm).
- Slot 0-based trong runner: Tik1=0, Tik2=1, tik3=2, Tik4=3, Tik5=4, Tik6=5, Tik7=6, Tik8=7. (Lưu ý quan trọng: `random_batch_render.py` và `randomize_profile.py` quy ước slot 0-indexed từ 0..7: Nick 7 / Slot 7 truyền `--slot 6`, Nick 8 / Slot 8 truyền `--slot 7`; tham số này điều khiển Voice Profile `VOICE_PROFILES[slot % 3]` gồm treble/normal/bass và sinh seed ngẫu nhiên độc lập chống trùng lặp giữa các nick trên cùng máy).
- **Cơ chế Randomize trong cùng 1 Folder**:
  - Không phải 1 preset cố định cho cả loạt video. Từng video trong cùng folder đều nhận một `seed` độc lập được tính từ `SHA256(run_id|machine_id|slot|seq|source_relative|seed_offset)`.
  - Tham số `--slot` đóng vai trò phân phối Voice Profile (`VOICE_PROFILES[slot % 3]`) và dải vân tay âm thanh/màu sắc giữa các nick khác nhau trên cùng một máy.
- `--parallel 1` vì máy host ~92% CPU khi chạy 2 worker.
- Output: `D:\TIKTOK-videonuoinick\<Folder Video>` (mỗi folder 45 mp4; min 30).
- Theo dõi tiến độ: script watchdog `tik3_render_watchdog.py`, `tik4_render_watchdog.py`, `tik5_render_watchdog.py`, `tik6_render_watchdog.py` (đếm folder đủ mp4, cron no_agent mỗi 60 phút).

## QUY TRÌNH THAY THẾ / RESET VIDEO POOL CHO NICK (RESEED FOLDER)

Khi một nick cần đổi/reset toàn bộ video (vd: reup nhầm niche, dính gậy, đổi hướng content):
1. **Tra cứu mapping chuẩn**:
   - Tìm account ID trong `taikhoan_dat_v2_updated .xlsx` / `taikhoan_run_safe.xlsx` / `TikN.xlsx` để xác định chính xác: `Máy`, `Slot (Tik1..Tik4)`, `video goc` (thư mục nguồn `D:\video goc\<video_goc>`) và `Folder Video` (thư mục render `D:\TIKTOK-videonuoinick\<Folder Video>`).
2. **Dọn sạch folder cũ của nick**:
   - Xóa toàn bộ file mp4 và cache trong `D:\video goc\<video_goc>` và `D:\TIKTOK-videonuoinick\<Folder Video>`.
3. **Tìm và kiểm tra folder dự phòng (spare pool)**:
   - Quét toàn bộ workbook (Tik1..Tik4, taikhoan_dat_v2) đảm bảo folder dự phòng chưa từng được gán cho nick nào đang chạy upload.
   - Folder nguồn: chọn folder trong `D:\video goc\` (thường >320) có $\ge 45$ video sạch chưa dùng.
   - Folder render: chọn folder trong `D:\TIKTOK-videonuoinick\` đã render hoàn tất ($\ge 44$ video + `avatar.jpg`) chưa thuộc danh sách output của Tik1..Tik4.
4. **Chuyển theo dạng CUT (dọn sạch spare folder sau khi chuyển)**:
   - Chuyển toàn bộ nội dung từ folder nguồn/render dự phòng sang thư mục đích của nick.
   - **BẮT BUỘC CUT dứt điểm**: Dọn sạch (xóa trắng) folder nguồn/render dự phòng cũ sau khi chuyển, CẤM để bản copy thừa vì sẽ dẫn đến rủi ro 2 nick trùng video/avatar sau này.
5. **Bù nguồn & Render lại ngay cho folder vừa bị cut**:
   - Ngay sau khi cut dữ liệu khỏi folder dự phòng, phải tải nguồn mới hoặc nạp nguồn thay thế vào `D:\video goc\<spare>` và chạy batch render random ngay (`random_batch_render.py` với preset `preset_owner.json`) để kho luôn có sẵn video.
6. **Reset counter khi xây lại video**:
   - Khi nick làm lại video từ đầu, phải reset counter `Video Đã Đăng = 0` đồng bộ ở cả `TikN.xlsx` (cột 8) và `taikhoan_run_safe.xlsx` (cột 4) kèm backup trước khi ghi.
7. **Cập nhật Avatar độc lập**:
   - Sử dụng launcher `run_tiktok_upload_avatar.ps1 -Tik <N> -AssignmentManifest <path> -WorkerId <id> -ForceAvatarMachineList "<may>"` để force up avatar mới mà không kích hoạt flow đăng video. Sau khi xong, quy trình tự động dọn dẹp cache ảnh và đưa máy về Home.



### RESEED NICK — exact identity, destructive CUT, and spare-source replacement (2026-08-26)

Khi user yêu cầu đổi toàn bộ content của một nick vì source cũ sai niche, phải hiểu đây là một chuỗi có thứ tự cố định, không tự rút gọn hoặc đảo bước:

1. Resolve **exact account ID** từ nguồn mapping hiện hành. Không biến username gần giống (`hatien1511`/`hatien15118`) thành cùng một nick và không dùng row lịch sử/runtime log làm bằng chứng cuối. Nếu ảnh, log và workbook không khớp exact ID thì dừng trước destructive action.
2. Map account → machine + slot/TikN + source folder (`video gốc`) + render folder (`Folder Video`) từ đúng workbook hiện hành. Không suy luận chỉ từ số máy; không dùng mapping cũ hoặc workbook path legacy.
3. Preflight ownership: source/render đích phải thuộc đúng account; không có downloader/render/upload đang giữ chúng; ghi lại cặp đích trước khi xoá. Kiểm tra cả file số và file title-based.
4. Khi user đã yêu cầu reseed rõ ràng, yêu cầu đó là authorization cho đúng phạm vi destructive action đã nêu; không hỏi lại một câu xác nhận chung sau khi đã có đủ scope. Tuy vậy vẫn phải preflight và không được tự mở rộng sang folder khác.
5. Xoá sạch **cả** source cũ và render cũ của nick (video, avatar, cache theo scope), rồi chọn một spare source chưa render/chưa gán cho nick đang hoạt động, có ít nhất 45 MP4 hợp lệ. Việc “chưa render” phải đối chiếu artifact/render manifest hoặc workbook, không kết luận chỉ vì spare nằm ở dải số cao.
6. **CUT, không COPY**: chuyển nguyên bộ spare source vào source folder của nick; verify spare cũ không còn MP4/title files thừa. Không trộn nhiều channel vào một source folder.
7. Render random local vào render folder của nick bằng runner đúng machine/workbook/path Kibe. Ưu tiên `scripts/random_batch_render.py`/launcher đã kiểm chứng, `--randomize`, `--parallel 1`, preset chuẩn; không dùng launcher còn trỏ `D:\video goc may 2` hoặc `D:\TIKTOK-videonuoinick-admin` cho dữ liệu Kibe. Output phải là `1.mp4..N.mp4`, ffprobe-valid.
8. **Sau khi render đích xong mới bù spare**: chạy downloader cho source folder spare vừa bị CUT, giữ `min-videos >= 30`, state DB/output/ledger hiện hành; không reset toàn bộ kho và không chạy downloader đè với process khác.
9. Reconcile cuối: đích nick đủ video + avatar + mapping; spare đã được bù; DB/workbook chỉ cập nhật đúng account/folder; nếu bị ngắt giữa bước nào thì resume đúng bước đó, không xoá lại dữ liệu đã tạo.

Chi tiết checklist, evidence và recovery nằm ở `references/reseed-nick-content.md`.

### PITFALL: PowerShell NativeCommandError giết batch render (2026-08-11)



Triệu chứng: chạy vài máy OK rồi chết giữa máy kế với `FullyQualifiedErrorId : NativeCommandError`; log có dòng python `HASH: ... bytes` (progress hash file nguồn lớn 200MB+ in ra **stderr**).



Nguyên nhân: launcher dùng `& $python.Source @args 2>&1 | Tee-Object` kèm `$ErrorActionPreference = "Stop"` → PowerShell coi stderr output là lỗi → throw NativeCommandError dù python exit code = 0. File nguồn càng lớn hash càng lâu → càng dễ dính.



Fix (đã áp vào `run_tik3_random_render.ps1`):

```powershell

$prevEAP = $ErrorActionPreference

$ErrorActionPreference = "Continue"     # không fail vì stderr progress

& $python.Source @runnerArgs 2>&1 | Tee-Object -FilePath $log -Append

$ErrorActionPreference = $prevEAP

if ($LASTEXITCODE -ne 0) { throw "Render loi tai may $machine" }  # chỉ fail theo exit code

```

Kèm switch `-ResumeVerifyExisting` → truyền `--resume-verify-existing` cho `random_batch_render.py` để chạy lại từ đầu mà máy đã xong chỉ verify+skip, không render lại. Trước khi resume: xóa output folder dở của máy đang render lúc crash (tránh file hỏng giữa chừng).



## PITFALLS

- **PITFALL: BẢNG TĨNH `farm_account_info` & HIỆN TƯỢNG NICK LIVE MẤT BADGE SỐ MÁY TRÊN DASHBOARD (Hit 2026-09-22)**:
  - **Hiện tượng**: Dashboard (`tiktok_dashboard.py`) hiển thị danh sách nick LIVE (như `@anan36014`, `@cout13110`, `@haibich156`, `@huynhat1035`) nhưng cột số máy trống trơn (không có badge `M{may}`).
  - **Nguyên nhân cốt lõi**: Dashboard lấy số máy từ câu query `LEFT JOIN farm_account_info f ON r1.username = f.username`. Bảng `farm_account_info` trong SQLite `tiktok_tracker.db` chỉ được import tĩnh từ ngày 18-20/09 và KHÔNG có cơ chế tự động đồng bộ (auto-sync) từ danh bạ hợp nhất `taikhoan_run_safe_combined.xlsx`. Mọi nick mới reg hoặc nick được dời/khôi phục slot đều bị `may IS NULL`.
  - **Sự cố "Nick Lạc" sau khi Restore**: Nick `@anan36014` là nick thật của Máy 218 (reg ngày 16/09 với mail `schappachude360@hotmail.com`). Do từng bị ghi nhầm đè vào Folder 2 & 8, khi restore 69 nick Folder 2 từ backup cũ `bak_final.xlsx`, 2 dòng đó được trả về nick cũ khiến `@anan36014` bị tách khỏi danh bạ Excel Admin và không được map vào DB.
  - **Quy tắc chuẩn hóa**:
    1. Khi restore hàng loạt nick từ backup, BẮT BUỘC đối soát các nick mới sinh để dời sang slot còn trống (ví dụ Tik 4, Tik 5 của Máy 218) thay vì để nick bị rơi rụng khỏi danh bạ.
    2. Bổ sung bước tự động đồng bộ từ `taikhoan_run_safe_combined.xlsx` vào bảng `farm_account_info` của SQLite `tiktok_tracker.db` trước mỗi phiên Daily Tracker hoặc sau khi sync safe workbook.

- **PITFALL: ONEDRIVE DEHYDRATION (ERRNO 22) LÀM BỎ SÓT NẠP TOÀN BỘ CỤM ADMIN TRONG DAILY TRACKER (Hit 2026-09-22)**:
  - **Triệu chứng**: Daily Tracker buổi sáng chỉ nạp 627 tài khoản của Kibe (1..80), bỏ rơi hoàn toàn 80 máy của Admin (201..280).
  - **Nguyên nhân**: File `D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx` bị tính năng Files On-Demand của OneDrive chuyển sang trạng thái Offline / Dehydrated (`attrib A O`, attribute `0x401620`). Khi `openpyxl.load_workbook()` mở file, Windows ném `OSError: [Errno 22] Invalid argument`. Vòng lặp `load_farm_accounts()` bắt `except Exception: continue` mù quáng nên âm thầm bỏ qua file của Admin mà không có bất kỳ log lỗi nào.
  - **Quy tắc phòng ngừa**:
    1. Khóa pin file vĩnh viễn trên máy địa phương: `attrib -u +p "D:\OneDrive\TaadaaData\admin\taikhoan_run_safe.xlsx"`.
    2. Trong code đọc workbook, TUYỆT ĐỐI CẤM nuốt chửng `except Exception: continue`. Bắt buộc log warning/error và kiểm tra mã lỗi `Errno 22` để kích hoạt recall/pin file.

- **QUY TẮC NẠP DEFERRED KHI THIẾU `tracking_row` / `tik` (2026-09-17)**:
  - **Vấn đề**: File JSON deferred tracking (từ runner reg/login) có thể thiếu `tracking_row` và `tik` (chỉ có `stt`, `email`, `tiktok_id`). Trước đây hàm `_check_expected_row` trong `scripts/deferred_tracking_writer.py` lập tức chặn với `RESULT_MISSING_ROW_OR_TIK`.
  - **Cơ chế tự động resolve slot trống**:
    + Khi `tracking_row` hoặc `tik` bị thiếu/None, `_check_expected_row` gọi `resolve_tracking_slot(ws, stt, email_l)` để tìm slot phù hợp trên sheet:
      1. Ưu tiên hàng đã có email khớp (`row_email == email_l`) mà chưa có ID/Pass.
      2. Nếu không có hàng trùng email, bốc hàng trống đầu tiên của máy (`stt`) chưa có ID/Pass/Gmail.
    + Nếu resolve thành công: tự động gán lại `result["tracking_row"] = slot_row` và `result["tik"] = slot_tik` rồi tiếp tục flow kiểm tra điều kiện ghi (`READY`).
    + Nếu không tìm thấy slot: trả về `BLOCKED_DATA_CONFLICT` kèm blocker rõ ràng (`NO_EMPTY_TRACKING_SLOT` hoặc `slot_blocker`).

- **PITFALL: ĐỤNG ĐỘ NẠP DEFERRED KẾT QUẢ REG GÂY LỆCH NICK TRÊN 2 MÁY & CRASH TRẦN 8 ACC (2026-09-08)**:
  - **Triệu chứng**: Máy báo lỗi `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` hoặc crash batch reg ban đêm, dù file Excel hiển thị máy mới chỉ có 7 nick (vẫn còn slot trống).
  - **Nguyên nhân gốc rễ**: Khi 1 email được chạy trên 2 máy khác nhau (do bốc trùng target hoặc retry đè), script nạp deferred (`apply_deferred_tracking_results.py`) lọc dedup theo `written_at` mới nhất $\rightarrow$ nạp kết quả của máy sinh sau (ghi vào hàng của máy sau trong Excel) và bỏ rơi kết quả của máy sinh trước. Khiến máy sinh trước thực tế trên app TikTok đã lưu nick đó (đủ 8 nick), nhưng Excel vẫn để trống slot 8 $\rightarrow$ Preflight đọc Excel thấy trống lại tiếp tục cử máy đi reg $\rightarrow$ TikTok chạm trần 8 nick nên ẩn hoàn toàn nút "Thêm tài khoản".
  - **Quy tắc điều tra & xử lý khi lệch nick giữa 2 máy (User Invariant 2026-09-08)**:
    1. Khi phát hiện nghi vấn 1 nick bị map lệch giữa các máy: BẮT BUỘC kiểm tra thực tế trong app TikTok trên cả 2 máy liên quan (O(1) ATX dump XML / switcher screenshot).
    2. Nếu nick CHỈ có trên 1 máy: cập nhật lại Excel ghi đúng máy thực tế đang chứa nick đó.
    3. Nếu CẢ 2 MÁY CÙNG CHỨA NICK: **TUYỆT ĐỐI CẤM tự ý xóa nick trên máy hoặc tự sửa Excel, BẮT BUỘC báo cáo user để xin chỉ đạo xử lý**.
  - **Chốt chặn kỹ thuật đã bổ sung**:
    1. **Runtime Device Gate (`social_reg_v1.py`)**: Trong `tap_add_account`, trước khi tìm nút "Thêm tài khoản", kiểm tra số lượng node account trong dropdown (`_acc_count >= 8`). Nếu đủ 8 acc $\rightarrow$ ghi nhận `MACHINE_FULL_8_ACCOUNTS`, tự động dismiss dropdown về Home an toàn thay vì crash `RuntimeError`.
    2. **Hạ ngưỡng lọc tên ngắn**: Trong `_try_open_account_dropdown_once`, hạ ngưỡng width từ `>= 220px` xuống `>= 120px` để không bỏ sót các tên ngắn (như "Hà" 168px).
    3. **Preflight Sheet Pinning**: Trong `tiktok_target_eligibility.py`, cố định đọc sheet `'Tài Khoản'` khi đếm số nick hiện có, không dùng `_active_worksheet` để tránh đếm sai khi con trỏ Excel lưu ở sheet khác.

- **PITFALL: `DUPLICATE_MEDIA_BLOCKED` DO LỆCH CỘT 'VIDEO ĐÃ ĐĂNG' VỚI PROFILE/LEDGER THẬT (2026-09-02)**:
  - Triệu chứng: Script `tiktok-video` hoặc ca nuôi có upload hook dừng phiên với lỗi `upload_subprocess_nonzero` / `[DUPLICATE_MEDIA_BLOCKED] Exact media SHA-256 already verified for machine=M, account=X`, trạng thái `MANUAL_REVIEW` / giữ hiện trường.
  - Nguyên nhân: Tài khoản trên thiết bị thực tế đã đăng đủ K video và media-fingerprint ledger (`D:/CodexRuntime/tiktok-video/idempotency/media-fingerprints/<key>.json`) đã lưu `status=verified_success` cho video K, nhưng cột `Video Đã Đăng` trong file `TikN.xlsx` (và `taikhoan_run_safe.xlsx`) vẫn lưu giá trị cũ `< K` (vd: 1 thay vì 2). Runner tính `video_number = Video Đã Đăng + 1 = K`, bốc đúng video K (`K.mp4`) đã đăng và bị chặn bởi cơ chế chống upload trùng SHA-256.
  - **Quy tắc Vận Hành & Khắc phục Hàng Loạt (User Invariant 2026-09-02)**:
    1. Khi phát hiện lỗi này, **TUYỆT ĐỐI CẤM yêu cầu user gửi/báo từng máy lẻ tẻ**. BẮT BUỘC chủ động chạy scan và reconcile hàng loạt toàn farm trên tất cả 80 máy x 6 files TikN (`Tik1..Tik6.xlsx`) và `taikhoan_run_safe.xlsx` bằng script `auto_reconcile_ledger_workbook.py`.
    2. **Cơ chế Auto-Advance trong State Machine (`_handle_resolve_next_video`)**: Code upload đã được bổ sung `_auto_advance_verified_videos()`, tự động kiểm tra ledger: nếu video candidate đã `verified_success`, tự động nhảy cóc cursor sang video chưa đăng tiếp theo và đồng bộ số mới vào Excel ngay tại chỗ mà không dừng phiên.
    3. Đưa thiết bị về màn hình Home (`adb shell input keyevent 3`) để ca tiếp theo tự động bốc video tiếp theo `K + 1`. Chi tiết xem `references/workbook-video-count-drift.md`.



- **Path repo có space/chữ hoa khác thường** (`tiktok-luot nuoi acc` chứa space; `D:\Taadaa\Tiktok-video` chữ hoa T): `search_files`/rg IO error → **verify path thật bằng bash trước** (`cd /d/Taadaa && ls -d "tiktok-luot nuoi acc"`), rồi dùng `terminal` grep với quote: `grep -rn --include='*.py' -e 'pattern' "tiktok-luot nuoi acc"` (thêm `grep -v __pycache__ -e worktree -e .ai-runs` để tránh nhiễu build lib). Đừng giả định tên/path.

- **Sync an toàn = 1 writer duy nhất (chốt 2026-08-16, nâng cấp toàn diện 80 máy 2026-09-01, hoàn thiện auto-sync source config 2026-09-03)**: 
  - `taikhoan_run_safe.xlsx` là **Single Source of Truth duy nhất** cho toàn bộ 80 máy (1..80, 480 rows).
  - Wrapper `hermes_taikhoan_sync_cron.py` (chạy mỗi 5 phút) tự động đồng bộ theo 3 bước tuần tự:
    1. Đồng bộ 1-chiều ID từ `taikhoan_dat_v2_updated .xlsx` sang `Tik1..Tik6.xlsx` (`scripts/sync-tik-workbooks.py`).
    2. Build lại `taikhoan_run_safe.xlsx` (`scripts/sync-safe-workbook.py` kèm số video từ `Tik1..Tik6`).
    3. Tự động gọi `generate_config_from_safe_workbook()` (trong `scripts/generate_cron_source_config.py`) để đồng bộ trực tiếp cấu hình nguồn `D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json` cùng state files `feed_state.json`, `post_state.json` từ `taikhoan_run_safe.xlsx`.
  - **CẤM TỰ Ý XÓA/TÁI TẠO MANIFEST/COHORT NGẦM TRONG CRON SYNC (User Rule 2026-09-01)**: Tuyệt đối không được thêm các bước tự chế `shutil.rmtree` xoá thư mục `manifests/` hay `cohorts/`, không reset `feed_state.json` trong cron sync vì sẽ làm lệch hash SHA-256 đối soát digest của các phiên nuôi đang chạy dở và làm ngắt dừng hàng loạt máy. Việc re-pick manifest khi đổi ca/ngày do `tiktok_picker.py` đảm nhiệm.
  - **Cơ chế chạy ca/phiên của Runner**: Mọi runner chạy nuôi feed (`multi-machine-feed-session`), follow (`tiktok-follow`), upload (`Tiktok-video`) **CHỈ ĐỌC TRỰC TIẾP `taikhoan_run_safe.xlsx`** theo số máy và Row (1..6) tương ứng để thực thi trên máy thật. CẤM tự chế thêm tầng trung gian phức tạp làm cản trở quá trình chạy.

- **CẤU HÌNH LỊCH CRON PARITY LANES & LỘ TRÌNH WARMUP NICK MỚI (Row 5 & 6) (2026-09-01)**:
  - **Phân chia Parity LANES (Ngày Chẵn / Ngày Lẻ)**:
    + **Ngày Lẻ (Lane B)**: Ca 1 (Row 1 - 06:00) + Ca 2 (Row 3 - 12:30) + Ca 3 (Row 5 - 19:00).
    + **Ngày Chẵn (Lane A)**: Ca 1 (Row 2 - 06:00) + Ca 2 (Row 4 - 12:30) + Ca 3 (Row 6 - 19:00).
    *(Row 1 và Row 2 chỉ chạy buổi sáng ca 1; ca tối nhường cho Row 5 và Row 6)*.
  - **Lộ trình nuôi 20 ngày chuẩn cho dàn nick mới (Row 5 & Row 6)**:
    + **Giai đoạn 1 (Ngày 1..10 lịch - 5 ngày chạy thực tế)**: CHỈ lướt feed (15 phiên lướt), 0 đăng video, 0 follow để tích lũy cookie và trust score.
    + **Giai đoạn 2 (Ngày 11..20 lịch - 5 ngày chạy thực tế tiếp theo)**: Bắt đầu đăng 1 video/ngày chạy ở phiên cuối ca (đạt 5 video/nick), VẪN CHẶN follow.
    + **Giai đoạn 3 (Từ ngày 21 lịch trở đi)**: Nick đã có 10 ngày tuổi thực tế + đạt $\ge 5$ video $\rightarrow$ Hệ thống tự động mở Gate Follow chéo ngoài farm (Module 2).

- **Sync an toàn = 1 writer duy nhất (chốt 2026-08-16)**: safe workbook hiện chỉ có 1 writer (`sync-safe-workbook.py` qua `single_writer_workbook_update` atomic — build lại toàn file + reopen-verify; 3 cột `May|Device ID|ID`). CẤM thêm nguồn ghi runtime thứ 2 (VD upload ghi `Video Đã Đăng` trực tiếp vào safe = race/corrupt OneDrive, y hệt lý do gốc tách safe khỏi upload). Kế hoạch thêm cột `Video Đã Đăng` (4 cột, dùng cho follow gate): **gộp vào CHÍNH cron sync hiện tại** — 1 process đọc taikhoandat_v2 (ID/serial) + Tik1..Tik6 (ID + Video Đã Đăng, acc không khớp file nào → ghi 0) → build lại safe → 1 lần ghi atomic. KHÔNG tạo cron thứ 2 (2 cron rebuild-from-source = process sau XÓA cột process trước vừa ghi, dù có writer-id lock). Upload vẫn chỉ ghi TikN. Follow gate đọc safe (read-only) theo ID nickname.

- **Nguyên tắc đối chiếu (user chốt 2026-08-16): mọi mapping cross-file theo ID account, không theo row/slot** — safe có 2–5 nick/máy nên row order không đáng tin; ID là key ổn định. (VD: sync video TikN → safe tìm row cùng ID; follow gate đọc Video Đã Đăng theo ID của nick đang chạy.)

- **Đồng bộ 1-based Account Slot Index khi đọc safe workbook (18/08)**:
  Mỗi máy trong `taikhoan_run_safe.xlsx` có cấu trúc 6 dòng vật lý tương ứng 6 slot (1..6). Khi các consumer repo (như `tiktok-follow`) đọc safe mapping để resolve `--account-row-index R`, bộ parser BẮT BUỘC phải tăng index cho mọi dòng của máy (kể cả dòng có ID trống `None`) thay vì bỏ qua rồi đánh số lại từ 1..N. Việc co nén index sẽ làm lệch slot khi gọi hook hoặc cron (vd: slot 6 bị biến thành slot 4 -> gây lỗi `CONFIG_ERROR: máy N không có account row 6`).

- **PITFALL: SERIAL DRIFT TRONG CÁC WORKBOOK CON TIK2..TIKN GÂY ACCOUNT_MISSING KHI ĐĂNG VIDEO (2026-09-02)**:
  - **Triệu chứng**: Khi kết thúc ca nuôi (phiên 3 đăng video) của Row 2 (`Tik2.xlsx`) hoặc Row 3 (`tik3.xlsx`), một nhóm máy liên tục fail upload với lỗi `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
  - **Nguyên nhân**: Cột `device ID` (Serial) của nhóm máy đó trong `Tik2.xlsx` hoặc `tik3.xlsx` bị hoán đổi chéo lẫn nhau (ví dụ: máy 76 mang serial của máy 78, máy 78 mang serial của máy 76...). Khi runner upload chạy `--single-device <serial>`, nó tìm serial đó trong workbook và bốc nhầm target account của máy khác $\rightarrow$ app TikTok trên máy thật không có nick đó $\rightarrow$ `ACCOUNT_MISSING`.
  - **Quy tắc Kiểm tra & Khắc phục**:
    1. Lấy serial chuẩn từ `Tik1.xlsx` hoặc `PROXYgandienthoai.xlsx` làm chuẩn duy nhất.
    2. Trước khi chạy các ca upload Tik2..Tik6, đối chiếu parity serial toàn bộ 80 máy giữa `TikN.xlsx` và `Tik1.xlsx`.
    3. Backup workbook (`.bak-fix-serials-...xlsx`), chuẩn hóa lại đúng serial cho từng dòng máy, và chạy preflight test `--preflight` để xác nhận target account binding đúng máy.

- **PITFALL: `EXTRA_MACHINES` Serial Mapping trong `sync-safe-workbook.py` & Lỗi `TARGET_INVENTORY_CONFLICT` (2026-08-31)**:
  Khi `sync-safe-workbook.py` tái tạo `taikhoan_run_safe.xlsx`, nếu dict `EXTRA_MACHINES` (cho các máy 75..80) bị gán nhầm hoặc hoán đổi serial (vd: máy 78 mang serial máy 76 `9885b64d56305a3731`), các dòng của cùng một máy sẽ chứa serial khác nhau. Điều này khiến `_detect_clean.py` bên `Tiktok_Reg` ném lỗi `TARGET_INVENTORY_CONFLICT: machine X` và chặn toàn bộ batch reg.
  Bảng serial chuẩn cho cụm máy 75-80:
  - Máy 75: `ce011711d4cd802905`
  - Máy 76: `9885b64d56305a3731`
  - Máy 77: `ce05160595e7953b04`
  - Máy 78: `ce0916090a9d320a01`
  - Máy 79: `ce0516059d279f3e03`
  - Máy 80: `ce061606cd45950405`
  Luôn đối chiếu serial với `Tik1.xlsx` và `adb devices` trước khi rebuild safe workbook.

- **Bỏ verify / switcher khi chạy qua feed hook `--skip-identity-verify` (18/08)**:
  Khi cờ `--skip-identity-verify` được bật: Feed runner trước đó đã chọn đúng tài khoản. Follow engine gán thẳng `active_account_handle = row.tik_id` và chạy ngay, không verify vị trí nick trên UI. Không phụ thuộc vào số lượng row hay thứ tự nick.

- **PITFALL: Trùng lặp ID / Lệch cột DAT gây dồn Slot trong Safe Workbook & Mismatch Cohort Identity (2026-08-31)**:
  - Khi chỉnh sửa `taikhoan_dat_v2_updated .xlsx`, nếu dán trùng ID tài khoản ở 2 slot của cùng một máy (vd: Slot 2 và Slot 3 cùng mang ID `darrellppere17`) hoặc lệch cột (Device ID bị đẩy sang cột trống bên phải):
    1. `compare_tiktok_accounts.py` sẽ ném `CONFIG_ERROR: machine X has conflicting serials in workbook`.
    2. `sync-safe-workbook.py` có cơ chế deduplicate ID (`seen_ids`) nên sẽ loại bỏ dòng trùng, kéo dồn tài khoản ở slot dưới lên slot trên (vd: nick Slot 4 `phanmai0464` bị nhảy lên Slot 3 trong `taikhoan_run_safe.xlsx`).
    3. Cron runner khi chạy ca 3 (`--account-row-index 3`) đọc ra `phanmai0464`, nhưng frozen cohort manifest lập từ đầu ngày vẫn ghi nhận slot 3 là `darrellppere17` $\rightarrow$ kích hoạt fail-closed `cohort target identity mismatch: expected_username` và dừng phiên giữ hiện trường.
  - **Quy trình chuẩn hóa & khôi phục khi gặp lỗi**:
    1. Backup `taikhoan_dat_v2_updated .xlsx` trước khi sửa.
    2. Rà soát đúng 8 dòng vật lý của máy `(m-1)*8+1 .. (m-1)*8+8`: chuẩn hóa đúng 10 cột, đưa ID vào đúng Slot 1..3, xóa sạch thông tin ở các slot trống 4..8 (giữ nguyên Máy, Folder Video, Device ID).
    3. Chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-tik-workbooks.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"` để cập nhật `Tik1..Tik6.xlsx`.
    4. Chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"` (và đồng bộ sang `D:/Taadaa/tiktok-luot nuoi acc/data/taikhoan_run_safe.xlsx`).
    5. Kiểm định bằng `python "D:/Taadaa/tiktok-log-in/scripts/compare_tiktok_accounts.py" --workbook "..." --machines <M> --adb-path "..." --plan-only` đạt `PLAN_OK`.
    6. Chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_taikhoan_sync_cron.py"` để lưu state hoàn tất.

- **CẤM gom Tik1+Tik2 (nhiều nick/máy) vào 1 workbook (phân tích code 2026-08-16)**:

  user từng hỏi "gom tik1+2 thành 1 file cho tiện, follow đọc 1 chỗ là đủ" —

  KHÔNG được. Lý do kỹ thuật (đã đọc `Tiktok-video/scripts/tiktok_workflow/account_source.py`):

  `_read_row_from_xlsx` dòng 266-281 máy mode = **first-row only** (chọn row đầu

  khớp Máy rồi break); device mode = dòng đầu khớp serial → nick 2+ cùng device

  trong 1 file KHÔNG BAO GIỜ được chọn → gom = vỡ chọn nick. Thêm nữa: 2 runner

  upload ghi cùng `Video Đã Đăng` (`update_video_number` monotonic cursor) vào 1

  file = lost update / OneDrive conflict — tách file là cơ chế chống race.

  Follow repo KHÔNG cần gom: nó đọc `taikhoan_run_safe.xlsx` (nguồn nick thật

  đa row/máy); file Tik chỉ để đọc cột `Video Đã Đăng` làm gate (row1→Tik1,

  row2→Tik2, row3→tik3). Khi user đề xuất gom: giải thích 2 lý do trên, giữ 3 file.

- **MÔ HÌNH VẬN HÀNH 6 ACC/MÁY (User quy chuẩn 2026-09-08)**:
  - Farm 80 máy × 6 acc = 480 acc/đợt. Mỗi máy chạy 3 ca/ngày (1 acc/ca), luân phiên ngày chẵn (Slot 1, 2, 3) và ngày lẻ (Slot 4, 5, 6) để mỗi acc hoạt động cách ngày (2 ngày/lần).
  - Nuôi 60–80 ngày (đăng 30–40 video) + follow chéo nội bộ để cán mốc 1,000 follow an toàn trước khi xuất bán và reset máy về mặc định.
  - Khi máy đã đủ 6 ID TikTok, detector `_detect_clean.py` BẮT BUỘC loại bỏ máy, không cấp thêm mail reg.

- **PITFALL TRÙNG MAIL NGUỒN & DEFERRED DEDUP GHI ĐÈ EXCEL (Root cause 2026-09-08, ref: `references/cross-machine-duplicate-email-and-deferred-tracking-dedup.md`)**:
  - Khi 1 email bị gán trùng cho 2 máy trong kho nguồn (`gmail_clean_v2.xlsx`), nếu máy B chạy sau đăng nhập/reg trúng email máy A đã reg (chưa kịp merge deferred JSON), cả 2 máy sẽ cùng giữ 1 nick.
  - Tool merge `apply_deferred_tracking_results.py` dedup theo `written_at` mới nhất sẽ ghi đè row máy B lên Excel và bỏ rơi máy A, gây lệch pha dữ liệu và kịch trần 8 acc trên app.
  - Khi phát hiện 2 máy cùng chứa 1 acc: BẮT BUỘC dừng lại báo cáo User chỉ đạo, không tự ý sửa.

- **BẪY LỆCH CHỈ SỐ HÀNG VẬT LÝ EXCEL VS FOLDER VIDEO (PHYSICAL ROW = FOLDER VIDEO + 1, Hit 2026-09-21)**:
  - **Triệu chứng & Cạm bẫy**: Khi điều tra log/báo cáo hoặc ghi nhận "Row 211 bị đè, Row 215 còn trống", người vận hành thường nhắc đến **số `Folder Video` (Cột B)** chứ KHÔNG PHẢI chỉ số hàng vật lý 1-based của Excel.
  - **Công thức bất biến**:
    $$\text{Folder Video} = (m - 1) \times 8 + k$$
    $$\text{Excel Physical Row} = 1 + \text{Folder Video} = 1 + (m - 1) \times 8 + k$$
    (với $m$ là số Máy 1..80, $k$ là Slot 1..8).
  - **Hậu quả nếu nhầm lẫn**: Truy cập nhầm `ws.cell(211, ...)` thay vì `ws.cell(212, ...)` sẽ thao tác lệch 1 hàng lên slot phía trước (Slot 2 thay vì Slot 3), dẫn đến ghi đè nhầm tài khoản đang sống và làm hỏng toàn bộ cấu trúc dữ liệu của farm.
  - **Quy tắc bắt buộc**: Trước khi đọc/ghi theo số "Row" được báo cáo, luôn kiểm tra giá trị Cột A (`Máy`) và Cột B (`Folder Video`). Nếu `ws.cell(r, 2).value != folder_target`, phải dừng lại và quy đổi lại theo công thức chuẩn `r = folder_target + 1`.

- **HARD GUARD CHỐNG GHI ĐÈ TÀI KHOẢN TRONG RUNNER & DEFERRED WRITER (Hit 2026-09-21, hoàn thiện chặn cả khi mail cũ trống)**:
  - **Bối cảnh**: Khi nạp nick reg mới từ file kết quả deferred tracking (`scripts/deferred_tracking_writer.py`) hoặc chạy trực tiếp (`social_reg_v1.py` hàm `upsert_tracking_account`), nếu logic resolve nhầm sang hàng đã có nick hoặc bị lệch hàng, code có thể vô tình ghi đè nick mới lên nick cũ đang sống (làm mất ID/Pass TikTok của acc cũ).
  - **LỖ HỔNG CẦN TRÁNH**: Điều kiện cũ `if (existing_id or existing_pass) and (existing_mail and existing_mail != new_mail):` sẽ bị `False` khi hàng cũ đã có ID/Pass nhưng ô email cũ đang trống (`existing_mail` là `""` hoặc `None`), dẫn đến việc vẫn ghi đè làm mất ID/Pass cũ!
  - **Cơ chế Hard Guard bắt buộc (Đúng chuẩn)**:
    1. Trước khi gán mảng `values` vào hàng mục tiêu (`check.row` hoặc `target_row`), BẮT BUỘC đọc trước giá trị hiện có: `existing_id`, `existing_pass`, `existing_mail`.
    2. Điều kiện chuẩn: `if (existing_id or existing_pass) and (not existing_mail or existing_mail != incoming_mail):` (đã có ID hoặc Pass, mà email cũ TRỐNG HOẶC email cũ KHÁC email mới $\rightarrow$ CHẶN NGAY LẬP TỨC):
       + Trong `deferred_tracking_writer.py`: Lập tức chặn ghi và trả về `TrackingWriteResult("BLOCKED_DATA_CONFLICT", blocker=f"OVERWRITE_REJECTED_EXISTING_ACCOUNT_{existing_id}_{existing_mail}")`.
       + Trong `social_reg_v1.py`: Raise ngay `RuntimeError(f"CRITICAL_OVERWRITE_PREVENTED: Cannot overwrite existing account @{ex_row_id} ({ex_row_mail}) at row {target_row} with new email {incoming_mail}")`.
    3. Quy tắc này đảm bảo fail-closed tuyệt đối: chỉ cho phép ghi vào hàng hoàn toàn trống hoặc hàng đã có đúng email đó đăng ký trước đó (trường hợp cập nhật thông tin bổ sung cho cùng 1 email).
    4. Unit test bắt buộc: Phải luôn có 2 unit test kiểm tra chặn ghi đè khi email cũ trống cho cả deferred writer và upsert tracking trong `tests/test_machine_full_8_acc.py`.
  - **CẢNH BÁO MÁY ĐÃ ĐỦ 8 NICK NHƯNG EXCEL THIẾU (USER INVARIANT 2026-09-21)**:
    - Khi script chạy reg bù mà phát hiện máy đã đủ 8 nick trên app TikTok (`_acc_count >= 8` / `MACHINE_FULL_8_ACCOUNTS`), nhưng Excel vẫn còn slot trống (do nick cũ chưa backfill hoặc lệch mapping):
    - TUYỆT ĐỐI CẤM im lặng bỏ qua hoặc tự ý xóa nick cũ để reg đè.
    - BẮT BUỘC báo ngay về Telegram: `"Máy đã đủ 8 acc (Lệch Excel - Cần kiểm tra backfill)"` để user kiểm tra, truy vết info nick trên máy và backfill vào Excel.

- **CỐ ĐỊNH ĐỌC SHEET `'Tài Khoản'` (CÓ DẤU)**: Khi đếm acc/slot trong `taikhoan_dat_v2_updated .xlsx`, CẤM dùng `_active_worksheet` (dễ đọc nhầm sheet user lưu gần nhất); BẮT BUỘC đọc đích danh sheet `'Tài Khoản'`.

- **QUY CHUẨN CỘT 'NGÀY TẠO' VÀ UPLOAD COOLDOWN GATE (2026-09-21)**:
  - **Cấu trúc 10 cột Master DAT (`taikhoan_dat_v2_updated .xlsx`)**:
    `0: Máy`, `1: Folder Video`, `2: ID`, `3: PASS`, `4: 2FA`, `5: GMAIL`, `6: PASS MAIL`, `7: NGÀY THÁNG NĂM SINH`, `8: NGÀY TẠO` (Cột I trong Excel), `9: device ID`.
  - **Cơ chế Upload Cooldown (`upload_preflight.py`)**:
    + Slot 1..4 (Row 1..4): Mặc định là nick cũ trưởng thành -> luôn Pass cooldown.
    + Slot >= 5 (Tik5, Tik6...): Bắt buộc kiểm tra `NGÀY TẠO`. Nếu ô trống (`None`/rỗng) hoặc unparseable $\rightarrow$ hệ thống kích hoạt fail-closed `account_creation_date_unverifiable` và CHẶN UPLOAD toàn bộ các máy này.
  - **Quy trình chuẩn khi backfill `NGÀY TẠO`**:
    1. **Backup bắt buộc trước khi sửa**: Tạo bản sao an toàn (vd `.bak_<timestamp>_filldate`).
    2. **Điều kiện lọc chuẩn**: Chỉ điền ngày tạo (vd `"2026-08-25"` để nick đủ tuổi và vượt qua chốt chặn benchmark) cho các dòng có Máy (1..80), Folder Video hợp lệ, và ID hợp lệ (khác `None`, rỗng, hoặc placeholder `ghjfghj`). Không điền vào các slot trống chưa có ID (`ID = None`).
    3. **Bảo tồn tuyệt đối cấu trúc**: Tuyệt đối CẤM làm thay đổi bất kỳ ô nào ở 9 cột còn lại; tổng số dòng sheet `Tài Khoản` phải giữ nguyên 641 dòng (1 header + 640 dòng dữ liệu).
    4. **Nghiệm thu & Đồng bộ**:
       + Kiểm tra lại bằng `check_upload_cooldown_eligibility(machine, slot)`.
       + Chạy ngay script đồng bộ: `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"`.

- **PITFALL: ĐIỀN DỒN SLOT TRỐNG KHI REG BÙ THEO CA (User Invariant 2026-09-12: "yêu cầu điền đsung row của nó")**:
  - **Triệu chứng**: Ca nuôi chạy Row 6 thiếu tài khoản, kích hoạt reg bù (`ensure_row_accounts.py 6`). Trên các máy mà slot trước đó cũng trống (như Máy 80 trống cả Row 5 và Row 6), thuật toán lấp đầy tuần tự (first-empty slot) đã điền nick mới vào Row 5 thay vì Row 6. Hậu quả là Row 6 vẫn `None`, ca nuôi Row 6 tiếp tục báo lỗi `account row 6 is empty, skipping`.
  - **Quy tắc bất biến**:
    1. Reg bù phục vụ ca nào (Row K / Slot K) thì BẮT BUỘC điền chính xác vào Row K của máy đó trong `taikhoan_dat_v2_updated .xlsx` (dòng `(m-1)*8 + K`) và `taikhoan_run_safe.xlsx`.
    2. TUYỆT ĐỐI CẤM điền dồn lấp các slot trống phía trước nếu chưa đến ca của slot đó.
    3. Đối soát 2 chiều giữa `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx` phải đảm bảo đúng index dòng `K` của máy đó nhận username vừa reg.

- **PITFALL: MASTER WORKBOOK THIẾU HÀNG VẬT LÝ LÀM THẤT THOÁT NẠP NICK REG BÙ (Hit 2026-09-13: "Nới rộng ra mỗi máy có 8 hàng r ghi lại info acc vào")**:
  - **Triệu chứng**: Khi reg bù thành công (sinh file tracking json `status: SUCCESS`), script `apply_results(row=7)` lại không thể merge thông tin nick vào `taikhoan_dat_v2_updated .xlsx` và `taikhoan_run_safe.xlsx`.
  - **Nguyên nhân gốc rễ**: Toàn bộ farm có 80 máy, đa số (76 máy) đã có đủ 8 hàng vật lý. Tuy nhiên, một số máy (cụ thể M76, M77, M78, M79) trong quá khứ chỉ được khởi tạo 6 hàng (Row 1..6). Khi reg bù chạy cho Row 7 (Ca 4 ngày lẻ), logic `len(machine_slots[stt]) >= row` không thỏa mãn (`6 < 7`), dẫn đến việc script bỏ qua và không ghi nhận username vào file Excel.
  - **Quy tắc bắt buộc khi nới rộng số hàng trên máy**:
    1. **Bảo toàn chuẩn 8 hàng vật lý cho toàn bộ 80 máy**: Mọi máy trong `taikhoan_dat_v2_updated .xlsx` BẮT BUỘC có đúng 8 hàng liên tục (từ Row 1 đến Row 8).
    2. **Gán Folder Video cho hàng mới**: Cần xác định Folder Video chưa sử dụng (`(m-1)*8 + slot`), không trùng lặp với các folder đã gán ở các slot trước.
    3. **Ghi nhận ngay thông tin nạp bù**: Sau khi chèn hàng vật lý mới, lập tức nạp đầy đủ thông tin tài khoản từ file tracking deferred (ID, PASS, GMAIL, PASS MAIL, CREATED, device ID) vào đúng Row chỉ định.
    4. **Đồng bộ Safe Sheet 1-writer**: Luôn chạy `sync-safe-workbook.py` với token `TAADAA_ALLOW_OVERWRITE_TOKEN` để build lại `taikhoan_run_safe.xlsx` đồng bộ 8 hàng cho 80 máy.
    - Chi tiết playbook nới rộng M76..M79 và cập nhật tracking JSON: xem `references/m76-m79-eight-row-expansion-and-deferred-tracking.md`.

- **PITFALL: TỔNG KẾT BATCH REG BÙ BỊ ĐẾM THIẾU DO TRỄ ĐỢT RUN & LỖI MAIL ĐÃ REG TIKTOK (Hit 2026-09-13)**:
  - **Triệu chứng**: User thắc mắc "sao reg thành công có 2 máy", trong khi thực tế farm có nhiều máy được reg thành công hơn.
  - **Nguyên nhân cốt lõi**:
    1. **Tách nhiều sub-batch ngầm**: Preflight reg bù tách tối đa 20 máy/đợt. Đợt 1 (00:05) chỉ có 2 máy pass (M77, M78) do nhiều máy bị vướng mail cũ đã có TikTok hoặc timeout. Đợt 2 (01:22) được cron đêm tiếp tục chạy và đã reg **thành công thêm 11 máy** (`M1, M2, M8, M10, M12, M14, M15, M16, M17, M26, M29`). Nếu coordinator chỉ soi run đầu tiên sẽ báo thiếu 11 máy.
    2. **Kho mail chưa lọc sạch**: 9/20 máy đợt 1 fail do mail trong kho `gmail_clean_v2.xlsx` đã từng được dùng đăng ký TikTok (`Tat ca 1 email da co TK TikTok`), khiến runner phải skip và cần mua bổ sung mail mới sạch hơn.
  - **Quy tắc điều tra**: Khi user hỏi về số lượng reg thành công, BẮT BUỘC quét toàn bộ các run trong ngày (`artifacts/runs/social-batch-all/YYYYMMDD*`) để tổng hợp đầy đủ số lượng tích lũy, không dừng ở run đầu tiên.

- **QUY TẮC CÁCH LY TỪNG ACC KHI MERGE KẾT QUẢ REG BÙ VÀO MASTER VÀ KÍCH HOẠT SYNC (User Rule 2026-09-14)**:
  - **Bẫy thư mục run rỗng**: Khi scan `runtime/artifacts/runs/social-batch-all`, nếu chỉ bốc `dirs[0]` thì rất dễ dính phải các run retry hoặc crash dở dang (chứa 0 file json). BẮT BUỘC duyệt qua danh sách `dirs` và lấy thư mục gần nhất **thực sự chứa các file `tracking_result_*.json`**.
  - **BẪY CO CỤM TUẦN TỰ (SPARSE PACKING) TRONG `sync-safe-workbook.py` LÀM RỖNG ROW 7/8 (Hit 2026-09-22)**:
  - **Triệu chứng**: Chạy sync safe workbook cho Admin (`admin/taikhoan_run_safe.xlsx`) ra đủ 640 hàng, nhưng Row 7 và Row 8 có 0 valid accounts, trong khi Master DAT Admin (`taikhoan_dat_v2_updated .xlsx`) có 133 nick ở Slot 7/8 (56 nick Slot 7, 77 nick Slot 8).
  - **Nguyên nhân cốt lõi**: `sync-safe-workbook.py` dùng vòng lặp `machine_entries[machine].append((serial, account_id))` rồi `entries[:8]`. Với file DAT thưa dòng như Admin (364 dòng thay vì 640 dòng cố định), máy chỉ có nick ở Slot 1, 7, 8 sẽ bị co cụm vào index 0, 1, 2 (Slot 1, 2, 3), đẩy các slot sau thành chuỗi rỗng (`""`), làm xóa trắng toàn bộ nick ở Row 7/8 và gây lệch ca chạy.
  - **Công thức Slot bất biến (Invariant cho cả Kibe và Admin)**:
    $$\text{slot} = ((\text{Folder Video} - 1) \pmod 8) + 1$$
    *(Vì cả Kibe: `(m-1)*8+slot` và Admin: `(m-201)*8+slot` đều là bội số của 8)*.
  - **Quy tắc bắt buộc khi sync Safe Workbook**:
    1. CẤM gom tuần tự `list.append()`. BẮT BUỘC khởi tạo cố định mảng 8 phần tử cho mỗi máy: `machine_slots[m] = [{"serial": "", "account_id": ""} for _ in range(8)]`.
    2. Đọc `Folder Video` (Cột B), tính `slot = ((folder - 1) % 8) + 1` và gán chính xác vào vị trí `machine_slots[m][slot - 1]`.
    3. Đảm bảo đúng 8 dòng cố định đại diện cho 8 slot (1..8) theo đúng thứ tự vật lý trong `taikhoan_run_safe.xlsx`.

- **BẪY SO SÁNH CỘT 2 VỚI SLOT (C2 == SLOT TRAP, Hit 2026-09-17)**:
    + **Triệu chứng**: Reg bù thành công 28 nick cho Row 7 (sinh file `tracking_result_*.json` SUCCESS), nhưng `taikhoan_run_safe.xlsx` vẫn giữ nguyên 0 nick ở Row 7 cho 28 máy đó.
    + **Nguyên nhân cốt lõi**: Trong `taikhoan_dat_v2_updated .xlsx`, Cột A (`c1`) là số Máy (1..80), nhưng Cột B (`c2`) là `STT_Tik` / `Folder Video` toàn cục (1..640), KHÔNG PHẢI số thứ tự slot 1..8! Đoạn code kiểm tra `c2 == slot` (vd `c2 == 7`) chỉ đúng duy nhất cho Máy 1 (Tik 1..8) và sai 100% cho Máy 2..80 (vd Máy 13 có Tik 97..104). Khi không khớp, script lầm tưởng chưa có dòng và tự động append acc mới xuống tận đáy sheet (dòng 642..669). Script `sync-safe-workbook.py` chỉ lấy 8 dòng đầu của máy (`entries[:8]`) nên 28 acc bị đẩy ở đáy bị bỏ sót hoàn toàn.
    + **Quy tắc bắt buộc**: Tuyệt đối CẤM kiểm tra `c2 == slot`. Dòng vật lý trong sheet master của Máy `m`, Slot `k` (1..8) BẮT BUỘC tính bằng công thức toán học hoặc đếm vị trí dòng thứ `k` của máy đó:
      $$\text{target\_row} = 1 + (m - 1) \times 8 + k$$
      Đồng thời, **Cột 2 (STT Tik / Folder Video) BẮT BUỘC bảo toàn giá trị cũ** `ws_trk.cell(target_row, 2).value` hoặc fallback `(m - 1) * 8 + slot`, **TUYỆT ĐỐI KHÔNG ghi đè thành giá trị `slot` (như 7)**.
  - **Cách ly từng account (Fault Isolation)**: Khi nạp danh sách tracking result vào `taikhoan_dat_v2_updated .xlsx`, BẮT BUỘC bọc quá trình parse JSON và ghi cell của từng máy trong một khối `try...except` riêng rẽ. Một file JSON bị lỗi format, data rác hay mailto CẤM làm crash toàn bộ loop nạp của các máy khác.
  - **Khóa cứng vị trí dòng vật lý**: Dòng cần cập nhật trong Master Workbook luôn được tính chuẩn xác theo công thức:
    $$\text{target\_row} = 1 + (m - 1) \times 8 + \text{slot}$$
    (với $m$ là số máy / STT, và $\text{slot}$ là Row ca chạy $1..8$). Tuyệt đối không append thêm dòng ở cuối sheet làm lệch cấu trúc 640 dòng của 80 máy.
  - **Kích hoạt đồng bộ Safe Sheet ngay sau khi lưu**: Sau khi `wb.save(TRACKING_WORKBOOK)`, tự động kiểm tra và chạy `taikhoan_sync_cron_launcher.py` (ưu tiên `AppData/Local/hermes/scripts` hoặc fallback OneDrive shared) để đồng bộ dữ liệu vừa nạp sang `taikhoan_run_safe.xlsx`.

- **QUY TẮC ĐỒNG BỘ 3 NƠI CHO HERMES CRON SCRIPTS (2026-09-12)**:
  - Khi bảo trì hoặc sửa lỗi các script chạy cron nuôi acc (`tiktok_runner.py`, `feed_session_watchdog.py`...):
    1. Thư mục mã nguồn git: `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`
    2. Thư mục runtime thực thi trên máy Kibe: `C:\Users\Kibe\AppData\Local\hermes\scripts\`
    3. Thư mục chia sẻ chung cho toàn farm trên OneDrive: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`
    BẮT BUỘC đồng bộ đồng nhất cả 3 nơi. Nếu chỉ commit git mà không copy sang `AppData\Local\hermes\scripts`, scheduler sẽ tiếp tục chạy code cũ (stale runtime).
  - Trong cron runner, mọi lệnh gọi subprocess python bổ trợ BẮT BUỘC dùng `target_python()` (`D:\Taadaa\python-envs\automation\Scripts\python.exe`), cấm gọi `sys.executable` vì venv của Hermes không cài `openpyxl`.

- **QUY TRẮC TRÍCH XUẤT SERIAL TRONG `sync-safe-workbook.py` (Chống Bốc Nhầm Cột Pass/Mail làm Serial Máy, Hit 2026-09-13)**:
  - **Hiện tượng**: Khi cột `device ID` (cột 10) trong `taikhoan_dat_v2_updated .xlsx` bị điền nhầm chuỗi ngày tháng (vd: `23/08/2026`), nếu loop quét tự do qua mọi cell của row sẽ bốc trúng cột `PASS MAIL` (`Emma2004wOjd`, `d93310aa`...) thỏa mãn regex `SERIAL_PATTERN`, làm `taikhoan_run_safe.xlsx` ghi nhận 2 serial cho 1 máy và khiến `gmail_reg_v10.py` văng ngay: `RuntimeError: Device map has conflicting valid serials for machine(s): 1, 2, ... 80`.
  - **Quy tắc chuẩn hóa**: CẤM quét mù qua các cột tài khoản (pass, 2fa, mail). Chỉ kiểm tra cột serial danh định (`serial_col`) hoặc cột liền kề phía sau (`serial_col + 1` / cột 11) khi bị lệch do cột ngày chèn vào, kết hợp fallback `EXTRA_MACHINES` và `series.txt`.

- **QUY TẮC CÚ PHÁP CLI RUNNER TIKTOK 2FA (`run_batch_live_2fa.py`) TRONG WATCHDOG (Hit 2026-09-13)**:
  - Lệnh gọi batch live 2FA từ script watchdog sau ca trưa/tối bắt buộc dùng cờ `--live` và `--max-workers <N>`:
    `python run_batch_live_2fa.py --live --max-workers 10`
  - TUYỆT ĐỐI CẤM truyền cờ bịa `--all-online` hoặc `--workers` (sẽ bị `argparse` quăng lỗi cú pháp Exit Code 2 làm dừng toàn bộ chuỗi).

- `taikhoan_dat_v2_updated .xlsx` — DẤU CÁCH trước .xlsx; dùng sai path fail ngay.

- **ADB & CỤM PHONE FARM TRÊN MÁY KIBE (2026-09-13)**:
  - Binary `adb.exe` chuẩn nằm tại `C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe` (không có trong PATH hệ thống). Khi thực thi ADB lệnh đơn qua Python/Terminal, luôn resolve binary từ đường dẫn này nếu `which adb` trả về `None`.
  - Thiết bị và row trong `taikhoan_dat_v2_updated .xlsx`: Cột J (`device ID`) chứa hardware serial chuẩn của thiết bị. Ví dụ Máy 46 có serial `ce0916092531413504`, tương ứng Row 362 (Slot 2 của M46).

- Sheet REG: `Tài Khoản` (có dấu). Sheet file Tik: `TaiKhoan` (không dấu).

- Sheet `Hashtag theo Folder` cột `Folder Nguồn` là SỐ folder nguồn (81-160/161-240), KHÔNG phải số máy — đừng lấy làm máy.

- Backup trước mọi ghi (`.bak-<mô tả>-<timestamp>.xlsx`), verify lại bằng đọc + đối chiếu DB sau khi ghi.

- openpyxl không mở được file backup đuôi lạ (`.bak-...` không có .xlsx) — phải copy sang tên `.xlsx` tạm.

- Tik1 đã đăng: KHÔNG bao giờ đổi folder/ID/video gốc của Tik1 (video đã lên TikTok, đối chiếu bằng workbook).

- Máy 74: từng fail `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` / `VIDEO_PICK_HOME_NOT_REACHED` + `DEVICE_LOCK_FAILED` (proxy readiness timeout) — root cause các lần 11:41/12:09 là **VPN tun0 chưa lên** (watcher cũ crash vì wheel automation-core thiếu `auto_enable_wifi`); sau khi rebuild wheel + restart watcher, tun0 lên, máy 74 đã về Home feed và sẵn sàng upload (Tik1 máy 74: `muyduyen4589`, folder 585, đã đăng 6, video tiếp theo = 7). Trước khi retry upload bất kỳ máy: check `tun0` up + Vichanger process + device lock sạch.



## VIDEO PICK / UPLOAD SAFETY (đã xác nhận m74, 2026-08-12)



- MediaStore xác nhận file push đã index **không chứng minh** tile tọa độ trong TikTok picker là đúng file.

- Không dùng fallback chỉ dựa vào "newest tile", duration overlay, vị trí top-left, hoặc thumbnail mơ hồ để chọn video. Nếu picker không lộ filename/album Download và không có identity match duy nhất → `VIDEO_PICK_TARGET_UNVERIFIED`, fail-closed, không tap.

- Hướng sửa an toàn: push vào album/path định danh riêng, mở album Download/Movies bằng selector; nếu vẫn không xác nhận được filename thì dừng. Visual frame matching chỉ là fallback khi có ngưỡng similarity + margin duy nhất + screenshot/recapture evidence.

- Máy 74 run cuối: target `D:\TIKTOK-videonuoinick\585\7.mp4` đã push/index, nhưng code chọn tile `(180,546)` bằng duration heuristic → không đủ chứng minh đúng target; workbook vẫn `Video Đã Đăng=6`. Không retry live trước khi sửa handler.

- MANUAL_REVIEW giữ lock dạng `handoff`; process chết để lại cặp `machine_N.lock.json` + `serial_<serial>.lock.json`. Chỉ dọn sau khi xác minh PID owner chết; với protocol-v2 ưu tiên takeover/reclaim có audit của core, không hand-delete lock sống; nếu xử lý legacy stale lock thì luôn xử lý cả hai loại.

- **Static helper call**: `_video_frame_tile_similarity` (giống `_image_correlation`) là class-level helper — gọi qua `StateMachine._video_frame_tile_similarity(frame, tile)`, KHÔNG gọi `self._video_frame_tile_similarity(...)` (sẽ truyền thừa `self` → `takes 2 positional arguments but 3 were given` làm identity verify fail hết tile). Test unit mock không bắt được lỗi này; smoke test thật bằng 2 ảnh PIL mới thấy.



## LIVE CANARY ACCEPTANCE (bắt buộc sau khi sửa upload)



- Test xanh chưa phải live success. Khi user yêu cầu sửa lỗi upload, phải chạy live canary đúng machine/account/video sau khi test; không kết luận từ exit code riêng.

- Trước chạy: preflight đúng serial, `tun0`/VPN up, Vichanger ready, cả machine+serial lock sạch hoặc reclaim hợp lệ, target account/video number được bind.

- Sau chạy chỉ báo `SUCCESS` khi đồng thời có: report `status=SUCCESS`, `post_verified=True`, profile tile count tăng baseline+1, SHA/fingerprint post-verify nếu workflow cung cấp, workbook đúng `workflow_workbook` trong live config tăng counter, và cả hai lock đã release.

- **CHẶN FALSE POSITIVE (sự cố m74 2026-08-12)**: report `SUCCESS` + `post_verified=True` KHÔNG phải bằng chứng. Video từng bị báo đã đăng khi thực tế chưa lên profile (receipt cũ `UNKNOWN` + scan 1 viewport đếm thiếu tile → "increment 3→4" giả → ghi workbook sai). Bắt buộc kiểm tra cả 3 lớp bằng chứng trước khi báo DONE:

  1. **Receipt** `idempotency/post-attempts/machine_<N>_video_<M>.json`: phải có `post_submission_state=ACCEPTED` + `post_tapped_at` + `post_submission_accepted_at`. `UNKNOWN` (tap timeout, thiếu timestamp) = chưa chứng minh đăng → không success, không ghi workbook (COMPAT-POST-VERIFY-004).

  2. **Profile scan reliable**: log phải có `viewports >= 2` cả baseline lẫn sau (`_profile_scan_is_reliable`, COMPAT-POST-VERIFY-005). "Không tìm thấy scroll container; dừng ở viewport 1" = count không đáng tin, increment là giả.

  3. **Ảnh độc lập**: chụp profile thật trước/sau, so danh sách tile bằng vision — phải thấy tile MỚI xuất hiện (user từng yêu cầu "Gửi hình ảnh xem"). Lưu ý mở profile: tab Hồ sơ = (972,1883); tap (540,1840) là nút + → mở composer, KHÔNG phải profile.

- Chi tiết đầy đủ sự cố + cách dọn state để retry: `references/m74-verify-false-positive-20260812.md`.
- Quy trình thay thế / reseed nội dung nick bị dính gậy, toxic comment, nhạy cảm: `references/quick-reseed-playbook.md` và `references/reseed-nick-content.md`.
- Sự cố trùng avatar giữa các Row do xung đột namespace folder video vs video gốc trong `path_resolver.py` & quy tắc resolve avatar chuẩn: `references/avatar-namespace-conflict-and-resolver-rules-20260911.md`.
- Sự cố lệch dòng c2==slot trong apply_results nạp acc xuống đáy sheet master và quy trình reconcile 28 acc Row 7: `references/c2-slot-trap-and-deferred-merge-reconcile-20260917.md`.
- Sự cố Nick mồ côi do bị ghi đè slot trong Master DAT khi nạp reg bù (`ahmetsguthe17` Máy 1) & quy trình điều tra backup khôi phục: `references/orphan-account-dat-overwrite-and-recovery.md`.
- Sự cố trùng kênh nguồn giữa các folder do lọt gate trong `download_by_niche.py` (chỉ check bảng `folders` bỏ sót bảng `videos`) & quy tắc khóa chặt UNION check: `references/source-channel-collision-and-downloader-gate.md`.
- Playbook điều tra và xử lý sự cố Preflight Reg Bù ném lỗi `[04_add_account] MACHINE_FULL_8_ACCOUNTS` (máy trên app đã đủ 8 nick nhưng Excel bị sót dòng None): `references/preflight-reg-bu-machine-full-8-accounts-triage.md`.
- Quy chuẩn phát hiện máy đủ 8 acc (resource-id `ndk`), Hard Guard chống ghi đè tài sản và cảnh báo Telegram Lệch Excel Backfill: xem `references/machine-full-8-accounts-mismatch-and-alert-protocol.md`.
- Quy tắc cảnh báo máy đủ 8 nick lệch Excel về Telegram & Hard Guard chống ghi đè tài sản (kể cả khi mail trống): `references/machine-full-8-acc-mismatch-and-hard-overwrite-guard.md`.
- Quy chuẩn audit và sửa lệch ánh xạ Video Gốc giữa các workbook Tik1..Tik8 tránh trùng nguồn video: `references/cross-workbook-video-goc-audit-and-parity.md`.
- Quy chuẩn 1 Folder = 1 Kênh duy nhất, giải mã hiện tượng đa kênh trong folder từ dữ liệu lịch sử tháng 8 & kỹ thuật kiểm tra 0 duplicate video: `references/single-channel-per-folder-and-source-collision-triage.md`.
- Quy chuẩn mở rộng Tik 7 & Tik 8, auto-sync keyword/hashtag toàn diện (All Tik 1..8) từ state.db và nguyên tắc báo cáo Farm Alert sau ca tối: `references/tik7-tik8-all-tik-keyword-sync-and-avatar-alert.md`.
- Gắn up-avatar ngay sau reg thành công trong Tiktok_Reg & xử lý phôi trắng Slot 7/8: `references/reg-success-avatar-attachment-rules.md` (Module chuẩn `avatar_after_reg.py` + tests `test_avatar_after_reg.py`).
- Thiết kế hook đăng video phiên cuối mỗi ca (Preflight Gate, verify nick, video integrity, Parity snapshot): `references/feed-shift-upload-hook-pattern.md`.
- Xử lý lỗi lệch nick switcher (`account-switcher-missing-expected`), swap nick Excel và sửa lệch cột DAT (Case Máy 10): `references/account-switcher-missing-expected-and-serial-shift-recovery.md`.
- Xử lý TikTok Account Switcher Placeholder Alias (`user<digits>`), lệch cột Cột 10/11 DAT và xử lý Stale Post Receipt dở dang (`POST_SUBMISSION_UNKNOWN`): `references/account-switcher-placeholder-alias-and-stale-receipt-triage.md`.
- Xử lý placeholder alias TikTok (`user<digits>`), chuẩn hóa lệch Cột 10/11 Master DAT và dọn stale post attempt receipt (Case Máy 3): `references/account-switcher-placeholder-and-stale-receipt-recovery.md`.
- Chuẩn hóa fallback 3-tier cho `atomic_workbook_update` (import, dynamic path, atomic lock, backup, retry Windows PermissionError, BytesIO in-memory read & fallback `.bak`): `references/atomic-workbook-update-fallback-pattern.md`.
- Kỹ thuật atomic write & backup `.bak` cho `sync_all_tik_keywords.py` và quy tắc deploy 3 vị trí (local, git deploy, OneDrive cron): `references/atomic-workbook-update-fallback-pattern.md`.
- Quản lý Avatar hợp nhất chéo host Kibe (1..80) & Admin (201..280), Single Source of Truth từ TikTok Tracker Dashboard và cơ chế tự động đối chiếu số máy (Auto-Resolve Machine ID): xem `references/unified-cross-host-avatar-management-and-machine-mapping.md`.
- Phương pháp kiểm toán tài khoản toàn Farm Kibe & Admin và tính toán nhu cầu mua Hotmail Graph API bù theo chuẩn 8 acc/máy: xem `references/farm-wide-account-audit-and-hotmail-procurement-20260919.md`.
- Hướng dẫn điều tra & quét cảnh báo sớm đứt gãy chuỗi video tuần tự (`video_not_rendered` / `Video Đã Đăng + 1`): xem `references/video-render-sequence-gaps-triage.md`.
- Chi tiết kiến trúc phân lập Sổ cái Vận hành vs Danh bạ Follow gộp toàn Farm Kibe & Admin (`taikhoan_run_safe_combined.xlsx`), phán quyết của Sol và Hard Gate Anchor Mode 2: xem `references/unified-safe-workbook-vs-separated-operational-workbooks.md`.
- Sự cố ghi đè xóa nick cũ khi nạp deferred apply, cơn thịnh nộ tài sản user, kết quả đối soát 27 nick bị mất và quy trình khôi phục: xem `references/deferred-apply-overwrite-incident-and-account-restoration-20260921.md`.
- Công thức chuẩn Folder Video cụm Admin (1..640 theo `(STT-201)*8+Slot`), giải mã dị biệt folder 2106/2108 và cơ chế Hard Guard chống ghi đè: xem `references/admin-folder-video-formula-and-anti-overwrite-guards-20260921.md`.
- Quy trình chuẩn hóa Folder Video Admin Master từ Tik1..Tik8 và đồng bộ sang taikhoan_run_safe_combined.xlsx: xem `references/admin-master-folder-video-reconciliation-and-safe-sync.md`.
- Sự cố co cụm tuần tự (Sparse Packing) trong `sync-safe-workbook.py` làm trôi dạt Slot & rỗng hoàn toàn Row 7/8 (133 nick Admin bị trôi): xem `references/sync-safe-workbook-slot-sparse-packing-pitfall.md`.
- Sự cố bảng tĩnh `farm_account_info` làm mất badge số máy trên Dashboard & OneDrive Dehydration (Errno 22) làm sót cụm Admin: xem `references/dashboard-farm-account-info-sync-and-onedrive-dehydration-triage.md`.
- **QUY TRÌNH CHUẨN DỌN DẸP SLOT DUPLICATE TRÊN MASTER DAT & ĐỒNG BỘ COMBINED SAFE (2026-09-23)**:
  1. **Tạo backup an toàn**: Trước khi can thiệp, sao lưu `taikhoan_dat_v2_updated .xlsx` thành `.bak_clean_duplicates_<timestamp>.xlsx` và kiểm tra dung lượng/tồn tại.
  2. **Quy tắc reset cột tài khoản (Columns C..I)**:
     - Khi phát hiện slot duplicate (trùng nick giữa 2 slot/folder): chỉ reset trắng các cột thông tin tài khoản: Cột C (`ID`), D (`PASS`), E (`2FA`), F (`GMAIL`), G (`PASS MAIL`), H (`NGÀY THÁNG NĂM SINH`), I (`NGÀY TẠO`) về `None`.
     - **BẢO TOÀN TUYỆT ĐỐI**: Cột A (`Máy`), Cột B (`Folder Video`), và Cột J (`device ID`). CẤM xóa dòng vật lý hay làm xô lệch cấu trúc 640 hàng của 80 máy.
     - Bảo toàn nick gốc tại slot trước đó nguyên vẹn.
  3. **Chuỗi đồng bộ 2 bước bắt buộc**:
     - Bước 1: Chạy `python "D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py"` để rebuild `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` từ Master DAT.
     - Bước 2: Chạy `python D:/Taadaa/tools/sync_combined_safe_workbook.py` để đồng bộ cả Kibe (1..80) và Admin (201..280) sang `D:\OneDrive\TaadaaData\taikhoan_run_safe_combined.xlsx`.
  4. **Post-verify**: Đọc lại workbook kiểm tra các ô C..I của slot duplicate đã `None`, nick ở slot gốc vẫn nguyên vẹn, và số lượng active UIDs trên file combined khớp kỳ vọng.

- **Đường dẫn workbook là acceptance data**: live m74 dùng `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx`; không dùng file legacy `D:\OneDrive\Tiktok\Tik1.xlsx` để kết luận. Nếu report nói đã update nhưng workbook đọc khác path còn cũ, phải reconcile path trước khi báo.

- **KỶ LUẬT TUYỆT ĐỐI KHI PREFLIGHT VALIDATOR / SYNC CRON BÁO LỖI DUPLICATE/CONFLICT**:
  - **CẤM BẢO USER TỰ SỬA**: Tuyệt đối không bao giờ thông báo cho user "chờ anh xử lý file Excel", "sửa lại 1 trong 2 file Excel để sync chạy tiếp". Hành vi này gây bức xúc nghiêm trọng ("Đkm", "Sửa cho tao").
  - **BẮT BUỘC CHỦ ĐỘNG TRACE & FIX**:
    1. Trích xuất exact `(machine, slot, file)` từ validator.
    2. Tra cứu `tiktok_tracker.db` (`snapshots`, `account_mapping`, `farm_account_info`) + `session_search` để tìm nick chính chủ của email đó.
    3. `curl` TikTok profile để phân loại: Nick LIVE có video/follower -> khôi phục ID chính chủ; Nick NOT FOUND (10221) -> email copy trùng, reset về `None`.
    4. Sao lưu timestamp, patch cả DAT và `tikN.xlsx`, chạy `excel_preflight_validator.py --exit-on-error` đạt PASS rồi kích hoạt sync cron bù. Xem chi tiết: `references/excel-preflight-validator-conflict-resolution.md`.

- Nếu post tap timeout hoặc verify lạc surface (LIVE/profile khác), trạng thái là `UNKNOWN`/`MANUAL_REVIEW`; không repost mù, không tăng workbook thủ công.

- Quy trình rollback code: giữ baseline commit/sha trước patch; trước commit dùng `git diff` + `git restore --source=<baseline> -- <file...>` cho đúng file scope, không `git reset --hard` vì có thể xóa dirty render launcher; sau commit dùng `git revert <patch-commit>`. Live artifact/workbook không rollback bằng git.



## SAFE LOCAL RENDER RESUME — workbook-driven and fail-closed



Use this section when resuming Tik3/Tik2 local rendering for a bounded output-folder range.



1. **Inspect before execution.** Load the workbook with `openpyxl.load_workbook(path, read_only=True, data_only=True)`, print the actual header row and relevant rows, then close the workbook before starting FFmpeg. Do not assume `machine/output/source` headers or assume an `sttvideo` column exists.

2. **Choose the launcher based on its contract.** Prefer `run_tik3_random_render.ps1`, whose Tik3 mapping is `[0]=machine`, `[3]=Folder Video/output`, `[4]=video goc/source`. `scripts/tik3_multi_batch.py` IS usable with Tik3.xlsx since 2026-08-16 (its `find_headers` now falls back to `Folder Video` when `sttvideo` is absent — commit in-repo; lệnh chuẩn: `--start-output <folder đầu> --start-source <nguồn đầu> --count 10 --min-videos 45 --parallel 1 --allow-existing-output --resume-complete --execute`). `--resume-complete` skips only folders with FULL 45 mp4; partial folder (<45) needs `--allow-existing-output` so batch_render skips the videos already rendered and finishes the rest — NEVER delete the partial mp4s (batch_render self-skips existing outputs; deleting forces a full re-render). `source_map_workbook` doesn't work for Tik3 (maps by output−1 but folder range jumps +8/máy) — let the script auto-increment source from `--start-source`. Do not use `run_tik3_resume_from_323.ps1` (legacy).

3. **Preserve mapping anchors.** If the workbook contains only one row per machine/slot anchor (for example output anchors 323, 331, 339, 347, 355), retain all anchor rows even when processing a split range. Derive intermediate folders only from a previously verified folder-block rule; never compute a source map from an incomplete filtered subset, because split workers can otherwise produce `None` mappings.

4. **Build an explicit allowlist.** Process only requested output numbers. Maintain an explicit protected-complete set and skip it before invoking any renderer. A folder with valid MP4s must never be passed with `--overwrite`; for incomplete folders use `--resume-verify-existing`. Use `--overwrite` only when the folder is proven completely empty and the user explicitly permits it.

5. **Keep the operation local-only.** Use only local source/output paths, FFmpeg/FFprobe, and the renderer. Do not run upload/login code, device automation, API clients, or network preflight. Prefer `--parallel 1` per renderer; if wall-clock parallelism is needed, split disjoint output allowlists and keep each renderer at one FFmpeg worker.

6. **Audit and verify.** Create a run directory under `D:\CodexRuntime\tiktok-video\batch-runs\` containing the launcher log, per-output stdout/stderr, source file lists, and a mapping snapshot. After completion, run FFprobe validation on every target folder, record total MP4s, valid MP4s, and newly created valid files, and report each folder as `done`, `skip`, or `error`. If interrupted, rerun the same allowlist with resume verification rather than deleting valid outputs.



Session detail and the reusable scoped-runner pattern are documented in `references/safe-local-render-resume.md`.



## VERIFY NHANH (script chuẩn)



1. REG: 80 máy × 8 dòng, folder `(m-1)*8+k` tăng dần.

2. TikN: ID = REG slot N (theo vị trí dòng), folder = `(m-1)*8+N`, video gốc = `(N-1)*80 + máy`.

3. Hashtag: keyword của folder nguồn khớp slug DB; pool không trống.

4. D:\TIKTOK-videonuoinick: folder slot 1,2 có ≥44 mp4.

5. **Trạng thái "đã đăng" của nick TikN: đọc thẳng `TikN.xlsx` cột `Video Đã Đăng`** — trống/0 = chưa đăng, số >0 = đã đăng N video. `Kiểm Tra Dữ Liệu = MISSING_ID` = thiếu ID (báo user điền, không chạy). Đừng đếm từ report.json khi câu hỏi chỉ là "máy nào chưa làm".



## LOCK CHẠY BATCH (re-enable 2026-08-16)



- 15/08 user bỏ auto device-lock (xem automation-core-consumer Device Lock Policy). **16/08 user ra lệnh "Lock lại khi chạy"** → runner `run_tiktok_upload_batch.ps1` đã sửa (commit `3921421`): nếu `$LockRoot` set (param hoặc env `CODEX_DEVICE_LOCK_DIR`) → pass `--lock-root` vào inventory, máy có lock sẽ bị skip. Chạy với lock:

  `export CODEX_DEVICE_LOCK_DIR='/c/Users/Kibe/.codex/device-locks'` (default dir tồn tại) + `-AssignmentManifest` + `-WorkerId` = `owner_id` của manifest.

- **CẢNH BÁO BẪY LOẠI TRỪ MÁY 38 TOÀN CỤC (User Correction 2026-09-06: "Tự nhiên bỏ qua 38. 38 nãy up cho tik4 chứ lq gì tik 5 6")**:
  Việc chừa Máy 38 trước đây chỉ áp dụng cho một batch riêng lẻ của Tik4 (khi máy đang giữ hiện trường/chờ xử lý). CẤM TUYỆT ĐỐI tự suy diễn thành quy tắc cấm toàn cục trên farm cho mọi slot/ca khác. Khi chạy Tik1..Tik3, Tik5, Tik6 hay các lượt avatar/feed chung, Máy 38 vẫn là thiết bị hợp lệ trong hệ thống và phải được chạy bình thường.

- **PITFALL "chạy với lock xong không thấy lock file" — ĐÓ LÀ BÌNH THƯỜNG**: với core policy

  `user_authorized=False` (no-op lease), chạy batch set `CODEX_DEVICE_LOCK_DIR` KHÔNG tạo lock

  file — lock chỉ tồn tại khi user chủ động tạo. Verify "lock đã nhả sau success": `ls

  ~/.codex/device-locks/` không còn `machine_<N>.lock.json`/`serial_<serial>.lock.json` của

  các máy đã chạy; workflow có state ACQUIRE_LOCKS → success DONE → `_release_leases()`

  (fail/manual → giữ `handoff`). Đừng kết luận "lock hỏng" khi chỉ thấy không có lock sau

  batch success. Muốn batch THẬT SỰ giữ lock → tạo lock trước (user ra lệnh) hoặc gọi acquire

  với `user_authorized=True` tường minh.

