# TikN workbook ↔ taikhoan_dat_v2 mapping + render launcher (2026-08-11)

## Vai trò các file

| File | Vai trò |
|---|---|
| `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` (REG) | **Master**. Sheet "Tài Khoản": 80 máy × 8 dòng (640). Cột: Máy, **Folder Video** (đổi tên từ `Tik` 2026-08-11), ID, PASS, 2FA, GMAIL, PASS MAIL, NGÀY SINH, NGÀY TẠO, device ID. |
| `D:\OneDrive\Tiktok\Tik1.xlsx` | Slot 1 mỗi máy (đã đăng video → là anchor chuẩn). |
| `D:\OneDrive\Tiktok\Tik2.xlsx` | Slot 2 (đã render). |
| `D:\OneDrive\Tiktok\tik3.xlsx` | Slot 3 (render 2026-08-11). |

Lưu ý tên file REG có dấu cách trước `.xlsx` — dùng đúng path, không tự "sửa" thành không space.

## Quy luật cốt lõi

- **Folder Video slot k của máy m = (m-1)*8 + k** (k=1..8). Tik1=+1, Tik2=+2, tik3=+3.
  - Máy 1: 1,2,3,4,5,6,7,8 · Máy 2: 9..16 · Máy 10: 73..80 · Máy 74: 585..592 · Máy 80: 633..640.
- **video gốc (source D:\video goc) slot N máy m = (N-1)*80 + m**: Tik1=m (1..80), Tik2=80+m (81..160), tik3=160+m (161..240). D:\video goc có 480 folder.
- **8 slot/máy là thiết kế gốc** (backup 07/07 mỗi máy 8 dòng). Cleanup 14/07 xóa 2 dòng/máy → còn 6; chèn lại 2 dòng trống (folder +7,+8, device ID copy từ máy, các cột khác trống) 2026-08-11.

## Hướng sync & anchor

1. **Sync MỘT CHIỀU**: REG (master) → Tik1/Tik2/tik3. File Tik KHÔNG đẩy ngược.
2. **Anchor = Tik1**: Tik1 đã đăng video thật → folder/ID của nó là chuẩn. REG folder có thể lệch do sửa dòng lịch sử (vd máy 10: backup 07/07 `73,74,75` → 20/07 `73,75,76` → hiện `73,75,76`). Khi REG lệch Tik1 → sửa REG + Tik2/tik3 theo Tik1.
3. **ID theo vị trí dòng slot**: dòng thứ k của máy trong REG = slot k (kể cả dòng trống → file Tik để trống). KHÔNG sync theo "ID không rỗng" (đẩy ID dòng 5 lên slot 3 — sai, đã xảy ra máy 22/34/39/40/53/61 tik3).

## Pitfall đã dính (đừng lặp)

- **"Tik1/2/3 = dòng 1/2/3 theo thứ tự xuất hiện trong REG" là HIỂU NHẦM** — nó làm hỏng folder 3 file Tik (đổi `(m-1)*8+k` thành giá trị REG lệch; Tik1 máy 2: 9→12 sai). Đúng: folder theo quy luật, ID theo vị trí dòng slot.
- **Cột `Tik` trong REG không phải STT toàn cục cũng không phải số thứ tự account** — nó là mã folder video (đã đổi tên thành `Folder Video`).
- **Tik3 lúc đầu là copy Tik2** (folder 2,10,18... và ID trùng Tik2) — phải rebuild theo slot 3: folder +3, ID = dòng 3 của máy.
- **ID rác trong file con** (`http://vo.my/` máy 76) không tồn tại trong master — xóa theo master (master trống → file con trống), không xóa lệch riêng Tik2.
- **Cột "Kiểm Tra Dữ Liệu" (I) là giá trị text cũ, không phải formula** — sau khi sync ID phải cập nhật tay theo `OK`/`MISSING_ID` (đã dính máy 16 báo MISSING_ID dù ID có).
- **openpyxl đọc backup không đuôi .xlsx** (`Tik2.xlsx.bak-sync-id-*`) → `InvalidFileException`. Copy sang temp đuôi `.xlsx` trước khi load. Backup chuẩn nên ghi đuôi `.xlsx` ngay.

## Verify chuẩn sau mọi thao tác workbook

Đọc lại bằng `read_only=True, data_only=True`, với mỗi dòng (máy m, slot k):
- `folder == (m-1)*8 + k`
- `id == REG dòng thứ k của máy m` (theo thứ tự xuất hiện, kể cả rỗng)
- Nếu slot ≤ 2 (đã render): folder phải tồn tại trong D với ≥44 mp4.

## Render launcher TikN (random pipeline)

Template: `run_tik2_random_render.ps1` (repo D:\Taadaa\Tiktok-video, commit 27c5cda). Bản tik3: `run_tik3_random_render.ps1` (tạo 2026-08-11).

- Đọc mapping từ workbook: `machine, output=Folder Video, source=video gốc`.
- Gọi `scripts\random_batch_render.py --input-dir D:\video goc\<src> --file-list <batchDir>\source-<src>.txt --output-dir D:\TIKTOK-videonuoinick\<folder> --preset presets\preset_owner.json --run-id tikN-kibe-m<M>-src<S>-out<O> --randomize --slot <N-1> --machine-id <M-1> --seed-offset 0 --parallel 2`.
  - `--slot` là 0-based: Tik1=0, Tik2=1, tik3=2.
  - `select_videos` (scripts/tik3_multi_batch.py): min 42, max 45 video ngắn nhất sau probe.
- Chạy: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File run_tikN_random_render.ps1 -StartMachine 1 -EndMachine 80 -PlanOnly` (plan) → `-AutoRun` (chạy ngầm, bỏ qua Read-Host confirm). **Luôn chạy qua `terminal(background=true, notify_on_complete=true)`**, không foreground (600s cap).
- Kết quả: run dir `D:\CodexRuntime\tiktok-video\runs\tikN-kibe-m*-src*-out*` chứa `render_manifest.csv` (source,output,status=rendered,duration,log_path) + `run_meta.json` (args: randomize=true, slot, machine_id, preset_name).
- Quy luật source = `(N-1)*80+m` quan trọng: tik3 cột `video gốc` ban đầu copy Tik2 (81..160) — phải sửa thành 160+m trước khi render, nếu không render nhầm source.

## Kiểm tra tiến độ đăng video máy (vd máy 74)

- Cột `Video Đã Đăng` trong Tik1.xlsx = số video đã đăng (máy 74 = 6).
- Run reports: `D:\CodexRuntime\tiktok-video\runs\run_<serial>_<ts>\report.json` — `status` + `reason`; chuỗi fail cùng signature (`VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`, `VIDEO_PICK_HOME_NOT_REACHED`) = kẹt VIDEO_PICK, không phải máy hết video.
