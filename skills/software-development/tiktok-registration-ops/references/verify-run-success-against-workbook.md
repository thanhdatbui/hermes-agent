# Verify success giả/thật của run cũ + chọn baseline git ổn định

Nguồn gốc: 2026-08-13, user nghi ngờ bản reg hiện tại (13/08) toàn block, hỏi tìm bản cũ ổn định. Yêu cầu: **chứng minh success cũ là THẬT bằng đối chiếu với dữ liệu real hiện tại, rồi mới revert**.

## Quy trình

### 1. Liệt kê run + đếm success/fail theo thời gian

```bash
# Run success thật nằm ở đây (KHÔNG phải .ai-runs/reg_all_* — file đó chỉ toàn dòng lock SKIP 1-dòng)
cd D:/Taadaa/Tiktok_Reg/.ai-runs/social-batch-deferred
for d in $(ls -d 2026* | sort); do
  ok=$(grep -rlE '✅|SUCCESS|Thanh cong' "$d" 2>/dev/null | wc -l)
  fail=$(grep -rlE 'STOPPED|✗|ERROR|FAILED_EXIT|BLOCKED' "$d" 2>/dev/null | wc -l)
  echo "$d OK=$ok FAIL=$fail"
done
```

Kết quả tham chiếu (kibe, 2026): đỉnh success là `20260724-194845` (OK=54 FAIL=46), `20260721-225414` (OK=24), `20260722-070844` (OK=16).

### 2. Trích email SUCCESS từ tracking_result JSON

```python
import json, glob
base = r'D:/Taadaa/Tiktok_Reg/.ai-runs/social-batch-deferred/20260724-194845'
for f in glob.glob(base + '/**/tracking_result_stt*.json', recursive=True):
    d = json.load(open(f, encoding='utf-8'))
    if str(d.get('status', '')).upper() == 'SUCCESS':
        print(d.get('stt'), d.get('email'), d.get('tiktok_id'), d.get('tracking_row'))
```

JSON chứa: `stt`, `email`, `tiktok_id`, `tracking_row`, `status=SUCCESS`, `proof_screenshot`, `proof_xml`, `serial`, `written_at`.

### 3. Đối chiếu với workbook hiện tại — THEO EMAIL, không theo tracking_row

- Cột GMAIL (index 5) trong `taikhoan_dat_v2_updated .xlsx` (tên có space trước .xlsx).
- **Email còn tồn tại trong cột GMAIL = success THẬT** (acc vẫn sống trong tracking).
- **Email missing = success GIẢ** (user xác nhận: "các mail k có là success giả đó").
- KHÔNG tra theo `tracking_row`: row cũ đã lệch sau nhiều lần thêm/xóa dòng.

Kết quả tham chiếu 24/07: 18 SUCCESS → 10 thật / 8 giả. Trong đó `truongthuy111034@gmail.com` ↔ id `truong.thuy950` (chính là máy 34 hiện tại), `tulanh080957@gmail.com` ↔ `phammai1805` (máy 57) — bằng chứng run đó thật.

### 4. Map run → commit git

```bash
git log --format='%h %ad %s' --date=short --since=2026-07-18 --until=2026-07-23
```

Tham chiếu: 21/07 → `0d260f9` (sinh password random), 22/07 → `2447d3a`+`e5ec760` (account switcher), 24/07 → `228e59c`, 25/07 → `c0bd473` (fix: harden TikTok OTP and recovery flow — **bắt đầu loạt sửa gây block**).

### 5. Chọn baseline theo tỉ lệ thật

| Run | Thật/tổng | % | Commit |
|---|---|---|---|
| 20260721-225414 | 11/12 | 92% | `0d260f9` |
| 20260722-072919 | 6/6 | 100% | `2447d3a` |
| 20260722-070844 | 7/8 | 88% | `2447d3a` |
| 20260724-194845 | 10/18 | 56% | `228e59c` |

User chốt **22/07 (`2447d3a`)**. Bản 24/07 có success giả nhiều (đúng user cảnh báo "bản đó reg đc nhưng cũng có success giả nhiều").

### 6. Diff baseline vs HEAD — giải thích "bản mới lỗi hoài"

```bash
git diff --stat 2447d3a HEAD -- *.py          # social_reg_v1.py 6580 → 12289 dòng
git show 2447d3a:social_reg_v1.py > /tmp/social_0722.py
# so sánh hàm chính giữa 2 bản
```

Pattern lặp lại — bản mới fail-closed quá mức:
- `detect_after_continue` 22/07: màn OTP/verify → `registered_otp` **đi tiếp** (resume đọc mail). HEAD: thêm `entry_surface` + `REGISTERED_LOGIN_DEFERRED` → **dừng**.
- `handle_tiktok_email_otp` 22/07: browser fallback + resend loop. HEAD: fail-closed newest-reader only → mailbox không vào được thì dừng cứng.
- Thêm host guard (`taadaa_host.py`), workbook adapter, device_lock phức tạp.

### 7. Thao tác an toàn

- Tạo branch từ baseline: `git branch reg-stable-0722 2447d3a` — GIỮ working tree hiện tại, không hard reset khi chưa user chốt.
- Chuyển branch riêng để reg tiếp, so diff sau.

## Cảnh báo

- `git diff --stat` của 22/07→HEAD rất lớn (43 files, 10051 insertions) — KHÔNG revert mù; xác định hàm cụ thể gây block rồi mới swap (xem `swap-functions-between-git-revisions.md`).
- Nếu chỉ cần bỏ phần hỏng: swap hàm bằng AST script giữa 2 bản, giữ các fix khác (không reset toàn bộ).
