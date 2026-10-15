# Quy Trinh Chuan Hoa Kenh TikTok Toan Dien: Bo Ba Ava - Hashtag - Pin (Channel Standardization Triad Protocol)

## 1. Chi Thi Bat Buoc Cua User
Khi nguoi dung yeu cau: "chuan hoa kenh nay" hoac "chuan hoa kenh <anh/ten>":
Coordinator BAT BUOC tu dong kiem tra va doi soat DU BO 3 TIEU CHI:
1. Avatar (Ava)
2. Hashtag & Niche
3. Pin (Ghim top video)

Tuyet doi khong duoc bo sot tieu chi nao.

---

## 2. Tieu Chi 1: Avatar (Ava) & Co Che Khoa Thu Cong
1. **Doi soat thuc te**:
   - Soi anh avatar tren profile (anh dinh kem hoac live capture) voi luoi video cua kenh.
   - Tranh cac bay nham lan: kenh nguoi that nhung ava dong vat, logo to chuc, hoac anime.
2. **Co che co khoa (Manual Lock Flag)**:
   - Khi kenh da duoc chinh sua tay, he thong bao ve qua cac co khoa:
     * Registry JSON: Danh sach cac folder duoc bao ve trong file cau hinh manual avatar protection.
     * File marker vat ly: `.manual_avatar_locked` dat trong thu muc video goc va thu muc render.
     * Khi co co nay, cac tool tao ava hang loat tu dong phai bo qua (skip), khong duoc phep de anh.
3. **Kiem tra len app thuc te**:
   - Neu trong kho da co anh chuan nhung tren app TikTok chua duoc cap nhat (do cot Avatar trong Excel ghi OK nen watchdog bo qua):
     * Dat lai trang thai PENDING trong Excel va hang doi de runner nap avatar chuan len profile thiet bi.
     * Nghiem thu bang chung thi giac qua browser_vision.

---

## 3. Tieu Chi 2: Hashtag & Niche (Chong Cronjob Ghi De)
1. **Doi soat chu de video**:
   - Kiem tra noi dung video thuc te so voi Keyword Video va Hashtag Pool trong file Excel cua slot tuong ung.
2. **Nguyen tac chong ghi de tu dong**:
   - Tren farm, cronjob dong bo tu khoa chay dinh ky se lay nhan tu CSDL trung tam ghi vao file Excel.
   - Neu chi sua tay trong file Excel ma khong dong bo CSDL goc, cronjob se tu dong ghi de lai nhan cu sau vai phut.
   - Vi vay, khi chuan hoa niche/hashtag, bat buoc phai cap nhat dong bo ca hai dau:
     * Cap nhat CSDL goc (bang luu folder va niche).
     * Cap nhat ca 2 sheet TaiKhoan va Hashtag theo Folder trong file Excel quan ly slot.

---

## 4. Tieu Chi 3: Pin (Ghim Top View Len Dau Trang)
1. **Tieu chuan ghim**:
   - Quet luot xem cua tat ca video tren luoi profile.
   - Tim cac video co luot xem cao vuot troi (>= 1.000 views) nhung chua co nhan "Da ghim".
   - Ghim toi da 2 den 3 video top view theo quy dinh.
2. **Thuc thi qua cong cu canonical**:
   - Su dung tool pin_top_videos voi day du thong so machine, account, min-views va max-pins.
   - Thao tac duoc boc trong device lock de dam bao an toan thiet bi.
   - Kiem tra lai ket qua sau khi ghim bang cach dump UI profile.
