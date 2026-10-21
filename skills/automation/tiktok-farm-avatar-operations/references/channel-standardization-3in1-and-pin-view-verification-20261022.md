# Chuan Hoa Kenh 3 Mon & Ky Luat Pin Top Video (2026-10-22)

## 1. Dinh Nghia Chuan Hoa Kenh (3-in-1 Standardization Bundle)
Khi User yeu cau chuan hoa kenh (hoac chuan hoa acc), bat buoc thuc hien du 3 mon:
1. **Avatar Moi Chuan Niche:**
   - Trich xuat frame ro net tu video goc hoac ung vien da duyet, ti le 1:1, khong dinh caption/chu, khong logo rac.
   - Sao chep vao avatar.jpg tai ca thu muc video goc va thu muc render.
   - Dat co khoa .manual_avatar_locked va dang ky vao danh sach bao ve.
2. **Hashtag / Niche Dong Bo 3 Tang:**
   - Khop niche giua co so du lieu trung tam va cac tap tin Excel (Tik1 - Tik8 cua ca Kibe va Admin).
   - Dat co khoa .manual_hashtag_locked va dang ky vao danh sach bao ve hashtag.
3. **Pin Top Video (Ghim Video View Cao >= 1.000 views):**
   - Chay script pin_top_videos.py voi tham so --machine, --account va --min-views 1000.
   - Kiem tra cac clip viral (luot xem > 1K, > 10K, > 20K). Neu clip view cao chua duoc ghim, bat buoc dung action swap de ha clip view thap va dua clip viral len vi tri ghim dau tien.

## 2. Bay Ao Giac Soi Mat Luoi Video (Grid Inspection Trap)
- **Hien tuong:** Nhin thay nhan "Da ghim" o goc tren ben trai (Hang 1 Cot 1) roi voi va ket luan clip viral da ghim, trong khi thuc te clip viral nam o vi tri khac (vi du Hang 2 Cot 3) va hoan toan chua duoc ghim.
- **Ky luat kiem chung OCR/Vision:**
  * Doc tach biet tung o (tile) trong luoi 3 cot cua Profile.
  * Xac dinh ro clip nao dat luot view cao nhat.
  * Kiem tra truc tiep tren thumbnail cua clip do co nhan "Da ghim" hay khong.
  * Neu clip view cao nhat chua co nhan ghim, bat buoc ghi nhan trang thai PIN = PENDING/FAILED, cam bao DONE.

## 3. Xu Ly Khi Ket Device Lock (Ca Nuoi Nick)
- Khi tool pin video gap device lock do ca nuoi nick dinh ky dang giu thiet bi:
  * Cam kill process, cam xoa lock cua ca nuoi dang chay.
  * Hoan tat cac buoc offline (avatar, marker lock, workbook sync).
  * Bao cao ro rang: Avatar va Hashtag da xong; buoc Pin video dang doi thiet bi nha lock. Cam bao xong khi chua ghim tren thiet bi that.
