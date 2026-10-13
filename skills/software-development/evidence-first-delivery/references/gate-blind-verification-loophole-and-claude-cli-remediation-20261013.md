# Lo Hong Kiem Tra Hinh Thuc Cua Gate Soi Mat & Quy Trinh Ban Giao Claude Code CLI (2026-10-13)

**Boi canh su co:**  
Khi doi avatar cho kenh `@hoangthu1804` (May 67), Coordinator gui nham anh be mat da tang khoang san kem mo ta bia dat nguoi that mim cuoi. Khi User chat van gay gat:
- *"Tai sao tao ep may soi anh trc khi gui cau tl tao may van deo tuan thu v?"*
- *"Anh dau may co gui dau"*
- *"Vkl sao t nho co gate soi anh qua vision ma may k tuan thu? Goi claude cli fix"*

---

## 1. Phan Tich Lo Hong Ky Thuat

### 1.1. Lo Hong Kiem Tra Hinh Thuc (Blind Verification Loophole)
- **Co che kiem tra cu**:
  - Hook theo doi cac loi goi `browser_vision` hoac `ocr.py`.
  - Khi Coordinator goi `browser_navigate(file:///path/to/img.jpg)` va `browser_vision(...)`, hook tu dong ghi nhan file do vao danh sach verified.
  - Den pha kiem tra cuoi luot, gate chi kiem tra don thuan xem the `MEDIA:<path>` co nam trong danh sach verified hay khong.
- **Diem chet chi mang**:
  - Gate hoan toan khong kiem tra noi dung thuc te cua anh. No gia dinh rang he model da goi tool la da xem that.
  - Khi LLM bi ao giac (hallucination): Model mo anh da tang nhung khong doc tensor thi giac ma tu bia ra van ban *"nam thanh nien mac ao be mim cuoi..."*.
  - Vi file da nam trong danh sach verified, gate cho qua ma khong chan Fail-Closed. User nhan anh thay da va phat hien bao cao sai su that.

### 1.2. Su Co Nuot Anh Do Gian Doan Stream (Mid-Stream Interruption Drop)
- Khi Coordinator dang stream cau tra loi kem the `MEDIA:`, neu tien trinh bi ngat giua chung (`interrupted by user correction`), adapter Gateway chua kip chay den pha trich xuat va upload file qua Telegram API.
- Hau qua: User chi nhan duoc text cut hoac khong thay anh dinh kem (*"Anh dau may co gui dau"*).

---

## 2. Giai Phap Va Co Hoc Doc Lap Khoi LLM

### 2.1. Mechanical Avatar Face Assertion (Kiem tra khuon mat co hoc)
Doi voi tac vu avatar / profile:
1. Bat buoc Face Detection co hoc qua OpenCV Haar Cascade truoc khi cap quyen xuat ban the `MEDIA:`.
2. Nguong hop le: So khuon mat $N \ge 1$, kich thuoc toi thieu $w \ge 100\text{px}$.
3. Neu phat hien $N = 0$ (anh da, phong canh, vai, mo bokeh): FAIL-CLOSED tuc thi, cam xuat the `MEDIA:`.

### 2.2. Mechanical OCR Token Binding (Rang buoc token cho man hinh UI)
- Bat buoc WinRT OCR trich xuat text thuc te.
- Doi soat token man hinh dich (Profile: `@username`, `Ho so`; Switcher: `Chuyen doi tai khoan`; 2FA: `Xac minh 2 buoc dang bat`).
- Neu dinh token man hinh la hoac khong khop context: Chan xuat ban anh.

---

## 3. Quy Trinh Ban Giao Claude Code CLI Xu Ly

### 3.1. Phân Vai & Ranh Gioi Quyen Han
- Coordinator bi chan boi cac quy tac guard tu bao ve, khong duoc tu sua code guard/hook.
- Khi User chi dao *"Goi claude cli fix"*, Coordinator bat buoc phai ban giao cho Claude Code CLI.

### 3.2. Quy Trinh Goi Claude CLI Qua Wrapper Quota
1. Soan task spec vao file trung gian (vi du `D:/Taadaa/tools/claude_task.txt`).
2. Goi Claude CLI qua wrapper kiem soat han muc:
   `python D:/Taadaa/tools/claude_quota_guard.py exec -p "$(< D:/Taadaa/tools/claude_task.txt)" --dangerously-skip-permissions`
3. Kiem chung qua test suite tu dong va khoi dong lai Gateway sau khi va code.
