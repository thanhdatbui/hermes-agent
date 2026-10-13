# Quy Hoạch Niche Farm: Anti-Clustering Permutation & Đồng Bộ Hashtag Hai Sheet (2026-10-13)

## 1. Bối cảnh & Nguyên tắc vận hành
Khi điều chỉnh hoặc gán niche cho 80 máy (M1..M80 hoặc M201..M280) trên các workbook slot `Tik1.xlsx` .. `Tik8.xlsx`:
- **CẤM TUYỆT ĐỐI gán 1 niche đồng loạt cho nguyên 1 slot:** Ví dụ gán toàn bộ Tik 6 là Story, Tik 7 là Emotion. Khi hệ thống chạy batch theo ca/slot, các máy chạy song song trong cùng 1 phiên sẽ bị dồn cục trùng lặp niche hàng loạt (clustering), dễ bị thuật toán TikTok đánh giá bất thường và bóp phân phối.
- **Yêu cầu của User (Invariant):** Phải phân bổ ngẫu nhiên/xen kẽ trong pool niches, đảm bảo các máy chạy cùng 1 phiên không bị giống niche.

---

## 2. Thuật toán phân bổ xen kẽ đa chiều (Anti-Clustering Permutation)

Để bảo đảm tính tất định (deterministic) và không tạo trùng lặp ngẫu nhiên như `random.choice()`, dùng bước nhảy nguyên tố cùng nhau với kích thước pool ($N = 12$ niches):

```python
# m_idx: chỉ số máy 0..79 (tương ứng hàng 2..81 trong sheet TaiKhoan)
# slot: số thứ tự slot (ví dụ slot 6, 7, 8)
# STAGE_NICHES: danh sách 12 cụm niche hybrid
stride = 5   # gcd(5, 12) == 1
offset = (slot - base_slot) * 4
niche_idx = (m_idx * stride + offset) % len(STAGE_NICHES)
slug, label, hashtags = STAGE_NICHES[niche_idx]
```

### Tiêu chuẩn nghiệm thu cứng (3 tiêu chí):
1. **Adjacent Duplicates = 0:** Hai máy liền kề nhau ($M_i$ và $M_{i+1}$) trong cùng 1 slot tuyệt đối không cùng niche.
2. **Cross-Slot Overlap = 0:** Trên cùng 1 máy, giữa các slot liền kề (Tik 6, Tik 7, Tik 8) mang các niche hoàn toàn khác nhau (không trùng lặp chéo slot).
3. **Uniform Distribution:** Mỗi niche trong danh sách 12 niches được rải đều chính xác cho 6 đến 7 máy trên tổng số 80 máy mỗi slot.

---

## 3. Danh sách 12 Niche Hybrid (Story Engine + Core Visual)
Dữ liệu thực nghiệm farm tháng 10/2026 (`chungan981` 19.7k tim, `tuantuannguyen56` 4.9k tim) chứng minh nội dung Storytelling và Curiosity có retention và comment vượt trội so với visual đơn thuần. Danh sách 12 niche chuẩn hóa gồm:

1. `cauchuyen`: "Câu chuyện" (Hook tò mò, kịch bản dẫn dắt, giải quyết mâu thuẫn)
2. `thuvi`: "Thú vị" (Fact bất ngờ, kiến thức kỳ lạ, "bạn có biết")
3. `cuocsong`: "Cuộc sống" (Đời thường, trải nghiệm, góc nhìn tích cực)
4. `hocsinh`: "Học sinh" (Kỷ niệm học đường, tuổi trẻ)
5. `thucung`: "Thú cưng cute"
6. `cuoi`: "Tiểu phẩm hài hước"
7. `douyin_beauty`: "Douyin Biến hình"
8. `amthuc`: "Món ngon đường phố"
9. `satisfying`: "Mẹo vặt & Satisfying"
10. `kienthuc_viral`: "Sự thật bất ngờ"
11. `dulich`: "Cảnh đẹp du lịch"
12. `gym_fit`: "Fitness & Vóc dáng"

---

## 4. Kỷ luật đồng bộ hai sheet trong file Tik (`TaiKhoan` & `Hashtag theo Folder`)

Khi cập nhật Niche & Hashtag trên bất kỳ file `Tik*.xlsx` nào, **BẮT BUỘC PHẢI ĐỒNG BỘ CẢ 2 SHEET**:
- **Sheet `TaiKhoan`:**
  - Cột E (col 5): `video gốc` (`src_id`)
  - Cột F (col 6): `Keyword Video` (`label`)
  - Cột G (col 7): `Hashtag Pool` (`hashtags`)
- **Sheet `Hashtag theo Folder`:**
  - Cột A (col 1): `Folder Nguồn` (BẮT BUỘC gán bằng `src_id` của sheet TaiKhoan)
  - Cột B (col 2): `Folder Video` (BẮT BUỘC gán bằng `out_id` của sheet TaiKhoan)
  - Cột C (col 3): `Keyword/Niche` (`label`)
  - Cột D (col 4): `Hashtag Pool` (`hashtags`)

### Bẫy phổ biến (Pitfall):
Nếu chỉ cập nhật Cột C & D trong `Hashtag theo Folder` mà quên ghi đè Cột A (`Folder Nguồn`), các file copy template cũ (như Tik7, Tik8 copy từ Tik6) sẽ giữ nguyên Folder Nguồn là `401..480` thay vì `481..560` hay `561..640`. Dẫn đến pipeline render/download đọc nhầm folder mapping. Luôn kiểm tra đối soát `Mismatch TaiKhoan vs Hashtag theo Folder == 0`.
