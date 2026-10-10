# Báo Cáo Follow: Quy Chuẩn Ngắn Gọn Khóa IP & Hiển Thị Máy Nhả Có Lượt Thành Công

## 1. Bối cảnh & Yêu cầu của User
Khi nhận báo cáo follow (`feed_session_watchdog.py`), người vận hành cần nắm bắt tức thì tình trạng hiện trường mà không bị hoa mắt bởi danh sách dài dòng hoặc gây hiểu lầm về số liệu:
1. **Khóa IP (Circuit Breaker):** Tuyệt đối không liệt kê lê thê từng cổng proxy và timestamp từng máy (dễ làm tràn 4.000 ký tự Telegram). Chỉ cần ghi số lượng proxy đã khóa kèm danh sách các máy partner được khóa cứu an toàn trong ngoặc.
2. **Máy dính nhả (`FOLLOW_FAILED`) nhưng đã follow thành công một số lượt trước đó:** Cần ghi rõ số lượt đã bấm thành công ngay cạnh tên máy, tránh để `(M1)` hay `(M18)` làm user tưởng máy đó bị nhả liền 0 lượt.

---

## 2. Quy chuẩn Format Báo cáo Telegram

### A. Chuẩn hiển thị Cầu dao tự ngắt IP (Đúng 1 dòng gọn gàng):
```text
⚡ Cầu dao tự ngắt IP (<N> proxy đã khóa): Khóa cứu <M> máy (M78, M75, M8)
```
*(Trường hợp không có máy partner nào cần khóa cứu thì chỉ ghi gọn: `⚡ Cầu dao tự ngắt IP (<N> proxy đã khóa)`)*.

### B. Chuẩn hiển thị Máy Nhả follow:
- **Nhả liền (0 lượt):** Chỉ liệt kê tên máy `(M3, M4, M9...)` vì 100% đều là 0 lượt.
- **Nhả ở các nấc Hồi phục / Cấp Khỏe (>= 1 lượt):** Bắt buộc in kèm số lượt follow thành công thực tế dạng `(M1: 2 lượt)`, `(M18: 12 lượt)`.

### Mẫu toàn phần trong báo cáo ca follow:
```text
• Follow chéo (14 lượt follow) [Module 2 (Anchor): 14 | Module 1 (Bù): 0]:
  + Thành công (0 máy | 0.0%): Không có
  + Nhả follow (25 máy | 100.0%):
    - Nhả liền (0 lượt | 92.0%): (M3, M4, M9, M16, M31, M36, M37, M39, M44, M46, M47, M48, M52, M55, M57, M60, M61, M62, M65, M68, M71, M72, M77)
    - Nhả ở Hồi phục 1 (1 - 4 lượt | 4.0%): (M1: 2 lượt)
    - Nhả ở Cấp Khỏe (10+ lượt | 4.0%): (M18: 12 lượt)
  ⚡ Cầu dao tự ngắt IP (22 proxy đã khóa): Khóa cứu 3 máy (M78, M75, M8)
  + Lỗi script/xác minh (0): Không có
  + Bỏ qua (51): Đang dưỡng sinh (23); Khóa IP do máy cùng IP nhả (3: M8, M75, M78); Chưa đủ điều kiện (2)
```

---

## 3. Bản chất Số liệu "Success = 0 máy" dù có lượt follow
- Khi TikTok quét và nhả follow, nếu nick bị dính cờ `follow_failed = True` ở lượt cuối thì hệ thống phân loại nick đó vào nhóm `Nhả follow`.
- Mục `Thành công (X máy)` chỉ tính các máy hoàn thành trọn vẹn phiên **mà không dính cờ nhả**.
- Việc hiển thị `M1: 2 lượt`, `M18: 12 lượt` giúp giải thích rõ ràng tại sao tổng số lượt của phiên là 14 lượt mà số máy thành công trọn vẹn lại là 0 máy.
