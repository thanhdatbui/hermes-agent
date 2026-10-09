# Fix → Canary Pipeline Discipline (User Correction 09/09/2026)

## Quy tắc bắt buộc

Khi fix lỗi farm (code sửa xong → commit), Coordinator BẮT BUỘC dispatch **1 worker duy nhất** thực hiện cả 2 bước trong cùng 1 goal:
1. Sửa code + commit
2. Canary verify ngay sau commit

**CẤM** tách thành 2 bước riêng: fix xong → chờ user nhắc → mới canary.

## Nguồn gốc correction

User correction (09/09/2026):
> "Sửa xong phải chạy run canary lại script lỗi chứ???"
> "Là m dự định làm sau khi sửa xong hay t nhắc ms làm v"

Coordinator đã commit fix `PROFILE_SWITCH_MAX_ATTEMPTS 2→3` nhưng không tự chạy canary — phải chờ user nhắc 2 lần mới chạy. Đây là lỗi nghiêm trọng về tự chủ workflow.

## Thứ tự đúng

```
1. Nhận Farm Alert
2. Inspect log (O(1)) → phân loại bình thường vs lỗi thực
3. Dispatch worker: [sửa code] + [commit] + [canary verify] — 1 goal duy nhất
4. Worker báo cáo: commit SHA + canary result
5. Coordinator nhận kết quả → nếu canary green → mới chốt phiên
```

Chốt phiên = bước **sau cùng** khi canary đã green, không phải khi fix xong.

## Lệnh canary chuẩn cho tiktok-luot nuoi acc

```
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" \
  -Row <N> -Machines <canary_machine> \
  -SkipAccountWorkbookSync -MaxWorkers 1 -RecoveryTestSwipes 2 -Run
```

- `-Row <N>`: đúng row của ca lỗi (tính từ timestamp alert + parity schedule)
- `-Machines <M>`: chọn 1 máy trong danh sách lỗi (ưu tiên máy đầu tiên)
- `-SkipAccountWorkbookSync`: không cần sync workbook khi canary
- Kết quả xanh: `profile username matched expected account` hoặc `status: success`

## Case áp dụng: PROFILE_SWITCH_MAX_ATTEMPTS fix (09/09/2026)

- Alert: 15/80 máy `profile username still mismatched after switch` ca Row 7
- Fix: `PROFILE_SWITCH_MAX_ATTEMPTS = 2` → `= 3` tại `feed_swipe_smoke.py:625`
- Canary M3 Row 7: **green** (`profile username matched expected account`)
- Commit: `7430415`

## Parity Schedule (để tính đúng Row từ timestamp alert)

| Ngày   | Ca 1 (06:00) | Ca 2 (12:30) | Ca 3 (19:00) | Đêm (01:00) |
|--------|-------------|-------------|-------------|------------|
| Lẻ     | Row 1       | Row 3       | Row 5       | Row 7      |
| Chẵn   | Row 2       | Row 4       | Row 6       | Row 8      |
