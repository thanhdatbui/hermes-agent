# Kiến trúc Ca & Timing Feed Session TikTok (Cập nhật 11/09/2026)

## 1. Bản chất thay đổi: Phân biệt kiến trúc CŨ vs HIỆN TẠI

### Kiến trúc cũ (Giai đoạn picker / cohort / manifest, đến 10/09/2026):
- Phân chia theo Ca và đa phiên:
  - Từng chạy 3 ca × 3 phiên/ngày (6 acc/máy).
  - Sau đó chuyển sang 4 ca × 2 phiên/ngày (8 acc/máy).
- Có khái niệm "Phiên 1" (lướt feed + follow) và "Phiên 2" (lướt feed + follow + upload).
- Giữa Phiên 1 và Phiên 2 của cùng 1 nick có khoảng nghỉ ngắn (pair-gap 30-60 phút).
- Hệ thống điều phối phức tạp qua `picker` tạo manifest lúc 6h sáng, `runner` tick 15p nhặt slot chạy rải rác.

### Kiến trúc hiện tại (Migrated 11/09/2026):
- Bỏ hoàn toàn tầng trung gian `picker / manifest / cohort`.
- **Mỗi Ca chỉ có DUY NHẤT 1 đợt chạy (1 run tập trung per Ca)**:
  - `tiktok_runner.py` chạy cron mỗi 15 phút, nhưng chỉ spawn đúng vào đầu 4 mốc giờ: `00:00`, `06:00`, `12:00`, `18:00`.
  - Không còn chia thành 2 phiên rời rạc trong cùng một ca. Toàn bộ máy của Row ca đó vào chạy một lèo: Lướt feed (8-11 video) -> Follow hook -> Upload hook (nếu có lịch) ngay trong phiên đó.
- Khử trùng lặp qua state file `D:/Taadaa/runtime/kibe/cron-state/runner_simple_state.json` với key `<date>T<hour>`.

---

## 2. Bảng phân bổ Row theo Parity ngày (Chẵn / Lẻ)

Để nuôi trọn vẹn 8 account/máy (Row 1 đến Row 8), farm chạy luân phiên 2 ngày một chu kỳ:

| Ca | Giờ bắt đầu | Ngày Lẻ (`date % 2 == 1`) | Ngày Chẵn (`date % 2 == 0`) |
|:---|:---|:---|:---|
| **Ca 1 (Đêm - slot đầu ngày)** | `00:00` | **Row 7** | **Row 8** |
| **Ca 2 (Sáng)** | `06:00` | **Row 1** | **Row 2** |
| **Ca 3 (Trưa)** | `12:00` | **Row 3** | **Row 4** |
| **Ca 4 (Tối)** | `18:00` | **Row 5** | **Row 6** |
| **Dead zone** | `01:00 - 05:00` | Nghỉ hoàn toàn (Clear cache lúc 04:00, 2FA lúc 01:00) | Nghỉ hoàn toàn |

> **Lưu ý**: Ca 06:00 chỉ chạy DUY NHẤT Row 1 (nếu ngày lẻ) HOẶC Row 2 (nếu ngày chẵn), KHÔNG chạy đồng thời cả Row 1 và Row 2.

---

## 3. Thời lượng thực thi & Khoảng cách nghỉ (Timing & Gaps)

- **Thời gian chạy của 1 Ca**: Toàn dàn ~80 máy chạy song song mất khoảng **40 - 50 phút** (tùy số lượng video và thời gian follow).
- **Khoảng cách nghỉ giữa các Ca**:
  - Các mốc Ca cách đều nhau **6 tiếng** (00:00 -> 06:00 -> 12:00 -> 18:00).
  - Sau khi hoàn thành ca (~50 phút), thiết bị được **nghỉ hoàn toàn ~5 tiếng 10 phút** trước khi bước vào Ca kế tiếp.
  - Thời gian nghỉ dài giúp thiết bị hạ nhiệt, pin không bị phồng và không làm nghẽn hạ tầng proxy/ADB.
- **Khoảng cách chu kỳ của 1 tài khoản (Account-level interval)**:
  - Một nick chỉ chạy đúng 1 lần trong ngày được chỉ định.
  - Chu kỳ quay lại của chính nick đó là **48 tiếng (2 ngày)** nhờ cơ chế đảo ngày chẵn/lẻ.
