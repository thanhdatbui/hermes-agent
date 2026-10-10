---
name: spreadsheet-mapping-audit
description: Audit and safely synchronize IDs, keys, folder mappings, and row-level relationships across Excel workbooks and filesystem-backed media manifests.
version: 1.0.0
category: productivity
metadata:
  hermes:
    tags: [xlsx, mapping, reconciliation, filesystem, audit]
---

# Spreadsheet Mapping Audit

Use this class-level skill whenever multiple Excel files represent the same accounts/assets, especially when one workbook maps records to folders or files on disk.

## Core rule

Never infer a key's meaning from its label, apparent sequence, or row position. A column named `Tik`, `STT`, or `ID` may be a global asset/folder key rather than a per-machine ordinal. Determine the contract from headers, workflow code/docs, representative rows, and the target filesystem before editing.

## Authority and synchronization direction

- Declare one authoritative master before editing. For this workbook class, the registration workbook (`taikhoan_dat_v2`) is the master; `Tik1.xlsx`, `Tik2.xlsx`, and `tik3.xlsx` are derived slot views.
- Synchronization is **one-way: master → derived**. A correction or deletion in a derived workbook must not be written back to the master automatically. If a value exists only in a derived file, report it as orphan/stale derived data and clear it by rebuilding from the master only after the user requests the repair.
- When the user defines Tik1/Tik2/Tik3 as account slots, select source rows by **machine-local row position** (slot k = the k-th REG row of that machine, including empty rows → empty slot), then copy both `ID` and the folder value into the derived row. Do not skip empty-ID rows when counting slots — row position is the contract, and skipping shifts later slots (observed: Tik3 rows got IDs from slot 4+ of REG).
- **REG's folder column is not automatically authoritative.** Historical manual edits can corrupt it (machine 2 read `12,10,11,13,14,15` instead of `9,10,11,12,13,14`). When a proven workbook exists (one whose videos were actually posted), anchor the folder allocation on it and normalize REG to the derived rule, with user confirmation.
- For this class, the folder allocation rule is `Folder Video(machine m, slot k) = (m-1)*8 + k` (Tik1 k=1 → 1,9,17...; Tik2 k=2 → 2,10,18...; Tik3 k=3 → 3,11,19...). Verify the rule against the posted workbook and D-folder existence before mass-rewriting.

## Hashtag/keyword: theo niche của folder NGUỒN, không theo máy

`Keyword Video` + `Hashtag Pool` của một dòng TikN phải khớp niche của **folder nguồn**
mà dòng đó render (`D:\video goc\<video gốc>`), không phải niche của máy — user sửa
thẳng: "Bậy. Sao lại lấy theo máy. Lấy theo keyword tải folder nguồn chứ?". Nguồn niche:
DB downloader `state-real-1-tiktok-final.db` (bảng `folders`: folder_num → niche slug),
`data/niches_pool.txt` (slug → label), và pool hashtag đã có trong Tik1 sheet
"Hashtag theo Folder" (niche có sẵn → copy nguyên; niche mới → build
`#<slug> [+extras] #<slug>vietnam #<slug>moingay + #tiktokvietnam #xuhuong #fyp #videohay`).
Cùng máy, ba slot khác niche (máy 74: Tik1 `thucung`, Tik2 `cafe`, Tik3 `game`).
Quy luật `video gốc` (cột source): Tik1 = m, Tik2 = 80+m, Tik3 = 160+m — tik3 mới tạo
hay copy 81..160 của Tik2, phải sửa. Chi tiết kèm launcher render + watchdog:
`references/tikn-hashtag-source-and-render.md`.

## Completeness gate for source-folder niche audits

Before any niche/hashtag resync, distinguish **coverage** from **correctness**:

- `state.db` is an operational source, not proof that every folder is correctly classified. A row can exist in `folders` while having a stale niche, no `source_channel`, or no matching `videos`/uploader evidence.
- Report audit coverage explicitly: expected folder range, folders present, folders with source/uploader/video evidence, and folders missing evidence. Never call a partial metadata scan “all folders fixed.”
- A folder with missing `source_channel` or no video/uploader evidence is `REVIEW`, not an automatic sync candidate. Recover evidence from the historical downloader DB, manifests/source metadata, and the actual source-folder provenance before writing a niche or hashtag.
- The sync script is a copier, not a classifier: it will faithfully propagate a wrong DB niche into `TaiKhoan` and `Hashtag theo Folder`. Validate the DB row before running it.
- For mixed-content folders, use source-channel identity plus majority/quality evidence; do not treat an old workbook row or a single stale DB label as authoritative.
- After editing, verify both layers independently: the DB `(folder_num, niche, source_channel)` and the exact derived workbook row keyed by `video gốc`, including both `TaiKhoan` and `Hashtag theo Folder`.

See `references/folder-niche-audit-completeness.md` for the reusable checklist and evidence table.

## Regression prevention for partial folder metadata

A successful workbook sync is not evidence that the classification was correct. The sync layer copies whatever niche is present in `state.db`; it must never be treated as the classifier. Before calling a 1..640 audit complete, report all four counts separately: expected folder range, folders present in the operational DB, folders with current source/uploader evidence, and folders requiring historical recovery or review. A folder with a missing `source_channel` or no matching `videos` rows is a coverage gap, not a verified match.

When a channel that was previously correct regresses after a bulk resync, inspect timestamped workbook and DB backups before assigning blame. Compare the exact `(account, video gốc, Keyword Video, Hashtag Pool)` row and the DB `(folder_num, niche, source_channel)` row across snapshots. If historical downloader data shows mixed niches, use the dominant source/uploader evidence and disclose the mixed-content caveat. Never claim “all folders fixed” from a partial metadata scan.

For the reusable checklist and evidence table, see `references/folder-niche-audit-completeness.md`.

## Historical render/artifact provenance

- Before claiming that rendered media is missing or “leaked” to another folder, compare the derived workbook mapping **at render time** with its current mapping. Inspect run metadata/manifest arguments (`input_dir`, `output_dir`, source/output folder, preset, randomization) and the historical workbook backup if available.
- A post-render master resync can legitimately move a row's `Folder Video` while old MP4s remain in the previous output folder. Classify this as `mapping_changed_after_render`, not as a renderer mapping failure. Never silently delete or rerender those artifacts; report the old→current mapping and counts first.

## Video folder numbering standardization & render count reconciliation (TikN / D:\TIKTOK-videonuoinick)

Khi chuẩn hóa số thứ tự video MP4 trong các folder `D:\TIKTOK-videonuoinick\<Folder Video>` và cập nhật workbook `TikN.xlsx`:
1. **Bảo vệ tuyệt đối file đã đăng**:
   - Đọc cột `Video Đã Đăng` (`posted`).
   - Các file từ `1.mp4` đến `posted.mp4` ĐÃ ĐĂNG LÊN TIKTOK: **TUYỆT ĐỐI KHÔNG ĐỔI TÊN HAY DI CHUYỂN**.
2. **Quy trình đổi tên 2 pha (Two-phase rename) chống xung đột/ghi đè chéo**:
   - Với các file MP4 chưa đăng (`> posted`), sắp xếp theo thứ tự số tăng dần.
   - Mục tiêu đánh số liên tục: `posted + 1`, `posted + 2`, ..., `N`.
   - **Pha 1**: Đổi tên các file cần đổi sang tên tạm `.tmp_ren_{folder}_{target}.mp4`.
   - **Pha 2**: Đổi tên từ file tạm sang `{target}.mp4`.
   - Cơ chế 2 pha này đảm bảo không bao giờ bị ghi đè chéo (collision/clobber) khi folder có gap hoặc dải số dịch lùi/tiến.
3. **Cập nhật workbook TikN.xlsx chuẩn Atomic**:
   - Tạo backup `.bak` trước khi ghi.
   - Cập nhật cột `Render Status = 'OK'` và `Render MP4 = <số lượng MP4 thực tế N>`.
   - Lưu ra file tạm cùng thư mục (`.xlsx.tmp`) rồi dùng `os.replace` để tránh corrupt file khi có tiến trình khác đang đọc hoặc ngắt giữa chừng.
   - Chạy script kiểm tra độc lập lại toàn bộ 80 folder (khẳng định liên tục `1..N`) và 80 dòng workbook trước khi chốt.

## Safe workflow

1. **Inventory before edit**
   - Resolve the exact files, including filenames with trailing spaces, suffixes, and backups.
   - Read sheet names, headers, row counts, cell types, and representative rows.
   - Identify the authoritative source and every derived workbook.

2. **Recover the actual join key and slot contract**
   - Build candidate joins explicitly, e.g. `(machine, global_key)`, `(machine, account_id)`, or `(device_id, account_id)`.
   - Do not infer slot semantics from filenames alone. However, when the user/source contract explicitly defines `Tik1`/`Tik2`/`Tik3` as account 1/2/3 within each machine, use the row position within that machine for slot mapping.
   - Keep two concepts separate: slot order selects the source row; the source row's `Tik` value may still be the folder key copied into the derived workbook's `Folder Video` field.
   - Search workflow code/docs for path construction such as `root/{key}/{filename}`.
   - **Find the folder allocation rule, don't copy raw folder cells.** If a workbook was actually used to post/render (e.g. Tik1 had real uploads), its folder column is the ground truth; derive the formula (here `(m-1)*8+k`) from it, then apply the formula to REG and all derived files. Raw REG folder values may be corrupted by prior manual row edits.

3. **Probe the filesystem contract**
   - If a workbook key is used in a path, verify the exact folder/file exists.
   - Report missing source folders separately from bad workbook links; absence on disk is not proof that a different key should be used.
   - Treat sparse/non-contiguous numeric folders as meaningful evidence that the key is global, not a simple row ordinal.

4. **Audit, do not mutate first**
   - Produce counts for: exact matches, ID not found, machine mismatch, key/folder missing, and conflicting IDs.
   - Show a small representative sample of each failure class.
   - Stop before editing when the candidate mapping is ambiguous or when many source keys have no corresponding filesystem asset.

5. **Safe edit and rollback**
   - Create a timestamped backup beside each workbook before any write.
   - Write only the intended cells; preserve sheets, formatting, formulas, and workbook conventions.
   - Reopen the saved files and re-run the exact mapping audit. Require zero unexpected mismatches before claiming synchronization.
   - If an edit was based on a wrong interpretation, restore the timestamped backup before attempting the corrected mapping; never layer a second speculative repair on top.

## Common pitfalls

- **Off-Grid Folder Video Drift & Slot Collisions on Cluster Admin (Máy 201–280)**:
  * Công thức Folder Video chuẩn cho cụm Admin: $\text{Folder Base} = (STT - 201) \times 8 + 1 \dots (STT - 201) \times 8 + 8$ (dải 1..640).
  * Khi tool reg ghi nhận Folder vượt ra ngoài dải (ví dụ $\text{base} + 8 + \text{slot}$ do gán nhầm hoặc cộng dồn, M264 có base 505..512 nhưng gán 513, 514), công thức tính slot trong `sync-safe-workbook.py` (`(folder - 1) % 8`) sẽ quay vòng và va chạm với Slot 1 hoặc Slot 2 đã có sẵn nick.
  * Hậu quả: Script đồng bộ loại bỏ nick mới vì trùng slot, để lại slot trống (`None`) trên `taikhoan_run_safe.xlsx`. Tool preflight reg bù (`ensure_row_accounts.py`) quét thấy `None` lại tưởng máy thiếu nick và tiếp tục điều máy đi reg bù, gây lỗi `MACHINE_FULL_8_ACCOUNTS` hoặc `[07] Tim email chua dang ky`.
  * Khắc phục: Quét tìm các dòng có $\text{Folder} < \text{base}$ hoặc $\text{Folder} > \text{base} + 7$ trong `admin/taikhoan_dat_v2_updated .xlsx`, chuẩn hóa về đúng dải $1 \dots 640$, rồi rebuild lại `taikhoan_run_safe.xlsx` bằng `TAADAA_HOST_CONFIG=".../admin.yaml"`.
- A global `Tik`/asset number is not the ordinal of the account within a machine.
- **`farm_account_info` SQLite vs Excel `Folder Video` confusion**: Trong database `D:/Taadaa/data/tiktok_tracker.db` (`farm_account_info`), cột `tik` biểu thị số thứ tự slot/ca nuôi (1..8) của máy (tương ứng Tik1..Tik8), TUYỆT ĐỐI KHÔNG lưu số `Folder Video` (ví dụ 1960). Việc nhầm lẫn điền Folder Video vào `tik` sẽ làm sai lệch phân bổ slot và các truy vấn tracking.
- **Dashboard Machine Badge Missing (`f.may IS NULL`) & `farm_account_info` Sync Gap**:
  - *Hiện tượng*: Trên Web Dashboard `TikTok Farm Dashboard` (`kibe:1905`), tài khoản LIVE hiển thị đầy đủ stats (tim, follow, ranking) nhưng không hiện nhãn số máy (`Mxx` như M39, M247) và bị đẩy ra khỏi filter Cụm Kibe / Admin (`cluster = 'other'`).
  - *Nguyên nhân cốt lõi*: `tiktok_dashboard.py` join dữ liệu qua `LEFT JOIN farm_account_info f ON r1.username = f.username`. Bảng `snapshots` nhận dữ liệu crawl realtime theo username từ TikTok, trong khi `farm_account_info` lưu mapping kho tài sản `(username, may, host_id, tik)`. Khi nick mới được tạo hoặc mới add vào Excel nuôi nhưng chưa được đồng bộ/backfill vào `farm_account_info`, trường `f.may` bị `NULL` -> hàm `mayTagHtml()` trên frontend trả về chuỗi rỗng.
  - *Quy trình đối soát O(1)*:
    1. Kiểm tra SQLite: `SELECT * FROM snapshots WHERE username = ? ORDER BY id DESC LIMIT 1;` và `SELECT * FROM farm_account_info WHERE username = ?;`.
    2. Đối soát tìm máy thực tế trong các file Excel phân bổ (`D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`, `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`) để xác định cặp `(may, tik, host_id)`.
    3. Cập nhật bổ sung mapping: `INSERT OR REPLACE INTO farm_account_info(username, may, host_id, tik) VALUES (?, ?, ?, ?)`. Sau khi ghi DB, Dashboard tại port 1905 sẽ tự động nhận diện đúng nhãn máy `Mxx` và cụm tương ứng trong chu kỳ refresh kế tiếp.
- **Master Excel (`taikhoan_dat_v2_updated .xlsx`) là Source of Truth tối cao cho `farm_account_info` SQLite**:
  - *Lỗi lệch ca/slot (Desync)*: Tuyệt đối CẤM map `tik` (ca nuôi 1..8) theo thứ tự crawl lịch sử hay thời điểm nick được tạo. Bảng `farm_account_info` BẮT BUỘC map 1:1 từ Master Excel (`taikhoan_dat_v2_updated .xlsx` của Kibe và Admin) theo công thức toán học:
    $$\text{Tik (Slot)} = ((\text{Folder Video} - 1) \pmod 8) + 1$$
    $$\text{Máy} = \text{Cột Máy trong file Master}$$
  - *Công cụ chuẩn hóa*: Đã tạo script chuẩn tại `D:/Taadaa/tools/sync_farm_account_info.py`. Mỗi khi cập nhật Master Excel, chạy lệnh `python D:/Taadaa/tools/sync_farm_account_info.py` để tự động tạo backup DB và đồng bộ nguyên tử toàn bộ dải máy Kibe (1–80) và Admin (201–280), đảm bảo 0 lệch ca và 0 thiếu máy trên Dashboard.
- A derived Tik1/Tik2/Tik3 workbook may already use a historical folder allocation that differs from the current registration workbook; do not silently overwrite it.
- Empty IDs and URL-like placeholders are not valid account IDs and must be reported distinctly.
- A folder existing on disk does not prove it is the folder assigned to that account; verify the authoritative `(machine, key)` mapping.
- If Tik3 is a copy of Tik2, that is a data-integrity finding to report—not a reason to blindly shift rows.
- Always state whether the user asked for an audit only or an actual synchronization. “Check mapping” means read-only unless the user explicitly requests repair.
- **openpyxl cannot open backup files whose name lacks the `.xlsx` extension** (e.g. `Tik2.xlsx.bak-sync-id-20260811_145651`) — it raises `InvalidFileException`. Copy the backup to a temp path ending in `.xlsx` before loading, and keep the original backup untouched.
- **Excel Serial Date Parsing vs ISO Dates (`ngày tạo` / date columns)**: Date values in workbook columns may be raw Excel serial numbers (e.g. `46236` = 2026-08-02, day offset from `1899-12-30`), string representations (`'2026-08-18'`, `'18/08/2026'`), or native Python `datetime.datetime` objects. Any inventory audit or recency filter must safely normalize all three representations (`datetime(1899, 12, 30) + timedelta(days=float(val))` for numeric values > 30000) to avoid silently dropping newly created records.
- **Excel Column Shift & Fallback Probe Pattern (Date/Metadata Columns)**: In multi-machine workbooks (e.g. `taikhoan_dat_v2`), manual copy-pasting or batch append scripts often cause data to drift into adjacent columns (e.g. date entered into column 9 `device ID` instead of column 8 `NGÀY TẠO`, leaving column 8 `None`). Never rely exclusively on header-detected column index when parsed value is empty or invalid. Always define an ordered fallback probe list (e.g. `[header_col] + [8, 9, 7]` deduplicated) and validate candidate values against domain constraints (`candidate and candidate.year >= 2025`) before declaring a row unparseable/unverifiable.
- **Recovering transient/quarantined account records from backup workbooks & audit sheets**: When auditing recent account registrations across the farm, accounts that died or triggered CAPTCHA shortly after creation may have been deleted or quarantined from the active workbook sheet into `Audit Pending` (e.g. `MAIL_DIE_GOOGLE_RELOGIN_REQUIRED`) or preserved only in timestamped backup workbooks (`gmail_clean_v2_backup_*.xlsx`). Always include backup snapshots and audit sheets to get a 100% accurate count of newly created inventory before comparing with checklive master results.
- **Excel Tab/Sheet Name Length Limit**: Tên sheet/tab trong Excel BẮT BUỘC <= 31 ký tự. Nếu vượt quá (vd `2. Tuitehao Ban Nhieu (Khac Nguon)` = 34 chars), Excel sẽ ném cảnh báo/popup *"We found a problem with some content in '...xlsx'. Do you want us to try to recover..."*. Luôn kiểm tra và rút ngắn tên sheet dưới 30 ký tự khi tạo workbook bằng openpyxl.
- **Tên cột và cấu trúc so sánh trực diện (3 bên)**:
  - Khi so sánh 3 bên (Shop A vs Shop B vs Kho nguồn), tên cột phải cụ thể (`Stock Shop A`, `Stock Shop B`, `Stock Kho Nguồn`), tránh dùng từ chung chung gây hiểu nhầm.
  - Xếp các cột cùng chiều dữ liệu liền kề nhau: Tên liền kề → Giá liền kề (đồng nhất VNĐ + USD) → Stock liền kề.
  - Dữ liệu thuần túy: Không chèn cột nhận xét/phân tích dài dòng kiểu AI; các nhãn trạng thái chỉ ghi ngắn gọn (`Bị lệch`, `Khớp`, `—`).
- **Status/check columns are stale text, not formulas** in this workbook class. After syncing IDs, recompute status cells (`OK` when ID is non-empty and not a URL-like placeholder, otherwise `MISSING_ID`); a visible stale `MISSING_ID` after a correct ID sync is a data-write omission, not an ID problem.
- **Rely on a posted/render-proven workbook over a raw master folder column.** The master REG folder values can be corrupted by prior row edits while Tik1 (actually posted) still encodes the true rule. When the user says "map theo Tik1" / "theo file đã đăng", that workbook is the anchor — apply its formula to REG, not the reverse.
- **Data type drift and alignment jitter (`số máy` / machine column)**: Khi nhập liệu thủ công hoặc append script, số máy dễ bị lưu lẫn lộn giữa kiểu chuỗi (`'1'`, `'75'` -> mặc định lệch trái) và kiểu số (`1`, `75` -> lệch phải). Quy chuẩn bắt buộc khi chuẩn hóa file nguồn tài khoản (`gmail_clean_v2.xlsx`, `taikhoan_dat_v2`):
  - Ép kiểu 100% cột máy về số nguyên `int`, định dạng căn giữa (`Alignment(horizontal='center', vertical='center')`).
  - Sắp xếp tăng dần theo số máy để các tài khoản cùng một máy nằm liền kề nhau; cấm append dồn tài khoản xuống đáy bảng.
  - Xóa bỏ các dòng placeholder rác (không có email và không có pass).
  - Cột ngày tháng/mã căn giữa (`center`), cột email/pass căn trái (`left`) đồng nhất font Calibri 11pt.
- **Khôi Phục Mật Khẩu TikTok & Phân Biệt Cột PASS vs PASS MAIL (`taikhoan_dat_v2`)**:
  - Cột 4 (`PASS`) là mật khẩu TikTok (bắt buộc theo chuẩn bảo mật TikTok: có chữ hoa, chữ thường, số, ký tự đặc biệt như `d50Xi*Uzk7`).
  - Cột 7 (`PASS MAIL`) là mật khẩu tài khoản email/Hotmail (thường là chuỗi chữ thường + số như `qaxvon909063`).
  - TUYỆT ĐỐI CẤM lấy giá trị cột `PASS MAIL` điền đè vào cột `PASS` TikTok khi thực hiện sync/restore dữ liệu bị thiếu.
  - Khi cần khôi phục mật khẩu TikTok bị mất do ghi đè/lỗi sync, quét thư mục `C:\Users\Kibe\AppData\Local\Taadaa\Tiktok_Reg\workbook-backups\` để lấy lại mật khẩu gốc từ các bản snapshot `taikhoan_dat_v2_updated_before_account_success_*.xlsx` tạo ngay lúc reg thực tế.
- **Kỷ Luật Độc Lập Credential Giữa Các Dịch Vụ (CẤM ĐÈ PASS CHATGPT/TIKTOK BẰNG PASS MAIL)**:
  - Cột 7 (`PASS MAIL`), Cột 4 (`PASS` TikTok), và Cột 12 (`PASS CHATGPT`) là các thông tin xác thực hoàn toàn độc lập của 3 dịch vụ khác nhau.
  - TUYỆT ĐỐI CẤM tự tiện suy diễn rằng pass các cột giống nhau rồi tiện tay đồng bộ hay ghi đè `PASS CHATGPT` khi tìm lại được hoặc đổi `PASS MAIL`.
  - Bất kỳ thao tác cập nhật mật khẩu nào chỉ được phép tác động ĐÚNG DUY NHẤT cột mục tiêu (ví dụ đổi pass mail chỉ ghi cột 7 `PASS MAIL`). Tuyệt đối không bao giờ chạm vào Cột 12 `PASS CHATGPT` hay Cột 4 `PASS` TikTok trừ khi có lệnh đích danh từ User.
- **Duplicate ID Audit & Cleanup Policy (`taikhoan_dat_v2`)**:
  - Khi quét duplicate ID TikTok trên file master: phân loại các hàng trùng thành (1) hàng rác/trống info (`PassTT=None` và `2FA=None`) vs (2) hàng có info riêng (có Pass riêng, 2FA riêng, hoặc Mail riêng).
  - Chỉ xóa trắng ô `ID` ở các dòng trống info để giải phóng slot rảnh cho batch reg mới; TUYỆT ĐỐI KHÔNG tự ý xóa dòng có Pass/2FA mà phải liệt kê bảng đối soát (Row, Máy, PassTT, 2FA, Gmail, PassMail) báo cáo user kiểm tra.
  - Sau khi sửa master, bắt buộc trigger sync sang `taikhoan_run_safe.xlsx` (`hermes_taikhoan_sync_cron.py` hoặc `sync-safe-workbook.py`) để tránh picker nuôi acc đọc ID rác.
- **Auditing Cross-Workbook UID Invariants vs Preflight Gate (`excel_preflight_validator.py`)**:
  - *Hiện tượng*: Cron sync `taikhoan-run-safe-sync` bị lỗi `[PREFLIGHT_VALIDATOR_FAIL]` do phát hiện trùng lặp tài khoản xuyên file (Rule 2: No Duplicate Accounts Cross-Files, ví dụ nick `laquyen2601` xuất hiện tại cả `tik3.xlsx` slot 3 M10 và `Tik2.xlsx` slot 2 M10).
  - *Nguyên nhân cốt lõi*: Trong quá trình reg bù hoặc dọn dẹp duplicate, nếu chỉ reset các slot bị trùng trong file Master (`taikhoan_dat_v2_updated .xlsx`) mà chưa kiểm tra file con (`Tik1.xlsx..Tik8.xlsx`), validator của cron sẽ chặn đứng toàn bộ tiến trình publish sang runtime để bảo vệ farm.
  - *Quy chuẩn đối soát định lượng trước khi Closeout*:
    1. Kiểm tra 100% Unique UIDs trên `taikhoan_run_safe_combined.xlsx` bằng `collections.Counter`: `len(counts) == len(uids)` (Duplicates = 0).
    2. Chạy độc lập `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir D:/OneDrive/TaadaaData/kibe --exit-on-error` để phát hiện sớm các case trùng lặp xuyên file `TikN` trước khi sync cron tự động phát hiện và ném alert.
- **Target Inventory Conflict & Extra Machines Normalization (`taikhoan_run_safe.xlsx`)**:
  - Khi `_detect_clean.py` hoặc `target_inventory.py` báo `TARGET_INVENTORY_CONFLICT: machine X` hoặc `TARGET_INVENTORY_SERIAL_CONFLICT`:
    - Nguyên nhân: `taikhoan_run_safe.xlsx` có các slot cùng một máy nhưng mang serial khác nhau, hoặc serial bị gán trùng giữa các máy (thường do `EXTRA_MACHINES` trong `sync-safe-workbook.py` bị lệch/swapped ở dải máy 75-80).
    - Quy trình xử lý chuẩn:
      1. Đối chiếu serial chuẩn từ `Tik1.xlsx` và ADB thực tế (`adb devices` / `adb -s <serial> get-state`).
      2. Đồng bộ mapping chuẩn trong `D:\Taadaa\tiktok-luot nuoi acc\scripts\sync-safe-workbook.py` (`EXTRA_MACHINES` 75..80: 75=`ce011711d4cd802905`, 76=`9885b64d56305a3731`, 77=`ce05160595e7953b04`, 78=`ce0916090a9d320a01`, 79=`ce0516059d279f3e03`, 80=`ce061606cd45950405`).
      3. Chạy `python sync-safe-workbook.py` để tái tạo đủ 480 dòng `taikhoan_run_safe.xlsx`.
      4. Chạy `python _detect_clean.py` trong `Tiktok_Reg` xác nhận giải quyết triệt để lỗi inventory conflict.

## Slot-aware synchronization contract

There are two separate operations:

1. **Select the slot:** within each machine, filter to rows with a non-empty account `ID` and preserve source order. The first/second/third such rows feed `Tik1`/`Tik2`/`tik3` respectively when the user has defined those files as account slots.
2. **Copy the fields:** copy the selected REG row's `ID` and its `Tik` value into the target's `ID` and `Folder Video` columns. In REG, `Tik` is the folder identifier; it is not the slot number. If desired, rename the REG header to `Folder Video` while preserving values.

For each target row, verify `(machine, slot) -> (ID, Folder Video)` against REG. Do not compare a target row number with REG's `Tik` value, and do not populate Tik3 from Tik2.

## Correct read-only audit

For each row in a derived workbook:

1. Determine the target slot from the user's contract and machine-local source order.
2. Resolve the authoritative REG row by `(machine, slot)`.
3. Compare both target `ID` and target `Folder Video` to the REG row's `ID` and `Tik`/`Folder Video`.
4. Separately check `D:\\TIKTOK-videonuoinick\\<Folder Video>` exists when filesystem validation is requested.
5. Classify failures separately: exact mapping; missing source slot; ID mismatch; folder mismatch; folder absent; empty or URL-like placeholder ID.
6. Recompute stale derived status columns. A visible `MISSING_ID` can remain after an ID is repaired; conversely, an invalid/placeholder value must not be treated as a valid ID merely because it is non-empty.

## Incident lesson

A prior audit initially treated `Tik1`/`Tik2`/`Tik3` as a global `(machine, Tik)` join and later treated them as rows without synchronizing `Folder Video`. The resolved contract is slot-by-source-row for selecting accounts, followed by copying both `ID` and the source `Tik` folder value. The safe recovery pattern is timestamped backups, a same-directory `.xlsx` temporary file, full row-level verification, and only then atomic replacement.

## 5 Invariant Rules & Preflight Validator Gate (`excel_preflight_validator.py`)

Khi kiểm tra hoặc đồng bộ hệ thống workbook phân bổ farm (`Tik1.xlsx..Tik8.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`), BẮT BUỘC tuân thủ và kiểm tra 5 Invariant Rules sau (đã đóng gói thành gate tại `D:/Taadaa/tools/excel_preflight_validator.py`):
1. **Rule 1 (Slot Limit Per Machine)**: Mỗi máy có tối đa 8 dòng/slot. Không xuất hiện trùng lặp máy trong cùng 1 file Tik.
2. **Rule 2 (No Duplicate Accounts Cross-Files)**: Tài khoản không bị trùng lặp trên 2 slot khác nhau trong cùng 1 file hoặc xuyên suốt các file `Tik1..Tik8.xlsx` (trừ `None`/trống).
3. **Rule 3 (Folder Video Formula & Uniqueness)**: Cột `Folder Video` (cột 4) phải độc bản trên toàn farm và khớp tuyệt đối công thức: `Folder Video(m, slot) = (m - 1) * 8 + slot`. Tuyệt đối không để chuỗi ký tự lạ, mật khẩu hay số lệch vào cột này.
4. **Rule 4 (Video Gốc Formula & Uniqueness)**: Cột `Video Gốc` (cột 5) phải độc bản trong cùng 1 file `Tik{slot}.xlsx` (không 2 máy nào trong cùng 1 ca dùng chung video gốc), và khớp công thức: `Video Gốc(m, slot) = (slot - 1) * 80 + m`.
5. **Rule 5 (taikhoan_run_safe.xlsx Invariants)**: Mỗi máy tối đa 8 dòng, 100% có serial phần cứng không rỗng, tài khoản không trùng lặp giữa các máy khác nhau.

### Tích hợp Preflight Gate vào Sync Cron:
Tại `hermes_taikhoan_sync_cron.py`, trước khi đồng bộ sang runtime (`hermes_cron_source_config.json`), bắt buộc chạy `excel_preflight_validator.py --excel-dir <path> --exit-on-error`. Nếu validator trả về lỗi (exit code != 0), HỦY NGAY luồng đồng bộ sang runtime để bảo vệ Farm khỏi dữ liệu rác.

## Multi-workbook transaction and lock-order invariant

When synchronizing more than one derived workbook as a group transaction:

1. Preflight every workbook and acquire the complete, deterministic outer lease set before any publish.
2. Run recovery before acquiring those outer leases, because the generic atomic-update helper acquires its own workbook lock.
3. Once outer leases are held, do not call a lock-acquiring atomic helper for publish or rollback. Use a narrowly scoped lock-free-under-caller-lease atomic routine that still preserves temp-file replacement, rollback copy, verification, and cleanup guarantees. Keep the generic helper only for recovery outside the group lease.
4. Persist all snapshots and the journal, with fsync, before the first publish. On any publish failure, rollback under the existing leases without reacquiring them.
5. Recovery must preflight every journal-referenced snapshot. A missing snapshot is an explicit fail-closed error; never skip it and delete the journal. Retain both journal and snapshots on missing-evidence or transaction-failure paths so a later operator/restart can recover.
6. Regression fixtures should use a fake lease set that raises on nested acquisition, and exercise no-update, publish, injected publish failure/rollback, and missing-snapshot recovery. Assert lock calls externally and assert journal/snapshot retention outside swallowed exception paths.

Keep this transaction logic in the consumer synchronizer; do not widen scope into shared workbook-core code unless the task explicitly authorizes it.

## Verification checklist

- Exact source/derived paths recorded.
- Authoritative key semantics proven from at least two independent signals (source rows plus workflow/path code or filesystem pattern).
- Timestamped backups exist for every edited workbook.
- Post-write audit counts and representative failures captured.
- Status/check columns recalculated and verified after data synchronization.
- No secrets, passwords, or raw account credentials included in reports.

## References

For the REG/Tik workbook and `D:\\TIKTOK-videonuoinick\\{Tik}` mapping pattern, see `references/reg-tik-folder-reconciliation.md`.
For off-grid folder video drift and modulo-8 slot collisions on the Admin cluster (machines 201–280), see `references/admin-cluster-offgrid-folder-slot-collision.md`.
For hashtag-by-source-folder niche, `video gốc` allocation rules, 8-row/machine restore, random render launcher, and the silent progress watchdog, see `references/tikn-hashtag-source-and-render.md`.
For fingerprint ledger vs workbook video count drift audit, see `references/fingerprint-vs-workbook-video-count-audit-20260902.md`.
For single-account hashtag drift between `Folder Video` and `video gốc` (e.g. pet videos with automotive hashtags), see `references/hashtag-drift-render-source-reconciliation.md`.
