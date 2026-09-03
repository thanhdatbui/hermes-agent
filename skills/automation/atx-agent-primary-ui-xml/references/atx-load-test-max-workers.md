# Sizing max_workers bằng load test ATX thật (2026-08-16, farm 80 máy kibe)

## Vấn đề
Khi tăng số máy chạy song song (feed session multi-machine), cần biết max_workers an toàn.
Đoán sai → quá tải ADB/ATX (lỗi rải rác) hoặc quá thận trọng (chạy chậm).
User yêu cầu test ĐÚNG công cụ thật + workload thật, không phải ping nhẹ.

## Method: 3 bậc test, bậc sau sát thực tế hơn

### Bậc 1 — Ping ADB nhẹ (KHÔNG đủ, chỉ sanity)
```python
subprocess.run([ADB, '-s', d, 'shell', 'echo', 'ok'], timeout=10)
```
80 máy: 5/10/20/40 song song đều 0 lỗi 0.1-0.2s → KHÔNG phân biệt được cap. Bỏ qua.

### Bậc 2 — ATX API thật (port 7912, `POST /uiautomator`)
```python
subprocess.run([ADB, '-s', dev, 'forward', 'tcp:7912', 'tcp:7912'], capture_output=True)
req = urllib.request.Request('http://127.0.0.1:7912/uiautomator', data=b'{}',
                             headers={'Content-Type': 'application/json'}, method='POST')
```
- Kết quả 80 máy: 20 song song 0 lỗi; 30: 1 lỗi; 40: 1; 60: 3; 80: 6
- **PITFALL: `adb forward tcp:7912 tcp:7912` dùng CHUNG local port 7912** — 2 máy forward cùng lúc có thể đụng (10 máy test lần đầu fail 3). Code thật dùng port riêng mỗi máy (9008 trong capture_recovery) nên không ảnh hưởng thực tế — nhưng test phải biết.

### Bậc 3 — Mô phỏng phiên thật (QUYẾT ĐỊNH)
Mỗi worker = mở TikTok + chờ load + N lần (đọc UI + swipe), giống feed session thật:
```python
subprocess.run([ADB, '-s', dev, 'shell', 'am', 'start',
                '-n', 'com.ss.android.ugc.aweme/.main.MainActivity'], capture_output=True, timeout=15)
time.sleep(8)  # S7 load LÂU — đừng dùng 2-3s
for i in range(15):
    atx_call(dev)  # POST /uiautomator
    subprocess.run([ADB, '-s', dev, 'shell', 'input', 'swipe',
                    '540', '1500', '540', '400', '200'], capture_output=True, timeout=10)
    time.sleep(0.5)
```
- Kết quả 80 máy: 20 → 0 lỗi; 30 → 0 lỗi; 40 → 2 lỗi (0.3%)
- **User correction (quan trọng):** "có mở tiktok lên k, mở tiktok lên thì phải chờ nó load r bắt đầu gọi" — phải có `am start` + `sleep` load. "Chờ load lâu lên máy s7 load lâu" — dùng 8s không 3s.
- User correction: "test max worker sao lại dùng ui automatore, t chuyển qua dùng atx service hết r" — **dùng ATX API (port 7912), KHÔNG dùng shell uiautomator dump** (farm đã chuyển hết sang ATX, xem atx-agent-primary-ui-xml).

## Kết luận chốt (user duyệt 2026-08-16)
- **max_workers = 30** cho feed session: 30 song song 0 lỗi ở cả bậc 2 và bậc 3; 40 bắt đầu lỗi nhẹ (retry được)
- Cơ chế pool: máy xong → máy khác vào ngay (ThreadPoolExecutor, KHÔNG chờ tick 15')
- Stagger đã có sẵn (`_machine_start_stagger_ms = (2000, 8000)` multi_machine_feed_session.py:1034) — 30 máy dàn 1-4 phút, không đồng loạt
- Jitter anchor ±20' (dời ngày khác nhau) + stagger 2-8s (dàn trong 1 lần chạy) = 2 lớp chống fingerprint đồng loạt

## Pitfall chung
- Test load phải dùng **đúng tool farm dùng** (ATX service, không uiautomator shell — farm chuyển hết rồi)
- Mô phỏng phải có bước mở app + chờ load (S7 ~8s) — thiếu bước này test sai kết quả
- `ThreadPoolExecutor(max_workers=n)` + `ex.map` là cách test song song chuẩn trong 1 process
- Kết quả "N song song 0 lỗi" mới đáng tin khi workload = thao tác thật liên tục, không phải 1 call lẻ
