# m74 VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED — root cause thật (2026-08-10/11)

## Triệu chứng

- Run m74 (serial `ce061606c21e153d03`, máy 74) fail:
  `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Recaptured surface did not prove a labelled bottom-centre create control`
- Visual gate: `white=0.000, dark=0.976, cyan=0.000, red=0.007`
- Ảnh `video-pick-*.png` trong run dir nhìn "giống feed" nhưng thật ra là **video detail** (mũi tên Back, search bar "Tìm nội dung liên...", prompt "Bạn muốn tiếp cận phạm vi đối tượng người xem lớn hơn? Thêm vị trí", nút "Cài đặt quyền riêng tư", KHÔNG có bottom nav, KHÔNG có nút +).

## Phân biệt QUAN TRỌNG: pre/post publish

- **SAU khi đăng xong**, TikTok mở video detail của video VỪA đăng (like/comment/share view) — đây là **hành vi bình thường**, KHÔNG phải lỗi surface. User xác nhận: "acc nào đăng video xong nó cũng sẽ ở mở video vừa đăng của acc đó". Đừng chẩn đoán nhầm đây là stuck.
- **TRƯỚC khi đăng** (m74 case): flow chưa tới POST/VERIFY_POST bao giờ — log dừng ở `MEDIA_PUSH → VIDEO_PICK → error`. Màn hình video detail lúc đó là **video CŨ của account** (ngày 07-30 trong khi run là 08-10), không phải video vừa đăng.

## Root cause thật

Không phải "UI máy 74 khác", không phải cache (PRE_CACHE_CLEANUP bị skip để giữ session — cache stale có thể góp phần nhớ route cũ nhưng không phải nguyên nhân chính).

Log m74:

```
[WAIT_FEED] Root surface confirmed with indicator: 'trang chủ'   ← ban đầu vào Home OK
[TAP_PROFILE] Tap profile tab by text 'Hồ sơ'                    ← flow vào Profile kiểm tra account
[ACCOUNT_READY] Target account verified on Profile
MEDIA_PUSH
[WAIT_FEED] Root surface confirmed with indicator: 'hồ sơ'       ← SAU MEDIA_PUSH chấp nhận Profile làm root
VIDEO_PICK → error
```

Nguyên nhân: `_is_tiktok_root_surface()` + `_wait_for_feed()` chấp nhận indicator `'hồ sơ'` (Profile) như root surface hợp lệ. Sau `MEDIA_PUSH`, flow chỉ `bring_to_foreground` mà **không normalize về Home**, nên TikTok resume đúng route cuối (Profile → video detail) → vào `VIDEO_PICK` từ màn không có nút + → classifier fail-closed ĐÚNG.

## Invariant cần có

```
MEDIA_PUSH
→ bắt buộc semantic navigate/verify về 'Trang chủ' (bottom nav, create control, không tap tọa độ mù, không bỏ foreground gate)
→ VIDEO_PICK
```

Chưa implement — chỉ chẩn đoán + evidence. Nếu sửa: sửa generic flow, KHÔNG thêm workaround riêng cho m74 (lịch sử UI máy khác biệt dễ phá farm).

## Chạy worker: cần `echo YES |`

`tiktok_workflow --config ... --machine N --no-dry-run` hỏi xác nhận interactive `Type 'YES' to continue`. Chạy background mà không pipe stdin → `EOFError: EOF when reading a line` (exit 1). Chạy đúng:

```bash
echo YES | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
  /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe \
  -m tiktok_workflow --config D:/CodexRuntime/tiktok-video/config-machine-62.yaml \
  --machine 74 --no-dry-run --recovery-mode --allow-device-reboot-recovery
```

Config `config-machine-74.yaml` có `machine: "62"` — phải luôn truyền `--machine 74` override (lock file cũ ghi command đúng pattern này).

## Workbook upload: Tik1/Tik2/Tik3 (2026-08-11)

- `D:\OneDrive\Tiktok\Tik1.xlsx` — live, 4 sheets: `TaiKhoan` (9 cột: Máy, device ID, ID, Folder Video, video gốc, Keyword Video, Hashtag Pool, Video Đã Đăng, Kiểm Tra Dữ Liệu), `Kiểm tra nguồn`, `Hashtag theo Folder`, `Ghi chú duyệt`. 81 dòng.
- `D:\OneDrive\Tiktok\Tik2.xlsx` — bản đã duyệt "theo cấu trúc và logic workbook Tik1", `TaiKhoan` 12 cột (thêm Render Status/Render MP4/Render Updated).
- `Tik3.xlsx` MỚI (tạo 2026-08-11) = copy Tik2 + sửa cell ghi chú thành "Bản Tik3 theo cấu trúc và logic workbook Tik1". Cách tạo: `shutil.copy2(Tik2, Tik3)` → openpyxl load/save → sửa sheet `Ghi chú duyệt` cell chứa "Bản Tik2" → verify sheets + headers.
- **CẨN THẬN:** `tik3.xlsx`/`tik4.xlsx` (viết thường) ĐÃ TỒN TẠI sẵn với cấu trúc CŨ khác: 1 sheet `TaiKhoan` 6 cột (`máy/phoneId/taiKhoan/Sttvideo/tenvideo/video gốc`), 142 dòng. Đừng nhầm chúng với Tik3 mới — chưa được đè/xóa khi chưa user yêu cầu.
