# Quy Tắc Phân Bổ Niche Đa Máy & Đa Slot (Chống Trùng Ngách Hàng Loạt Theo Ca)

## 1. Bối Cảnh & Nguyên Tắc Sống Còn (User Directive)
- **CẤM TUYỆT ĐỐI** gán 1 niche duy nhất cho toàn bộ 1 file Tik (80 máy).
- **Lý do thuật toán**: Khi farm vận hành theo ca, 80 máy cùng chạy 1 slot (ví dụ Tik 6) tại cùng một thời điểm. Nếu cả 80 máy đồng loạt đăng hoặc tương tác cùng 1 chủ đề, hệ thống kiểm duyệt TikTok sẽ phát hiện cụm thiết bị bất thường (cùng dải IP/AP, cùng thời gian, cùng chủ đề), dẫn tới bóp tương tác hoặc shadowban hàng loạt.
- **Quy chuẩn bắt buộc**: Phân bổ ngẫu nhiên có kiểm soát (Balanced Pseudo-Random) qua toàn bộ 12 Niche Hot được phê duyệt.

## 2. 4 Tiêu Chuẩn Phân Bổ Bắt Buộc (Distribution Invariants)

1. **Cân bằng trong từng Slot (Balanced per Slot)**:
   - 80 máy trong cùng 1 file Tik phải được chia đều cho $N$ ngách.
   - Với $N=12$, mỗi ngách xuất hiện 6–7 máy ($12 \times 6 + 8 = 80$).
2. **Khử trùng máy liền kề (Anti-neighbor Collision)**:
   - Hai máy vật lý liên tiếp ($M$ và $M+1$) không bao giờ nhận cùng một ngách trong cùng một slot.
3. **Triệt tiêu va chạm giữa các Slot của cùng một máy (Zero Collision per Device across Shifts)**:
   - Một thiết bị vật lý $M$ khi chạy xoay ca qua các slot khác nhau (ví dụ Slot 6, 7, 8) **bắt buộc** phải nhận 3 ngách khác nhau.
   - **Công thức bước nhảy modulo**:
     ```python
     # N = 12 ngách
     # slot_offset: với N=12, chọn step = 4 (các offset: 0, 4, 8)
     niche_idx = (m - base_m + (slot - start_slot) * 4) % N
     ```
     Với công thức này, trên cùng một máy $M$, 3 slot $\{6, 7, 8\}$ sẽ có chỉ số ngách $\{i, (i+4)\%12, (i+8)\%12\}$ là 3 tập rời rạc hoàn toàn $\rightarrow$ **Tỷ lệ trùng ngách trên cùng máy = 0/80**.
4. **Bảo toàn tài nguyên đã render (Chỉ áp dụng slot trống)**:
   - Các slot đã có video render (ví dụ Tik 1–5 đã render >11.5k video): **GIỮ NGUYÊN 100%**, cấm purge hoặc ghi đè làm mất công sức render.
   - Chỉ áp dụng phân bổ Niche mới cho các slot chưa render video (ví dụ Tik 6–8, 0% clip).

## 3. Template Code Chuẩn Hóa
```python
def generate_balanced_random_assignments(machines, slots, niches):
    N = len(niches)
    assignments = {m: {} for m in machines}
    for slot_idx, slot in enumerate(slots):
        offset = slot_idx * 4  # step 4 đảm bảo gcd(4, 12) = 4, chu kỳ 3 slot không trùng
        for i, m in enumerate(machines):
            assignments[m][slot] = niches[(i + offset) % N]
    return assignments
```
