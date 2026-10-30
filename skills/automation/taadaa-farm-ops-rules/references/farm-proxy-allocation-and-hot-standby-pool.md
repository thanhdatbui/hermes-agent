# Quy Hoạch Hạ Tầng Proxy Toàn Farm (MobiProxy, R3G Thái Bình, MikroTik PPPoE)

## 1. Tổng Quan Quy Hoạch Toàn Farm (160 Máy S7)
Hệ thống vận hành song song 3 cụm hạ tầng Proxy FTTH/4G sạch, đảm bảo tỷ lệ chuẩn vàng **1 Proxy : 2 Máy**:
- **Cụm 1: MobiProxy (`test.taadaa.click:5101..5138`)**
  - Gồm 32 proxy có user/pass (`mobi1..mobi38`).
  - Gánh 64 máy Kibe (`M1..M32` và `M39..M70`).
- **Cụm 2: R3G Thái Bình (`tb.taadaa.click:5141..5158`)**
  - Gồm 16 proxy FTTH Viettel Thái Bình qua Xiaomi R3G (Tailscale `100.115.94.49`).
  - Line 1 (`tamnhb1`): 8 port `5141..5148`.
  - Line 0 (`tamnhb0`): 8 port `5151..5158`.
  - Gánh 32 máy non/yếu Farm Admin (`M203, M204, M208, M211, M213... M272`).
- **Cụm 3: MikroTik PPPoE Đà Nẵng (`192.168.110.2`)**
  - Tổng số session PPPoE chạy thực tế: **35 IP Public Viettel Đà Nẵng** (`10001`..`10035`).
  - Trần cứng hạ tầng: Bắt đầu từ port thứ 36 (`pppoe-out36`) trở đi, BRAS Viettel tự động đá vào CGNAT nội bộ `172.22.x.x` (timeout, không ra được internet). Duy trì bật đúng 35 session `pppoe-out1..pppoe-out35`.
  - Cổng `10001..10007`: Dành riêng mạng phụ trợ / tool.
  - Cổng `10008..10027` & `10032..10035` (24 port): Gánh 48 máy kênh chính Farm Admin (tỷ lệ 1:2).

## 2. Dải 4 IP Dự Phòng Nóng Trên MikroTik (Hot Standby)
Bao gồm 4 cổng PPPoE nhận IP Public sạch:
- **`192.168.110.2:10028`** (`pppoe-out28`)
- **`192.168.110.2:10029`** (`pppoe-out29`)
- **`192.168.110.2:10030`** (`pppoe-out30`)
- **`192.168.110.2:10031`** (`pppoe-out31`)

### Mục Đích & Nguyên Tắc Vận Hành:
1. **Dự phòng nóng (Hot Standby Swap):** Khi bất kỳ line PPPoE nào trong 24 line đang gánh máy chính bị chập chờn hoặc cần quay đổi IP gấp, điều phối swap máy sang 4 port này tức thì mà không làm gián đoạn máy khác.
2. **Cấp phát linh hoạt (Ad-hoc / Testing):** Dùng để test script mới, nuôi profile Hotmail/Gmail trên GPM cần IP sạch cố định, hoặc cắm thêm máy lẻ thử nghiệm.
3. **Cấm dồn máy ngoài quy hoạch:** Không tự ý gán máy vĩnh viễn vào 4 port này nếu chưa có kế hoạch mở rộng dàn máy.
