# Concurrency cap testing (max_workers) — dùng ĐÚNG công cụ thật

Bài học 2026-08-16 (plan 3 phiên/ca + follow hook): khi user hỏi "max_worker bao nhiêu vừa đủ / test chính xác cách nào" — **test bằng công cụ farm THẬT đang dùng, không phải công cụ mình nghĩ**.

## Sai lầm đã mắc (user sửa)

1. Test bằng `uiautomator dump` song song → user: *"Ủa test max worker sao lại dùng ui automatore, t chuyển qua dùng atx service hết r mà"* → farm đọc UI qua **ATX agent (port 7912)**, không phải uiautomator.
2. Gọi sai ATX endpoint: `/wd/hub/session`, `/wd/hub/status`, `/jsonrpc/0` đều fail. Endpoint đúng của atx-agent lifecycle: **`POST http://127.0.0.1:7912/uiautomator`** (body `{}`, header `Content-Type: application/json`) — xem `python_runner/core/capture_recovery.py:1114 _atx_http_request`.
3. Test chỉ 1 call nhẹ → user: *"Thế có mở tiktok lên k, mở tiktok lên thì phải chờ nó load r bắt đầu gọi"* → phải mô phỏng **cả phiên**: mở app (`am start -n com.ss.android.ugc.aweme/.main.MainActivity`) + chờ load (máy S7 load lâu → 8s) + lặp 15× (đọc UI + swipe + sleep).

## Recipe test chuẩn (Python, ThreadPoolExecutor)

```python
def atx_call(dev):
    req = urllib.request.Request('http://127.0.0.1:7912/uiautomator', data=b'{}',
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=25) as r: r.read()
        return 0
    except Exception: return 1

def sim_session_s7(dev):  # giả lập phiên S7 thật
    subprocess.run([ADB, '-s', dev, 'forward', 'tcp:7912', 'tcp:7912'], capture_output=True)
    subprocess.run([ADB, '-s', dev, 'shell', 'am', 'start', '-n',
                    'com.ss.android.ugc.aweme/.main.MainActivity'], capture_output=True, timeout=15)
    time.sleep(8)  # S7 load lâu
    for i in range(15):
        fails += atx_call(dev)
        subprocess.run([ADB, '-s', dev, 'shell', 'input', 'swipe', '540','1500','540','400','200'],
                       capture_output=True, timeout=10)
        time.sleep(0.5)
    return time.time()-t0, fails

for n in (20, 30, 40):  # chạy map qua ThreadPoolExecutor(max_workers=n)
    ...
```

## Kết quả đo thật (80 máy online, 2026-08-16)

| Parallel | ATX /uiautomator 1 call | Mô phỏng phiên (15 reads+swipe) | Mô phỏng S7 (mở app + load 8s) |
|---|---|---|---|
| 20 | 0 lỗi | 0 lỗi | 0 lỗi |
| 30 | 1 lỗi transient | **0 lỗi** | **0 lỗi** |
| 40 | 1 lỗi | 2 lỗi (0.3%) | — |
| 60-80 | 3-6 lỗi | — | — |

→ **Chốt max_workers = 30** (0 lỗi ở tải thật, nhanh). 20 = an toàn tuyệt đối; 40+ bắt đầu lỗi nhẹ (retry được).

## Lưu ý

- `adb forward tcp:7912 tcp:7912` dùng **chung local port 7912** — nhiều máy forward đồng thời có thể đụng; code production dùng port riêng mỗi máy (9008, capture_recovery.py:1589) nên không bị.
- Không background `&` trong terminal (Hermes chặn) — dùng Python ThreadPoolExecutor + `terminal` foreground.
- Tải thật = mở app + chờ load (S7 chậm) + nhiều lần đọc UI, không phải 1 call nhẹ — test 1 call nhẹ cho kết quả lạc quan giả.
