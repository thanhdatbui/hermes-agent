# Dieu Tra Loi Ro Ri Egress Prompt & False-Positive Regex Nhan Viec Cua Media Gate

## 1. Hien Tuong (Incident Description)
Khi nguoi dung phat lenh:
`"chuan hoa kenh nay"` (kem anh chup man hinh profile).

Thay vi tiep nhan cong viec hoac bat dau phan tich, Telegram cua nguoi dung ngay lap tuc nhan duoc tin nhan tho dang code block ky thuat:
```text
[CONTRADICTION_GATE_TRIGGERED]
verdict: MISSING_MEDIA_EVIDENCE
reason: message claims UI/device completion but contains no MEDIA: evidence tag
...
```

---

## 2. Can Nguyen Ky Thuat (Root Cause Analysis)

### A. Bat nham cau nhan viec (Reception False-Positive Regex)
- Trong bo kiem duyet media vision:
  * Tu khoa `chuan hoa` va `cap nhat` nam trong danh sach hoan tat (`ACTION_COMPLETION_PATTERNS`).
  * Tu khoa `kenh`, `tai khoan`, `profile` nam trong `SUBJECT_PATTERNS`.
- Khi bot phan hoi cau tiep nhan ban dau (vi du: *"Em tien hanh chuan hoa kenh nay..."*), bo doi soat thay xuat hien ca hai cap tu khoa nhung KHONG thay the `MEDIA:`.
- He thong danh dong cau tiep nhan cong viec voi hanh vi bao cao mom hoan thanh UI ma thieu anh bang chung, kich hoat chan `MISSING_MEDIA_EVIDENCE`.

### B. Ro ri prompt cuong che noi bo ra Telegram (Egress Prompt Leakage)
- Ham tao prompt cuong che duoc thiet ke de lam forced re-reasoning prompt noi bo nham ep LLM trong vong lap agent phai suy luan lai, tu dong chup anh hoac bo claim chua chung minh truoc khi xuat ban tin nhan.
- Tuy nhien, o tang plugin gateway, khi gap loi kiem duyet, hook da tra ve prompt cuong che nay lam text thay the cho tin nhan gui di.
- Hau qua: Toan bo doan prompt ky thuat noi bo bi ban thang ra giao dien chat Telegram cua nguoi dung.

---

## 3. Quy Tac & Giai Phap Khac Phuc Chuan

1. **Tuyet doi khong ro ri prompt noi bo ra chat ngoai:**
   - Tang Egress Hook neu phat hien tin nhan vi pham Gate 6 thi BAT BUOC phai giu lai trong agent loop noi bo hoac fallback sang degraded template an toan ngan gon.
   - CAM TUYET DOI xuat nguyen van doan forced re-reasoning prompt ra nen tang chat nguoi dung.

2. **Phan biet rach roi giua Cau Tiep Nhan va Bao Cao Hoan Tat:**
   - Danh sach hanh dong hoan tat CHI DUOC chua cac dong tu chi trang thai ket thuc thuc su: `da doi`, `doi thanh`, `da xong`, `hoan tat`, `da ghim`, `da sua`, `da nap`.
   - CAM dua cac tu chi tien trinh hoac ten quy trinh chung chung nhu `chuan hoa`, `cap nhat`, `kich ban` vao regex bat buoc anh.

3. **Thai do xu ly khi gap su co Gate ro ri:**
   - Tra loi thang vao ban chat ky thuat: Day la prompt noi bo cua Gate kiem duyet anh bi ro ri do bat nham cau nhan viec.
   - Ngan gon, khong vong vo phan tran, khong khoc loc.

---

## 4. Giai Phap Co Hoc O(1) Da Trien Khai (`guard_media_vision_gate.py`)

1. **Bo Loc Cua Nhan Vien `RECEPTION_OR_IN_PROGRESS_MARKERS`:**
   Dua danh sach chan truoc vao ham `_requires_media_evidence`:
   ```python
   RECEPTION_OR_IN_PROGRESS_MARKERS = (
       "nhan lenh",
       "bat dau",
       "dang",
       "dang thuc hien",
       "dang kiem tra",
       "chuan bi",
       "ke hoach",
       "quy trinh",
       "se",
       "huong dan",
       "chuan hoa kenh nay",
       "chuan hoa kenh do",
       "chuan hoa 2 kenh",
       "chuan hoa hai kenh",
       "chuan hoa cac kenh",
       "yeu cau chuan hoa",
       "lenh chuan hoa",
       "tien hanh chuan hoa",
   )

   def _requires_media_evidence(message: str) -> bool:
       norm_msg = _normalize_text(message)
       if any(_phrase_in(norm_msg, kw) for kw in RECEPTION_OR_IN_PROGRESS_MARKERS):
           return False
       return bool(ACTION_COMPLETION_PATTERNS.search(norm_msg) and SUBJECT_PATTERNS.search(norm_msg))
   ```

2. **Kiem Chung Regression Unit Test:**
   Bo test `test_guard_media_vision_gate.py` duoc bo sung test case:
   ```python
   def test_reception_and_in_progress_messages_bypass_gate6(store):
       reception_phrases = [
           "chuẩn hoá kênh này",
           "Dạ em nhận lệnh chuẩn hoá kênh này",
           "Em bắt đầu chuẩn hoá kênh",
           "Đang chuẩn hoá kênh 243",
           "Kế hoạch chuẩn hoá kênh gồm 4 bước",
           "Quy trình chuẩn hoá kênh",
       ]
       for phrase in reception_phrases:
           passed, out = guard.transform_llm_output_check(phrase, store)
           assert passed is True
           assert out == phrase
   ```
   Ket qua toan bo suite 98/98 tests PASSED 100%.
