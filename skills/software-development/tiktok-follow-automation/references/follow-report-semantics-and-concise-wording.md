# Follow report semantics and concise operator wording

## Trigger
Use when a follow-session report shows `Success (0)` and the operator asks whether any machine actually ran, was released, or caused an IP lock.

## Interpretation
`Success (0 máy)` means zero completed successful cross-follows without release. It does **not** prove zero attempts or zero follows executed:
- `Follow chéo (X lượt follow)`: Tổng số lượt follow tích lũy được trong phiên (ví dụ 14 lượt).
- `Thành công (0 máy)`: Không có máy nào hoàn tất phiên mà giữ sạch cờ — mọi máy đều dứt điểm bằng `FOLLOW_FAILED` (bị nhả ở lượt cuối).
- `Nhả follow` / `Nhả liền`: Machines that attempted and were released before a successful count was recorded, hoặc follow được một số lượt (ví dụ M1 được 2 lượt, M18 được 12 lượt) rồi bị nhả ở lượt kế tiếp và rơi vào diện `Nhả follow`.
- `Bỏ qua`: Safe skips such as cooldown, organic rest, eligibility, or circuit-breaker protection (`Khóa IP do máy cùng IP nhả`).
- `Khóa IP`: Proxy/IP circuit-breaker events and protected machines.

Do not collapse attempted, successful, released, skipped, and protected into one number. If the report lacks an explicit attempt count, say that the attempt count is not directly shown rather than inventing it.

## Compact Telegram Circuit Breaker Formatting (User Correction)
Khi nhiều proxy bị ngắt cầu dao (20–40 proxy), TUYỆT ĐỐI KHÔNG in từng dòng riêng lẻ cho mỗi proxy làm tràn giới hạn 4096 ký tự của Telegram và trôi màn hình. BẮT BUỘC gom nhóm ngắn gọn:
```text
  ⚡ Cầu dao tự ngắt IP (X proxy đã khóa do dính nhả):
    - Khóa cứu partner (Y máy): M<A> (cổng <port1>), M<B> (cổng <port2>)
    - Khóa toàn bộ nick cùng IP (Z proxy): <port3>, <port4>, <port5>, ...
```
- Dòng 1: Danh sách các máy partner được khóa cứu an toàn kèm cổng proxy (high-signal).
- Dòng 2: Gom các cổng proxy còn lại trên 1 dòng liệt kê số cổng ngắn gọn.

## Compact wording
Preferred shorthand: `Nhả → khóa IP`.

When a little more context is needed:
```text
Follow chéo: 0 lượt thành công
Nhả liền: X máy, 0 lượt thành công
Khóa IP: Y IP
```

## Answer style
Answer the operator's direct question first, in Vietnamese, with no speculative theory. Explain only the distinction needed to prevent the common misread that `Success (0)` equals “no machine ran.”
