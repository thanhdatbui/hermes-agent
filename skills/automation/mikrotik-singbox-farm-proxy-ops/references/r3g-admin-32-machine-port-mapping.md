# Mapping Chi Tiết 32 Máy S7 Admin Sang 16 Port Xiaomi R3G Thái Bình

## 1. Bản Đồ Gán Cổng Sing-box & R3G Direct WAN (Tỷ lệ 1 Proxy : 2 Máy)
Tất cả 32 máy này đều lắng nghe tại port Sing-box `192.168.110.2:(20000 + M)` và được Sing-box chuyển tiếp ra domain `tb.taadaa.click`:

| Port R3G | Upstream Port | OpenWrt PPPoE Interface | Cặp Máy Phụ Trách | Inbound Sing-box Trên MikroTik | Dải IP Viettel Thái Bình Dự Kiến |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **P1** | `tb.taadaa.click:5141` | `WAN2` (Line 1 chính, cổng giữa `lan2`) | M203, M204 | `20203`, `20204` | `117.5.152.175` |
| **P2** | `tb.taadaa.click:5142` | `wan_sub2` (macvlan mvl2) | M208, M211 | `20208`, `20211` | `117.5.153.81` |
| **P3** | `tb.taadaa.click:5143` | `wan_sub3` (macvlan mvl3) | M213, M217 | `20213`, `20217` | `117.5.153.178` |
| **P4** | `tb.taadaa.click:5144` | `wan_sub4` (macvlan mvl4) | M220, M223 | `20220`, `20223` | `117.5.153.107` |
| **P5** | `tb.taadaa.click:5145` | `wan_sub5` (macvlan mvl5) | M227, M230 | `20227`, `20230` | `117.5.152.120` |
| **P6** | `tb.taadaa.click:5146` | `wan_sub6` (macvlan mvl6) | M233, M235 | `20233`, `20235` | `117.5.152.126` |
| **P7** | `tb.taadaa.click:5147` | `wan_sub7` (macvlan mvl7) | M238, M241 | `20238`, `20241` | `117.5.153.180` |
| **P8** | `tb.taadaa.click:5148` | `wan_sub8` (macvlan mvl8) | M243, M246 | `20243`, `20246` | `117.5.153.181` |
| **P9** | `tb.taadaa.click:5151` | `wan` (Line 0 chính, cổng ngoài `lan1`) | M251, M253 | `20251`, `20253` | `117.5.61.229` |
| **P10** | `tb.taadaa.click:5152` | `wan_sub11` (macvlan mvl11) | M255, M260 | `20255`, `20260` | `117.5.62.126` |
| **P11** | `tb.taadaa.click:5153` | `wan_sub12` (macvlan mvl12) | M262, M264 | `20262`, `20264` | `117.5.183.211` |
| **P12** | `tb.taadaa.click:5154` | `wan_sub13` (macvlan mvl13) | M268, M270 | `20268`, `20270` | `116.107.116.183` |
| **P13** | `tb.taadaa.click:5155` | `wan_sub14` (macvlan mvl14) | M261, M263 | `20261`, `20263` | `116.104.210.119` |
| **P14** | `tb.taadaa.click:5156` | `wan_sub15` (macvlan mvl15) | M265, M266 | `20265`, `20266` | `116.104.220.235` |
| **P15** | `tb.taadaa.click:5157` | `wan_sub16` (macvlan mvl16) | M267, M269 | `20267`, `20269` | `116.104.217.152` |
| **P16** | `tb.taadaa.click:5158` | `wan_sub17` (macvlan mvl17) | M271, M272 | `20271`, `20272` | `116.107.112.230` |

---

## 2. Kịch Bản Đối Soát Nhanh Bằng Python
Chạy đoạn code sau để nghiệm thu đối soát kép giữa R3G thật và cổng Singbox trên MikroTik:

```python
import urllib.request, time

mapping = {
    203: 5141, 204: 5141, 208: 5142, 211: 5142,
    213: 5143, 217: 5143, 220: 5144, 223: 5144,
    227: 5145, 230: 5145, 233: 5146, 235: 5146,
    238: 5147, 241: 5147, 243: 5148, 246: 5148,
    251: 5151, 253: 5151, 255: 5152, 260: 5152,
    262: 5153, 264: 5153, 268: 5154, 270: 5154,
    261: 5155, 263: 5155, 265: 5156, 266: 5156,
    267: 5157, 269: 5157, 271: 5158, 272: 5158
}

for m, r3g_p in sorted(mapping.items()):
    sb_p = 20000 + m
    req = urllib.request.Request('http://api.ipify.org')
    h = urllib.request.ProxyHandler({'http': f'http://192.168.110.2:{sb_p}'})
    o = urllib.request.build_opener(h)
    try:
        ip = o.open(req, timeout=3.5).read().decode().strip()
        print(f"M{m} (Port {sb_p}): LIVE -> {ip}")
    except Exception as e:
        print(f"M{m} (Port {sb_p}): FAIL -> {e}")
```
