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

---

## 6. Cạm Bẫy Phân Rã Toàn Bộ Chuỗi (Exact-Only Segmentation Trap) & Giải Pháp 2-Stage Prefix Matching

- **Sự cố thực tế**: Tại Máy 68, username là `ngohaaenexi`. Hệ thống lại đổi thành `Hoàng Phước Châu`.
- **Triệu chứng & User Feedback**: *"Vì sao tên user ngonaaenexi mà lại đặt tên hoàng phước châu"*.
- **Root Cause**:
  - Username được tạo từ tool reg mail thường có tiền tố Họ + Tên có nghĩa (`ngo` + `ha`) nhưng phần đuôi lại bị dính các ký tự rác ngẫu nhiên (`aenexi`).
  - Hàm phân rã cũ sử dụng đệ quy `find_segments` yêu cầu khớp sạch 100% không sót ký tự nào. Khi gặp đuôi rác `aenexi` không nằm trong từ điển âm tiết tiếng Việt, hàm trả về rỗng `[]`.
  - Kết quả: Bộ sinh tên ngộ nhận đây là username ngoại lai hoàn toàn, rơi vào nhánh fallback ngẫu nhiên và gán tên `Hoàng Phước Châu`.
- **Giải pháp chuẩn hóa (2-Stage Matching)**:
  - Giai đoạn 1: Thử phân rã toàn bộ chuỗi (`exact match`). Nếu khớp hoàn toàn $\rightarrow$ Trả về kết quả ngay.
  - Giai đoạn 2 (Prefix Greedy Fallback): Nếu không khớp hoàn toàn, duyệt tuần tự từ đầu chuỗi bằng tham lam tiền tố dài nhất (`text.startswith(w)`), nhặt toàn bộ các âm tiết Họ - Đệm - Tên ở đầu chuỗi cho đến khi gặp ký tự rác thì dừng lại.
  ```python
  exact = find_segments(raw)
  if exact:
      return exact

  segs = []
  text = raw
  while text:
      matched = False
      for w in words_sorted:
          if text.startswith(w):
              segs.append(w)
              text = text[len(w):]
              matched = True
              break
      if not matched:
          break
  return segs
  ```
  - **Hiệu quả**: `ngohaaenexi` bóc tách được ngay `['ngo', 'ha']`, sinh ra tên `Ngô Hà` hoặc `Hà Bơ` / `Hà Đậu` thay vì bị đổi tên ngẫu nhiên sai lệch.

---

## 7. Cạm Bẫy False-Positive Trong `is_target()` Khi Tên Cũ Dính Số Đuôi Username

- **Sự cố thực tế**: Tại Máy 63, username là `phannhung1710`. Runner báo kết quả `"ALREADY"` (đã đổi) nhưng ảnh thực tế trên Profile vẫn là `phannhung1710`.
- **Triệu chứng & User Feedback**: Gửi ảnh màn hình Profile và hỏi *"Có thấy đổi thành phan nhung đâu"*.
- **Root Cause**:
  - Tên hiển thị cũ trên màn hình vẫn là username gốc: `phannhung1710`.
  - Tên mục tiêu cần đổi là `Phan Nhung` (`NEW_NAME_NORM = "phan nhung"`).
  - Thuật toán `difflib.SequenceMatcher(None, "phannhung1710", "phan nhung").ratio()` cho ra kết quả **`0.7826` (78.26%)**, vượt ngưỡng `>= 0.75`!
  - Kết quả: Runner tưởng tài khoản đã được đổi sang tên mới rồi nên bỏ qua khâu gõ tên, không bấm Lưu và xuất ảnh báo hoàn tất khống.
- **Giải pháp chuẩn hóa (Digit-Suffix Guard)**:
  - Bổ sung chốt chặn kiểm tra chữ số đuôi trước khi tính tỷ lệ tương đồng:
  ```python
  def is_target(name_line):
      if not name_line:
          return False
      nl = norm(name_line)
      if re.search(r"\d{2,}$", nl):
          return False
      if nl == NEW_NAME_NORM:
          return True
      return difflib.SequenceMatcher(None, nl, NEW_NAME_NORM).ratio() >= 0.75
  ```
  - **Hiệu quả**: Mọi tên hiển thị còn dính từ 2 chữ số trở lên ở đuôi (dấu hiệu đặc trưng của username chưa đổi) sẽ bị `is_target()` từ chối ngay lập tức, ép runner phải vào màn hình nhập tên và gõ tên chuẩn có dấu.

