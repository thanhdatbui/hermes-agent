# Cạm Bẫy Ép Tọa Độ Switcher Full-Width Container (Dead Whitespace Tap) & Bài Học Đối Soát Phiên Bản TikTok (Case Máy 8 vs Case Máy 79)

## 1. Hiện tượng thực tế (Sự cố Máy 8 sau bản vá Máy 79)
- **Cảnh báo farm**: `[FARM ALERT: MÁY 8] DỪNG PHIÊN - Nick: tolmavhj12k - profile username still mismatched after switch`.
- **Triệu chứng Canary**:
  - Sheet *Chuyển đổi tài khoản* mở lên đầy đủ, nick `tolmavhj12k` xuất hiện rõ trong danh sách (`content-desc="tolmavhj12k"`, resource-id `com.ss.android.ugc.trill:id/lkp`, bounds `[0, 600][1080, 816]`).
  - Runner thực hiện 2 lần mở Account Switcher để tap chọn nick, nhưng sau khi tap, màn hình Profile vẫn giữ nguyên tài khoản cũ (`Donie` / `donieovhdvc`).
  - Runner kích hoạt `auto_login_recovery` qua `reconcile_tiktok_accounts.py`, hết timeout và dừng an toàn với `profile username still mismatched after switch`.

---

## 2. Nguyên nhân kỹ thuật cốt lõi (Technical Root Cause)

### A. Sự khác biệt giữa phiên bản TikTok 46.2.3 (Cũ) và 46.7.3 (Chuẩn Farm)
1. **Trên TikTok 46.2.3 (Case Máy 79 & 78 trước đây):**
   - Hàng tài khoản là một `android.widget.Button` (`com.ss.android.ugc.trill:id/l9b`).
   - Bên trong chứa child `TextView` (`id/mtx`, `clickable="false"`).
   - Khi tap vào child TextView không clickable ở giữa màn hình (`x = 397`), touch event bị Samsung nuốt và Button cha không nhận click.
2. **Bản vá sai lầm do khái quát hóa quá mức (Overgeneralized Fix):**
   - Để "xử lý" lỗi Máy 79, code đã thêm điều kiện:
     ```python
     if node.attributes.get("clickable", "false").casefold() == "true":
         best_bounds = node.bounds
     ```
   - Lệnh này ép mọi node có `clickable="true"` đều phải giữ nguyên `best_bounds = node.bounds`.
3. **Hậu quả trên TikTok 46.7.3 (Toàn bộ dàn máy chuẩn farm như Máy 8, Máy 61...):**
   - Hàng tài khoản là `com.ss.android.ugc.trill:id/lkp` (`clickable="true"`, bounds full-width `[0, 600][1080, 816]`).
   - Do có `clickable="true"`, đoạn code trên bỏ qua hoàn toàn việc tìm inner `TextView`/avatar (`content-desc="tolmavhj12k"`).
   - `best_bounds.center` bị ép thành `[540, 708]`.
   - Tại tọa độ `x = 540`, cú chạm rơi vào **vùng khoảng trống chết (dead whitespace)** bên phải tên tài khoản (trong khi tên tài khoản và avatar nằm ở dải $x \approx 150 \dots 350$).
   - TikTok 46.7.3 bỏ qua touch event vào khoảng trống chết này, khiến việc đổi nick không bao giờ diễn ra!

---

## 3. Quy tắc kiến trúc & Giải pháp chuẩn (Architectural Rule & Standard Fix)

### A. Cấm tuyệt đối ép tap tâm container full-width (`x = 540`)
Khi container là full-width ($width \ge 600\text{px}$ như $x=0 \dots 1080$), tuyệt đối không được tap vào tâm $x=540$ vì hầu hết các layout danh sách của TikTok đều để trống nửa phải hoặc chứa badge/khoảng trắng không kích hoạt switch.

### B. Ưu tiên tìm Inner Node Username/Avatar & Fallback Clamp Nửa Trái
1. **Bước 1 (Inner Node Target):** Duyệt qua `_nodes(xml_text)` tìm node con có `content-desc` hoặc `text` khớp với `expected_account` nằm trong phạm vi chiều cao của container. Nếu tìm thấy, dùng trực tiếp `inner.bounds` (hoặc `inner.center` tại $x \approx 200 \dots 400$).
2. **Bước 2 (Left-Align Clamp Fallback):** Nếu không tìm thấy inner node cụ thể, bắt buộc clamp biên phải về nửa trái của màn hình (`min(node.bounds[0] + 500, max_r)`):
   ```python
   best_bounds = (node.bounds[0], y1, min(node.bounds[0] + 500, max_r), y2)
   ```
   Điều này đảm bảo tọa độ tâm tap luôn nằm ở $x \approx 250$, trúng vùng avatar hoặc chữ của tài khoản thay vì rơi vào dead whitespace $x=540$.

---

## 4. Bảng đối chiếu nhanh 2 phiên bản TikTok Account Switcher

| Tiêu chí | TikTok Cũ (46.2.3 - Máy 79, 78) | TikTok Chuẩn Farm (46.7.3 - Máy 8, Máy 61...) |
| :--- | :--- | :--- |
| **Resource ID hàng** | `com.ss.android.ugc.trill:id/l9b` | `com.ss.android.ugc.trill:id/lkp` |
| **Widget Class** | `android.widget.Button` | `android.view.ViewGroup` / `LinearLayout` |
| **Hành vi tap `x = 540`** | Không ăn (do layout lệch) | **Bị bỏ qua hoàn toàn (Dead whitespace tap)** |
| **Hành vi tap inner TextView** | Nuốt event nếu child `clickable="false"` trên Button cũ | **Ăn click 100% (lan truyền event lên container cha)** |
| **Giải pháp triệt để** | Đồng bộ APK lên `46.7.3` (`D:/OneDrive/apk-bank/com_ss_android_ugc_trill`) | Giữ tìm inner bounds + clamp nửa trái $x \le 500$ |
