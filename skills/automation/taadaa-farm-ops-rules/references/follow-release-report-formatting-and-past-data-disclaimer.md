# Quy Chuẩn Format Báo Cáo Phân Nhóm Nhả Follow & Kỷ Luật Dữ Liệu Minh Họa (08/09/2026)

## 1. Nguồn Gốc Phản Hồi Từ Operator (User Frustration Signal)
Trong quá trình vận hành watchdog theo dõi phiên follow nuôi nick:
- Định dạng cũ: `5 - 9 lượt (1): 18 (6 lượt)` gây hiểu nhầm nghiêm trọng vì:
  + `(1)` bị lầm tưởng là 1 lượt follow, thay vì 1 máy.
  + Số `18` đứng cạnh `(6 lượt)` khiến mắt người đọc bị lú giữa số thứ tự máy và số lượt follow.
- Việc trích dẫn số liệu cũ của Row 1 (ngày lẻ) để làm ví dụ minh họa vào đúng ngày chạy Row 2 (ngày chẵn) mà không có nhãn disclaimer khiến operator hốt hoảng tưởng bot đang chạy sai lịch ca hoặc dữ liệu live bị nhầm lẫn.

---

## 2. Quy Chuẩn Bắt Buộc Khi Format Nhóm Nhả Follow

Mọi báo cáo trong `feed_session_watchdog.py`, tin nhắn tổng kết phiên, hoặc báo cáo điều tra thủ công BẮT BUỘC tuân thủ định dạng 4 tầng có nhãn rõ ràng:

```text
  + Nhả follow (N máy):
    - Nhả liền (0 lượt - X máy): M1, M7, M10, ...
    - 1 - 4 lượt (Y máy): M14 (1 lượt), M15 (1 lượt), ...
    - 5 - 9 lượt (Z máy): M4 (7 lượt), M9 (7 lượt), ...
    - 10+ lượt (W máy): M2 (19 lượt), M6 (16 lượt), ...
```

### Các Bất Biến Hiển Thị (Format Invariants):
1. **Số lượng máy BẮT BUỘC có chữ "máy":**
   - Đúng: `(1 máy)`, `(27 máy)`, `(5 máy)`
   - CẤM: `(1)`, `(27)`, `(5)` (dễ bị nhầm với số lượt follow).
2. **Định danh máy BẮT BUỘC có tiền tố "M":**
   - Đúng: `M18 (6 lượt)`, `M4 (7 lượt)`
   - CẤM: `18 (6 lượt)`, `4 (7 lượt)` (dễ gây hiểu lầm giữa số máy và số lượt).
3. **Helper chuẩn hóa trong code (`feed_session_watchdog.py`):**
   ```python
   def _format_m(m: Any) -> str:
       s = str(m).strip()
       if s.upper().startswith("M"):
           return f"M{s[1:]}"
       return f"M{s}"
   ```

---

## 3. Kỷ Luật Nghiêm Ngặt Về Dữ Liệu Minh Họa / Ví Dụ

1. **BẮT BUỘC có nhãn cảnh báo rõ ràng:**
   Khi trích xuất số liệu cũ hoặc dựng khung báo cáo ví dụ cho operator, BẮT BUỘC đặt banner ngay dòng đầu tiên:
   `[DỮ LIỆU MINH HỌA - CA CŨ NGÀY DD/MM (ROW X)]`
2. **CẤM gửi khối báo cáo giống hệt ca thật mà không có disclaimer:**
   Vào ngày Chẵn (Row 2), tuyệt đối không gửi báo cáo ghi "Row 1" mà không giải thích trước, tránh gây hoang mang cho người vận hành.
