# Night-Chain Row 7/8 Feed Alert Triage Guide

## Bối cảnh
`run_night_chain_pipeline.py` (01:00 AM hàng đêm) **LUÔN** chạy Phase 2b nuôi feed Row 7 hoặc Row 8, ngay cả khi Phase 2a (Reg TikTok) không có target mới. Phase 2b KHÔNG phải fallback if-else nữa — nó chạy song song sau Phase 2a (cập nhật 2026-09-07).

- Ngày lẻ → Row 7
- Ngày chẵn → Row 8

## Hai loại lỗi trong batch alert Row 7/8

### Lỗi 1: `account row 7 is empty (no username) for machine X, skipping`
- **Phân loại: CÓ THỂ LÀ BÌNH THƯỜNG (CHƯA REG) HOẶC LỖI NẠP DỮ LIỆU EXCEL (ĐÃ REG NHƯNG CHƯA SYNC)**
- **Nguyên nhân 1 (Bình thường)**: Máy chưa từng được reg nick Slot 7 (hoặc 8). Runner đọc Row 7 trống → skip an toàn theo thiết kế incubator.
- **Nguyên nhân 2 (Bug nạp/sync dữ liệu sau reg bù — Sự cố 17/09/2026)**:
  - Batch reg bù (`ensure_row_accounts.py 7`) đã chạy thành công trong đêm (sinh file `tracking_result_*.json` trạng thái `SUCCESS` trong `runtime/artifacts/runs/social-batch-all/`).
  - Tuy nhiên, do lỗi logic xác định dòng (ví dụ `c2 == slot` trap) hoặc lỗi lệch cấu trúc sheet, các tài khoản mới bị append dồn xuống tận đáy sheet master (`taikhoan_dat_v2_updated .xlsx`) thay vì ghi vào đúng dòng `target_row = 1 + (m-1)*8 + slot`.
  - Script `sync-safe-workbook.py` chỉ lấy 8 dòng đầu của máy (`entries[:8]`), nên các acc ở đáy file bị loại bỏ hoàn toàn $\rightarrow$ `taikhoan_run_safe.xlsx` vẫn trống và runner tiếp tục skip hàng loạt.
- **Hành động chẩn đoán O(1)**:
  1. Kiểm tra nhanh thư mục run reg gần nhất: `runtime/artifacts/runs/social-batch-all/YYYYMMDD*` xem có tracking result `SUCCESS` mới không.
  2. Kiểm tra max_row của `taikhoan_dat_v2_updated .xlsx`: Nếu `max_row > 641`, chắc chắn có acc bị append dồn xuống đáy file.
  3. Reconcile đưa acc về đúng dòng `1 + (m-1)*8 + slot`, xóa các dòng thừa ở đáy, và chạy `sync-safe-workbook.py` để nạp ngay vào safe workbook.

### Lỗi 2: `profile username still mismatched after switch`
- **Phân loại: LỖI THỰC SỰ — cần điều tra**
- **Nguyên nhân**: Runner tìm thấy nick Slot 7 trong account switcher TikTok và tap nhưng sau 2 lần switch, profile vẫn hiện nick khác. Auto-reconcile (`reconcile_tiktok_accounts.py`) được kích hoạt nhưng timeout 900s.
- **Triệu chứng từ log M3 (09/09/2026)**:
  - `expected`: `brifeqme954` (Slot 7)
  - `current_username`: `040d9679d7` (nick khác)
  - Switcher tìm thấy đúng nick (`content_desc=brifeqme954`) và tap thành công 2 lần
  - Sau mỗi lần tap → profile vẫn hiện nick cũ → `manual-needed:account-switcher` loop
  - Auto-reconcile timeout 900s → `finish_reconcile: error`
- **Các máy bị ảnh hưởng điển hình**: Là các máy ĐÃ CÓ nick Slot 7 nhưng TikTok app không switch được (có thể do network kém, app state hỏng, hoặc nick cần login lại)

## Quy trình triage batch alert Row 7/8

```
Nhận batch alert "Row 7/8 empty" rate cao:
    1. Kiểm tra ngày chẵn/lẻ → xác nhận đúng Row được chạy
    2. Tách 2 signature:
       a. "account row N is empty" → bình thường, skip qua
       b. "profile username still mismatched" → lỗi thực sự, cần xử lý
    3. Với nhóm (b): lấy danh sách máy thực sự lỗi
    4. Canary 1 máy: chụp ảnh màn hình xem TikTok app đang ở trạng thái gì
    5. Xác định: nick Slot 7 có tồn tại trên thiết bị không? (Account Switcher có item không?)
    6. Nếu nick không có trên thiết bị → tiktok-log-in reconcile
    7. Nếu nick có trên thiết bị nhưng không switch được → manual clear app state / reboot máy
```

## Kiến trúc `run_night_chain_pipeline.py` (2026-09-07)

```
01:00 AM
  ├─ Phase 1: Reg Gmail (run_all.ps1)
  ├─ Phase 2a: Reg TikTok (_run_all_targets.py)
  │     Nếu 0 target → in "Total targets: 0", exit code non-zero
  │     Nhưng pipeline KHÔNG dừng
  ├─ Phase 2b: Nuôi Feed Row 7 hoặc Row 8 (LUÔN CHẠY)
  │     Ngày lẻ → Row 7; Ngày chẵn → Row 8 (ZoneInfo Asia/Ho_Chi_Minh)
  └─ Phase 3: Add 2FA TikTok (LUÔN CHẠY sau Phase 2b)
```

**Lưu ý quan trọng**: Phase 2b không còn là fallback if-else. Nó chạy SONG SONG sau Phase 2a bất kể kết quả reg. Phase 3 (Add 2FA) cũng vẫn chạy sau đó.

## Tham chiếu code
- Skip logic: `python_runner/core/feed_session_workbook.py` dòng 348-368
- Mismatch handler: `python_runner/flows/feed_swipe_smoke.py` dòng 17424
- Night chain pipeline: `D:/Taadaa/Tiktok_Reg/scripts/run_night_chain_pipeline.py` dòng 984-991
- Incubator architecture: `references/eight-slot-incubator-and-night-chain-feed-fallback.md`
