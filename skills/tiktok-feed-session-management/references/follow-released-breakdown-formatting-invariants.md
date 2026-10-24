# Quy Chuẩn Định Dạng Thống Kê Máy Nhả Follow (Follow Released Tier Breakdown)

## 1. Vấn Đề (User Feedback)
Trong báo cáo watchdog follow chéo (`format_released_follows` trong `scripts/watchdog/formatters.py` thuộc repo `tiktok-luot nuoi acc`), khi phân loại danh sách máy bị TikTok nhả follow theo từng tầng:
- Cấp cha có thống kê tổng số máy: `+ Nhả follow (25 máy | 100.0%):`
- Nhưng ở các tầng con (sub-tiers), đặc biệt là **Nhả liền (0 lượt)**, định dạng cũ bị khuyết số lượng máy:
  ```text
  - Nhả liền (0 lượt | 92.0%): (M3, M4, M9, M16, M31, M36, M37, M39, M44, M46, M47, M48, M52, M55, M57, M60, M61, M62, M65, M68, M71, M72, M77)
  - Nhả ở Hồi phục 1 (1 - 4 lượt | 4.0%): (M1: 2 lượt)
  - Nhả ở Cấp Khỏe (10+ lượt | 4.0%): (M18: 12 lượt)
  ```
- **Hệ quả:** Người vận hành nhìn vào danh sách dài dằng dặc 20-30 máy ở nhóm "Nhả liền" nhưng không biết chính xác có bao nhiêu máy bị dính nếu không đếm thủ công từng chữ `M`.

## 2. Invariant Định Dạng Bắt Buộc (Format Contract)
Mọi tầng con trong phân loại Nhả Follow BẮT BUỘC phải có tiền tố thống kê số máy `{len(sub_list)} máy`:

```text
  - Nhả liền ({len(rel_0)} máy | 0 lượt | {pct:.1f}%): ({', '.join(_format_m(m) for m in rel_0)})
  - Nhả ở Hồi phục 1 ({len(rel_1_4)} máy | 1 - 4 lượt | {pct:.1f}%): ({', '.join(_format_m(m, c) for m, c in rel_1_4)})
  - Nhả ở Hồi phục 2 ({len(rel_5_9)} máy | 5 - 9 lượt | {pct:.1f}%): ({', '.join(_format_m(m, c) for m, c in rel_5_9)})
  - Nhả ở Cấp Khỏe ({len(rel_10_plus)} máy | 10+ lượt | {pct:.1f}%): ({', '.join(_format_m(m, c) for m, c in rel_10_plus)})
```

## 3. Ví Dụ Chuẩn Đầu Ra (Expected Telemetry)
```text
• Follow chéo (14 lượt follow) [Module 2 (Anchor): 14 | Module 1 (Bù): 0]:
  + Thành công (0 máy | 0.0%): Không có
  + Nhả follow (25 máy | 100.0%):
    - Nhả liền (23 máy | 0 lượt | 92.0%): (M3, M4, M9, M16, M31, M36, M37, M39, M44, M46, M47, M48, M52, M55, M57, M60, M61, M62, M65, M68, M71, M72, M77)
    - Nhả ở Hồi phục 1 (1 máy | 1 - 4 lượt | 4.0%): (M1: 2 lượt)
    - Nhả ở Cấp Khỏe (1 máy | 10+ lượt | 4.0%): (M18: 12 lượt)
```

## 4. Phạm Vi & Hậu Kiểm Test
- File triển khai: `tiktok-luot nuoi acc/scripts/watchdog/formatters.py` (hàm `format_released_follows`).
- Test đối soát: `tiktok-luot nuoi acc/tests/test_feed_session_watchdog.py` (hàm `test_format_released_follows_with_count`).
- Bắt buộc cập nhật cả assertions trong test suite để bảo đảm Closeout Gate pass 100%.
