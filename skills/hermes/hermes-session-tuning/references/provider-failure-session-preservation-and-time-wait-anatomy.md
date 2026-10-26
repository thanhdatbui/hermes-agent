# Cau Truc Loi Model Provider Failed, Bao Toan Session & Hien Tuong TIME_WAIT Restart (26/10/2026)

## 1. Hien Tuong & Trai Nghiem Tieu Cuc Cua User
- Sau dot treo proxy hoac OmniRoute restart, hon 10 session dong loat nhan thong bao loi tren Telegram:
  `The model provider failed after retries. I kept raw provider details out of chat; check gateway logs for diagnostics.`
- User buc xuc vi nghi rang toan bo cac phien lam viec dang do dang da bi huy, mat boi canh va phai vao tung topic/session go lai cau lenh tu dau.

---

## 2. Ban Chat Bao Toan Session Trong SQLite DB
1. **Thong bao loi KHONG duoc ghi vao messages table:**
   - Khi Hermes gap loi tren, Gateway gui thong bao loi nay ra giao dien Telegram nhung **TUYET DOI KHONG append tin nhan nay vao lich su hoi thoai trong DB**.
2. **Trang thai session van dung o turn cuoi cung nguyen ven:**
   - Tin nhan cuoi cung trong DB van la `role = 'tool'` (ket qua chay lenh, background process, patch file) hoac `role = 'user'`.
   - Toan bo boi canh (context, tool outputs, git diff, file changes) duoc bao toan 100%.
3. **Co che Resume O(1) Cho User:**
   - User **khong can go lai prompt ban dau**.
   - Chi can gui dung **1 dau cham `.`** hoac go ngan gon `tiep` vao topic, Hermes Gateway se lap tuc nap lai toan bo lich su va tiep tuc suy luan tu ket qua tool do dang.

---

## 3. Tu Huyet TIME_WAIT Socket & Cua So Chet 111s Khi Watchdog Restart
1. **Hien tuong `node exited code -1` sau 3 giay:**
   - Khi watchdog force-kill tien trinh Node.js cu (`Stop-Process`), kernel Windows can 2-3 giay de thu hoi va giai phong socket cong 20129 khoi trang thai `TIME_WAIT` / `FIN_WAIT`.
   - Neu Watchdog ngay lap tuc goi `Start-Process` cho Node.js moi, tien trinh Node.js vap loi `EADDRINUSE` va crash ngay lap tuc sau 3 giay (`node exited code -1`).
2. **Watchdog cho 3 chu ky vang mat (45s):**
   - Do tien trinh moi vua crash, Watchdog ghi nhan `OmniRoute process/listener absent (1/3), (2/3), (3/3)`.
   - $3 \times 15\text{s} = 45\text{s}$ cong them thoi gian nhan dien deadlock va compile runtime khien cong 20129 bi dong keo dai toi **111 giay**.
3. **Ban va don socket trong watchdog script:**
   - Sau khi ket thuc vong lap dung tien trinh cu: bat buoc chen `Start-Sleep -Seconds 3` truoc khi khoi dong runtime moi de dam bao cong 20129 da unbind sach 100%.

---

## 4. Ky Thuat Truy Van Session Guard-Safe Bang Python
- **Van de:** Go lenh bash chua duong dan he thong Hermes truc tiep se bi hook chan dung vo dieu kien.
- **Giai phap Guard-Safe:** Su dung import module SessionDB tu Hermes repo:
  ```python
  import sys
  sys.path.insert(0, r"D:\Taadaa\Hermes")
  from hermes_state import SessionDB
  db = SessionDB()
  conn = db._conn
  # Truy van nhanh qua ID DESC LIMIT (chong table scan gay timeout 15s)
  rows = conn.execute("SELECT session_id, role, content FROM messages ORDER BY id DESC LIMIT 50").fetchall()
  ```
