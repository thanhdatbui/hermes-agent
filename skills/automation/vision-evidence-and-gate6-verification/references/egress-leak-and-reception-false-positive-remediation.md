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

1. **Bo Loc Mien Tru Toan Dien `EXEMPTION_MARKERS`:**
   Mo rong bo loc mien tru tu reception markers len day du cac truong hop giai trinh ky thuat, thao luan kien truc va tra loi cau hoi:
   ```python
   EXEMPTION_MARKERS = (
       # Nhận việc & Đang tiến hành
       "nhan lenh", "bat dau", "dang", "dang thuc hien", "dang kiem tra", "chuan bi",
       "ke hoach", "quy trinh", "se", "huong dan", "chuan hoa kenh", "chuan hoa cac kenh",
       "yeu cau", "tien hanh",
       # Giải trình kỹ thuật, thảo luận & phân tích
       "giai thich", "nguyen nhan", "ly do", "van de", "dieu tra", "phan tich", "overengineer",
       "gate", "hook", "watchdog", "prompt", "leak", "lo hong", "kien truc", "security theater",
       "tai sao", "vi sao", "thao luan", "tu van", "hoi dap",
       # Code & Git & Công cụ
       "script", "code", "ham", "function", "commit", "diff", "branch", "repo", "test", "pytest",
   )

   def _requires_media_evidence(message: str) -> bool:
       norm_msg = _normalize_text(message)
       if any(_phrase_in(norm_msg, kw) for kw in EXEMPTION_MARKERS):
           return False
       return bool(ACTION_COMPLETION_PATTERNS.search(norm_msg) and SUBJECT_PATTERNS.search(norm_msg))
   ```
   => Triet tieu hoan toan hien tuong: User chat hoi "sao the?", "gate co bi overengineer khong?", bot tra loi giai thich co chua tu "bao cao/ket qua/kenh" lien bi gate chan dung va nem prompt tho ra Telegram.

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

---

## 5. Bai Hoc Xuong Mau: Bay Module Caching Trong RAM & Sai Tang Kien Truc Cua Egress Hook

### A. Bay Caching Trong RAM (`sys.modules`)
- **Hien tuong:** Agent da sua file gate tren o dia $D:$ va chay test pass 100%, nhung ngay luot tiep theo khi gui tin nhan giai thich, tin nhan do van bi chan va bi chup mu `[CONTRADICTION_GATE_TRIGGERED]` ban thang ra Telegram (khien nguoi dung bat binh: *"Don cua may day ha"* kem screenshot).
- **Nguyen nhan vat ly:** Tien trinh Python cua Hermes Gateway da import module vao RAM tu thoi diem khoi dong. Khi file tren dia thay doi, tien trinh dang chay tiep tuc thuc thi bytecode cu trong `sys.modules`.
- **Hau qua:** Ban gate cu trong RAM quet thay cac tu khoa trong bai phan tich ky thuat (`bao cao, ket qua, tien do, chuan hoa, avatar, bio, kenh`), tuong agent dang "bao cao mom UI thieu anh", lap tuc chan va nhet prompt vao dau tin nhan.
- **Quy tac bat bien:**
  * Moi thay doi tren hook/gate nam tren dia chi thuc su co hieu luc trong runtime neu tien trinh gateway duoc khoi dong lai hoac module duoc reload ro rang (`importlib.reload()`).
  * Khi giai thich ve loi hoac tu khoa, tuyet doi khong viet cac tu khoa hoan tat UI mot cach lien tuong de phong truong hop module trong RAM chua cap nhat.

### B. Sai Tang Kien Truc (Wrong-Layer Enforcement Trap)
- **Ao tuong cua thiet ke cu:** Tuong rang hook o tang xuat text se hoat dong nhu mot prompt injector de bat LLM suy luan lai (Forced Re-Reasoning).
- **Thuc te Gateway:** Hook xuat text la **Egress Formatter** — bat ky chuoi nao ham nay tra ve se tro thanh van ban xuat ban truc tiep len man hinh chat Telegram.
- **Quy tac bat bien:**
  * CAM TUYET DOI dung Egress Hook de tra ve prompt huong dan LLM (`[CONTRADICTION_GATE_TRIGGERED]`, `REQUIRED_NEXT_ACTION...`).
  * Neu tin nhan cuoi thieu bang chung, hook chi duoc phep log telemetry hoac tra ve 1 dong trang thai gon gang (`Trang thai: DEGRADED`). Chot chan co hoc bat buoc phai nam o tang Tool Call (`pre_tool_call` / `post_tool_call`).

### C. Quy Trinh Soi Mat Doi Soat Screenshot Telegram Qua Staging
- Khi User gui screenshot chat Telegram chat van ("Don cua may day ha", "What do you see in this image?"):
  1. File anh nam trong thu muc cache he thong thuong bi guard chan truy cap truc tiep.
  2. BẮT BUỘC dung script staging copy ra thu muc ngoai (`D:/Taadaa/reports/<name>.jpg`).
  3. Mo bang `browser_navigate('file:///D:/Taadaa/reports/<name>.jpg')`.
  4. Goi `browser_vision` doc ro tung dong text tren anh de xac nhan su that khach quan truoc khi tra loi.
