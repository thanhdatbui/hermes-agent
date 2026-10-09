# Giới Hạn Phiên Lướt Feed Mỗi Ca & Ranh Giới Phần Cứng Phone Farm

> **QUAN TRỌNG — Cập nhật 2026-10-07:**
> Thực tế farm KHÔNG chạy 8 nick tuần tự trên 1 máy trong 1 ca. 160 máy chạy SONG SONG hoàn toàn độc lập. Mỗi ngày mỗi máy chỉ chạy **4 nick** (luân phiên Chẵn/Lẻ), không phải 8. Rule cũ "CẤM tăng quá 1 phiên/nick/ca" được sửa lại thành "2 phiên/nick/ca là Sweet Spot đã verify — không nên tăng lên 3."

---

## 1. Cấu Trúc Thực Tế Farm (Chẵn/Lẻ + 4 Ca × 2 Phiên)

```
_SCHEDULE trong tiktok_runner.py:
  Ngày LẺ: Row 1, 3, 5, 7  → mỗi row chạy 1 ca riêng biệt
  Ngày CHẴN: Row 2, 4, 6, 8 → mỗi row chạy 1 ca riêng biệt

CẤU TRÚC ĐÃ DEPLOY (4 Ca × 2 Phiên/ngày):
  Ca 1 (Sáng):  Phiên 1  06:00 (Feed only) + Phiên 2  08:00 (Feed + Upload)
  Ca 2 (Trưa):  Phiên 1  12:00            + Phiên 2  14:00
  Ca 3 (Tối):   Phiên 1  18:00            + Phiên 2  20:00
  Ca 4 (Đêm):   Phiên 1  00:00            + Phiên 2  01:30
```

Nghĩa là **1 nick bản chất ĐÃ CHẠY 2 PHIÊN TRONG MỖI CA** (Phiên 1 + Phiên 2 cách nhau 1.5–2 tiếng). Đây là cấu trúc HIỆN HÀNH đã deploy và đang chạy production.

---

## 2. Tải Thực Tế 1 Máy S7 / Ngày

| Thông số | Giá trị thực tế |
|:---|:---|
| Nick chạy / ngày | 4 nick (Chẵn/Lẻ) |
| Phiên / nick / ngày | 2 phiên (Phiên 1 + Phiên 2 trong cùng Ca) |
| Tổng phiên / máy / ngày | 4 × 2 = **8 phiên** |
| Thời lượng / phiên | ~7–8 phút |
| Tổng Screen-On Time / ngày | 8 × 8 phút ≈ **~64 phút** (~1.1 tiếng) |
| Machine idle time / 24h | **~22.9 tiếng** |

S7 chạy ở mức 27% công suất ca — cực kỳ nhẹ, không có bất kỳ rủi ro nhiệt hay pin.

---

## 3. Đánh Giá Tăng Lên 3 Phiên / Nick / Ca

### 3A. Về mặt phần cứng & thời gian
Nếu tăng lên 3 phiên/nick/ca:
- Tổng phiên/máy/ngày: 4 × 3 = 12 phiên
- Screen-On Time: ~96 phút/ngày (~1.6 tiếng)
- Vẫn ở mức nhẹ về phần cứng — S7 dư sức.
- **Vấn đề thực sự: khoảng cách giữa các phiên** bị rút ngắn nguy hiểm.

### 3B. Constraint thật từ Watchdog Grace Period
Cấu trúc hiện tại: Ca 1 từ 06:00 đến 08:00 (2 tiếng).
Nếu nhồi Phiên 3 vào giữa (ví dụ 07:00):

```
06:00 → Phiên 1 (7-8p) → Xong ~06:08
07:00 → Phiên 3 (7-8p) → Xong ~07:08  ← GAP chỉ 52 phút!
08:00 → Phiên 2 (7-8p + Upload) → Xong ~08:15
```

- Watchdog `feed_session_watchdog.py` có Grace Period ~20 phút.
- Khoảng cách giữa các phiên chỉ còn **~52 phút** → nguy cơ watchdog ép chốt phiên Phiên 3 trước khi Phiên 2 kết thúc → **False Alarm báo lỗi hàng loạt** (đã xảy ra tương tự Case Ca 4 - 22 máy ngày 15/09).

### 3C. Về mặt thuật toán TikTok (Anti-Bot Fingerprint)
Người dùng thật trung bình mở TikTok **8–12 lần/ngày**, mỗi lần 3–10 phút.
- 1 nick / ngày (trong ngày chạy): hiện 2 phiên (~16 phút) → **Hành vi thấp tự nhiên (Low-Active User)**.
- Tăng lên 3 phiên (~24 phút/ngày): Biên giới giữa "người ít dùng TikTok" và "người dùng bình thường" — không có gì nguy hiểm về thuật toán nếu gap đủ lớn.
- **Rủi ro thực sự:** Nếu 3 phiên cách nhau đều đặn cứ 40–50 phút trong 2 tiếng Ca → machine-periodic fingerprint rõ ràng. Người thật không mở app đều đặn như đồng hồ.

### 3D. KẾT LUẬN: KHÔNG NÊN TĂNG LÊN 3 PHIÊN
- **Lý do chính:** Constraint Watchdog Grace Period & window gap — không còn đủ buffer an toàn trong Ca 2 tiếng.
- **Lý do phụ:** 2 phiên/ca (Sweet Spot hiện tại) đã đạt chuẩn hành vi người dùng tự nhiên.
- **Khác với hiểu nhầm cũ:** Không phải vì máy S7 không chịu nổi hay phần cứng quá tải — máy dư sức. Lý do là toán học lịch Watchdog và fingerprint thuật toán.

---

## 4. Quy Tắc Bất Biến Đúng (Cập Nhật)

| Thông số | Giá trị chuẩn |
|:---|:---|
| Phiên / nick / ca | **2 phiên** (Phiên 1 + Phiên 2 cách nhau 1.5–2h) |
| Tổng phiên / máy / ngày | **8 phiên** (4 nick × 2 phiên) |
| Screen-On Time / ngày | **~64 phút** (far below S7 thermal limit) |
| Gap giữa Phiên 1 và Phiên 2 | **1.5–2 tiếng** — KHÔNG được rút ngắn |
| Nick / máy / ngày | **4 nick** (Chẵn/Lẻ alternating) |
| Tần suất nick hoạt động | **1 ngày chạy, 1 ngày nghỉ** (Chẵn/Lẻ) → mỗi nick nghỉ ~32 giờ liên tục |

---

## 5. Jitter Layer Kiểm Chứng (Verify 2026-10-07)

### Tầng 1 — Cron Gate (tiktok_runner.py)
- Cron: `*/15 * * * *`
- `_determine_row()` match cứng các slot giờ chẵn
- **Status: OK** — gate chuẩn, không cần đổi

### Tầng 2 — Session Start Jitter (run-feed-session.ps1 dòng 421–430)
```powershell
$SessionJitterMinSeconds = 60   # 1 phút tối thiểu
$SessionJitterMaxSeconds = 180  # 3 phút tối đa
$sessionJitterSec = Get-Random -Minimum 60 -Maximum 181
Start-Sleep -Seconds $sessionJitterSec
```
- Mỗi Ca bắt đầu, PowerShell ngủ ngẫu nhiên 1–3 phút TRƯỚC khi chạm vào thiết bị đầu tiên
- Phá vỡ chữ ký giờ tròn `:00` một cách tự nhiên
- **KHÔNG TĂNG lên 3–5 phút** vì: Ca 4 (00:00 → 01:30) chỉ có 90 phút, Watchdog grace period 20 phút → chỉ còn 5–10 phút buffer nếu jitter 5 phút → nguy cơ False Alarm
- **Status: OPTIMAL — KHÔNG CẦN SỬA**

### Tầng 3 — Machine Order & Stagger (run-feed-session.ps1 & multi_machine_feed_session.py)
- `-RandomizeMachineOrder`: Xáo trộn thứ tự 160 máy ngẫu nhiên mỗi lần chạy
- `-MachineStartStaggerMs "2000,8000"`: Mỗi máy spawn cách máy trước 2–8s ngẫu nhiên
- Mặc định trong multi_machine: `(4000, 10000)` ms nếu không truyền tham số
- **Status: OPTIMAL — KHÔNG CẦN SỬA**

**Tổng kết Jitter Audit 2026-10-07: Cả 3 tầng ĐẠT CHUẨN, không cần chỉnh sửa bất kỳ dòng code nào.**

---

## 6. Giải Pháp Đúng Cho Bài Toán Nhả Follow & 200-View Limbo

Tăng phiên feed KHÔNG giải quyết được nhả follow hay 200-view limbo. Giải pháp thực sự:

1. **Xây Inbound Trust (Internal Mutual Seed):** Chia 1.280 nick thành cụm, cho follow chéo mồi nội bộ (~540 follow để xây nền tảng trust trước khi đi follow ngoài).
2. **Tối ưu Hook 3s video:** Video 15–25s, visual gái xinh/Douyin, nhạc trending — đây mới là yếu tố quyết định cắn đề xuất.
3. **Watch Time Gate đúng chuẩn:** Ngâm 8–12s trước khi thả tim hoặc follow tự nhiên.
4. **Không follow khi acc chưa có Inbound Trust:** Nick chưa có ~200 follower nội bộ đi follow người lạ bên ngoài → TikTok silent-drop ngay (Outbound-only pattern = bot flag).

---

## 7. Anti-Pattern: Lỗi Tư Duy Cũ (CẤM ĐỂ LỌT Lần Sau)

| Lỗi tư duy | Thực tế đúng |
|:---|:---|
| "1 máy chạy 8 nick tuần tự 1 ca" | 160 máy SONG SONG, mỗi máy chỉ chạy 4 nick/ngày theo Chẵn/Lẻ |
| "Tăng phiên feed thì bị quá tải S7" | S7 đang chỉ dùng 27% công suất — không phải vấn đề phần cứng |
| "CẤM tăng quá 1 phiên/ca" | Hiện tại ĐÃ chạy 2 phiên/ca và hoạt động tốt — sweet spot |
| "Jitter in-app cần tăng để an toàn hơn" | Cả 3 tầng jitter đã optimal, tăng thêm chỉ gây cấn Watchdog |
