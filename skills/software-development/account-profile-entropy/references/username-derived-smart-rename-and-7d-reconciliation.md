# Username-Derived Smart Rename & 7-Day Cooldown Reconciliation

## 1. Problem & User Steering
Khi đổi biệt danh ("display name") cho tài khoản TikTok hàng loạt trên phone farm:
- **Lỗi trước đây**: Đổi ngẫu nhiên từ pool Họ + Đệm + Tên không liên quan gì đến `@username` (ví dụ `@duongkien1202` bị đổi thành `Yến Mập`, `@vothitram` bị đổi thành `Hải Cường`).
- **Chỉ đạo bắt buộc từ User**:
  1. Tên hiển thị **BẮT BUỘC phải gần giống / bắt nguồn từ `@username`** (ví dụ `@vothitram` thì đổi thành `Võ Thị Trâm` hoặc `Trâm Bơ`, `Trâm Miu`).
  2. **Tăng tính random mạnh mẽ**: Không được ra 1 kết quả cố định cho cùng 1 username nếu chạy lại; phân bổ đa dạng các biến thể tự nhiên.
  3. **Hàng chờ 7 ngày cho các nick lỡ đổi sai**: Các nick trước đó đã đổi tên không khớp username phải được giữ trong hàng chờ 7 ngày (`COOLDOWN_DAYS = 7`), hết cooldown mới bốc ra đổi lại đúng chuẩn.

---

## 2. Vietnamese Syllable Segmentation Engine (`smart_name_generator.py`)

Do `@username` thường không có dấu và viết liền (e.g. `vothitram`, `lequynh2043`, `thiphong960`, `buitruc190`):
1. **Từ điển âm tiết tiếng Việt**:
   - `HO_MAP`: nguyen, tran, le, pham, hoang, huynh, phan, vu, vo, dang, bui, do, ho, ngo, duong, ly, dinh, truong, luu, dao, ha, luong, mai, trinh...
   - `DEM_MAP`: van, thi, ngoc, hoang, minh, quang, thanh, duc, dinh, huu, xuan, hai, thu, bao, anh, cong, trong, gia, tuan, phuoc, kim, tien, hong, phuong, khanh, duy, nhat, thao, my, quoc...
   - `TEN_MAP`: an, binh, cuong, dung, dat, ha, hai, hieu, hoang, huy, hung, khoa, kien, lam, linh, long, minh, nam, nghia, phong, phuc, quan, quang, son, thang, thanh, thao, thinh, tien, toan, trung, tuan, tung, viet, vinh, vu, xuan, trang, huong, lan, mai, ngoc, phuong, quynh, thuy, van, yen, nhi, vy, ly, tuoi, hoan, tram, ngan, loan, tuyen, hoa, nga, giang, chau, trinh, duyen, nhung, huyen, hang, truc, loc, kieu, chi, diep, tu, tam, tai, nhan, hien, nghi...
2. **Thuật toán Greedy / Longest-Prefix Segmenter**:
   - Tách chuỗi chữ cái thường thành danh sách các âm tiết tiếng Việt hợp lệ:
     `vothitram` -> `['vo', 'thi', 'tram']`
     `duongkien1202` -> `['duong', 'kien']`
     `thiphong960` -> `['thi', 'phong']`
     `tuan31075` -> `['tuan']`

---

## 3. High-Entropy Natural Distribution (Tăng Tính Random)

Khi phân tách được các âm tiết:
- **Trường hợp >= 2 âm tiết (`['vo', 'thi', 'tram']`):**
  - **35% Tên đầy đủ có dấu**: `" ".join(accented)` -> `Võ Thị Trâm`
  - **35% Tên chính + Biệt danh đời thường**: `f"{main_ten} {choice(NICK_SFX)}"` -> `Trâm Bơ`, `Trâm Miu`, `Trâm Na`, `Trâm Sóc`, `Trâm Mây`, `Trâm Xù`, `Trâm Dâu`, `Trâm Sữa`...
  - **15% Đệm + Tên chính**: `f"{dem} {main_ten}"` -> `Thị Trâm`, `Ngọc Trâm`
  - **15% Họ + Tên chính**: `f"{ho} {main_ten}"` -> `Võ Trâm`
- **Trường hợp 1 âm tiết (`['tuan']`):**
  - **60% Tên chính + Biệt danh**: `Tuấn Miu`, `Tuấn Thỏ`, `Tuấn Bơ`...
  - **40% Đệm + Tên chính**: `Minh Tuấn`, `Duy Tuấn`, `Anh Tuấn`...
- **Trường hợp chuỗi ký tự ngoại lai / không phân tách được (e.g. `jorgebnstdk`, `stutectzyes`):**
  - Nhận diện tiền tố ngữ âm: `lily` -> `Linh`, `fran` -> `Phương`, `debi` -> `Diệp`, `anci` -> `An`, `sado` -> `Sa` + Biệt danh.
  - Fallback ngẫu nhiên Họ + Đệm + Tên hoặc Tên + Biệt danh chuẩn người thật.

---

## 4. Kiểm Thử Quan Hệ Username ↔ Name (`is_name_related_to_username`)

Để phân loại nick nào cần đổi lại mà không dựa vào exact match:
```python
def is_name_related_to_username(name: str, username: str) -> bool:
    if not name or not username: return False
    words = name.strip().split()
    if len(words) < 2 or re.search(r"\d{2,}$", name.strip()): return False
    segs = parse_username_syllables(username)
    if not segs: return True # foreign/unparsed -> pass
    name_norm = norm(name)
    name_words = name_norm.split()
    for seg in segs:
        seg_norm = norm(seg)
        if seg_norm in name_words or seg_norm in name_norm:
            return True
    return False
```

---

## 5. Kỷ Luật Hàng Chờ 7 Ngày (7D Cooldown Reconciliation)

TikTok giới hạn nghiêm ngặt: Mỗi tài khoản chỉ được đổi biệt danh **7 ngày 1 lần**.
1. **Lưu trữ trạng thái (`rename_natural_state.json`)**:
   - Bắt buộc ghi lại `renamed_at` (ISO timestamp) và ảnh bằng chứng `proof` cho mọi nick đổi thành công.
2. **Xếp hàng chờ tự động trong Watchdog**:
   - Watchdog kiểm tra:
     ```python
     if u in state:
         days_passed = (now - datetime.fromisoformat(state[u]["renamed_at"])).days
         if days_passed < 7:
             continue # Bỏ qua, chưa đủ 7 ngày
     ```
   - Khi `days_passed >= 7` VÀ tên hiện tại trong `STATS_XLS` không ăn khớp username (`not is_name_related_to_username(current_name, u)`):
     -> Watchdog tự động đưa vào danh sách ứng viên (`candidates`) để đổi lại tên chuẩn mới theo `smart_name_generator`.
