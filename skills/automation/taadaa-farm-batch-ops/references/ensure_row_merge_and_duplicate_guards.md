# Kỷ Luật Merge Kết Quả Đăng Ký Tài Khoản & Chống Duplicate (ensure_row / batch_ops)

## 1. NGUYÊN NHÂN LỖI TRÙNG LẶP NICK VÀ LỆCH EXCEL
Trong các đợt chạy reg bù hoặc merge tracking workbook, lỗi nhân bản 1 nick vào nhiều slot (ví dụ cùng lúc ở cả Slot 5 và Slot 7) thường bắt nguồn từ 3 bẫy logic:
1. **Stale Artifact (Quét trôi ngược về quá khứ):** Khi batch reg hiện tại có 0 nick thành công, thư mục run hiện tại rỗng. Vòng lặp `runs_dir.glob("20*")` nếu không có ràng buộc mtime sẽ lùi về quá khứ, bốc lại file kết quả của đợt reg trước đó (10-12 tiếng trước).
2. **Slot Override (Ép tham số dòng lệnh):** Lấy tham số `row` truyền vào (ví dụ `row=5`) ép cứng `slot = row` thay vì đọc `tik` thực tế trong file JSON kết quả của máy. Khi bốc phải kết quả của Row 7, script ghi đè toàn bộ info Row 7 vào dòng Row 5.
3. **Thiếu Unique Constraint Guard:** Không kiểm tra xem TikTok ID hoặc Email đã tồn tại ở bất kỳ dòng nào khác trong workbook trước khi lưu.

---

## 2. QUY TẮC BẢO VỆ BẮT BUỘC KHI MERGE WORKBOOK

### A. Chống Stale Artifact theo `batch_start_time`
Khi khởi động batch:
```python
batch_start_time = datetime.now()
res = subprocess.run(...)
apply_results(row=row, batch_start_time=batch_start_time)
```
Trong hàm `apply_results`:
```python
if batch_start_time is not None:
    min_ts = batch_start_time.timestamp() - 10
    dirs = [d for d in dirs if d.stat().st_mtime >= min_ts]
    if not dirs:
        print("[ensure_row] Khong co run folder moi phat sinh tu luc batch chay. Bo qua merge de tranh stale data.")
        return
else:
    # Nếu chạy thủ công --apply-only: CHỈ lấy đúng run mới nhất duy nhất
    dirs = dirs[:1]
```

### B. Tôn Trọng Slot Thực Tế Từ JSON (`tik`)
```python
raw_tik = int(data.get("tik") or 0)
json_slot = ((raw_tik - 1) % 8) + 1 if raw_tik > 8 else raw_tik

if 1 <= row <= 8:
    if json_slot > 0 and json_slot != row:
        print(f"[ensure_row] Warning: JSON slot {json_slot} khac requested row {row}. Dung json_slot={json_slot}")
        slot = json_slot
    else:
        slot = row
else:
    slot = json_slot if json_slot > 0 else 1
```

### C. Lookup Target Row Chuẩn Xác
Duyệt tìm dòng khớp cặp `(Machine, Expected Tik / Slot)` thay vì dựa hoàn toàn vào công thức cứng:
```python
target_row = None
expected_tik = (m - 1) * 8 + slot
for r in range(2, ws_trk.max_row + 1):
    c1 = ws_trk.cell(r, 1).value
    c2 = ws_trk.cell(r, 2).value
    try:
        if c1 is not None and int(str(c1).strip()) == m:
            if c2 is not None and int(str(c2).strip()) in (expected_tik, slot):
                target_row = r
                break
    except (ValueError, TypeError):
        continue

if target_row is None and 1 <= m <= 80 and 1 <= slot <= 8:
    target_row = (m - 1) * 8 + slot + 1
```

### D. Hard Guard Chống Duplicate UID & Email
```python
existing_uids = {
    str(ws_trk.cell(r, 3).value).strip().lower().lstrip("@"): r
    for r in range(2, ws_trk.max_row + 1)
    if ws_trk.cell(r, 3).value and str(ws_trk.cell(r, 3).value).strip().lower() not in ("none", "")
}
existing_mails = {
    str(ws_trk.cell(r, 6).value).strip().lower(): r
    for r in range(2, ws_trk.max_row + 1)
    if ws_trk.cell(r, 6).value and str(ws_trk.cell(r, 6).value).strip().lower() not in ("none", "")
}

clean_uid = uid.lower().lstrip("@")
if clean_uid in existing_uids and existing_uids[clean_uid] != target_row:
    print(f"[ensure_row] REJECT DUPLICATE UID: @{uid} da ton tai tai dong {existing_uids[clean_uid]}! Khong ghi de vao dong {target_row}.")
    continue

clean_mail = mail.lower()
if clean_mail and clean_mail in existing_mails and existing_mails[clean_mail] != target_row:
    print(f"[ensure_row] REJECT DUPLICATE MAIL: {mail} da ton tai tai dong {existing_mails[clean_mail]}! Khong ghi de vao dong {target_row}.")
    continue
```

### E. Structured Telemetry & Audit Metrics
Mỗi lần merge kết thúc, xuất metrics ra artifact để audit:
```python
metrics = {
    "applied": applied_count,
    "rejected_duplicate_uid": rejected_uid_count,
    "rejected_duplicate_mail": rejected_mail_count,
    "skipped": skipped_count,
    "timestamp": datetime.now().isoformat()
}
metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
```
