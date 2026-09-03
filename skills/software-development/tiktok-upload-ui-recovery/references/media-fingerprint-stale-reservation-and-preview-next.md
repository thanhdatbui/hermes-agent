# Media Fingerprint Stale Reservation Recovery & Feed-to-Upload Transition

## 1. Lỗi Stale Fingerprint Reservation (`MEDIA_FINGERPRINT_PENDING`)

### Triệu chứng:
Khi chạy upload video trên máy vừa bị ngắt quãng giữa chừng hoặc thử lại nhiều lần:
```text
[ERROR] scripts.tiktok_workflow.state_machine: [MEDIA_FINGERPRINT] [MEDIA_FINGERPRINT_PENDING] Exact media SHA-256 has unresolved ledger status=reserved
Checkpoint saved: MANUAL_REVIEW
```

### Nguyên nhân:
Trước khi upload, hệ thống ghi nhận file fingerprint vào ledger tại:
`D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<sha256>.json`
với trạng thái `"status": "reserved"`. Nếu run bị kill hoặc timeout trước khi hoàn tất hoặc fail sạch, reservation này bị treo vĩnh viễn và chặn tất cả các lần chạy sau của cùng video/account.

### Cách xử lý:
1. Quét tìm fingerprint file bị treo cho máy mục tiêu:
```python
from pathlib import Path
import json

ledger_dir = Path(r"D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints")
for f in ledger_dir.glob("*.json"):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("machine") == TARGET_MACHINE and d.get("status") == "reserved":
            f.unlink()
            print(f"Cleared stale reservation: {f.name}")
    except Exception:
        pass
```
2. Sau khi xóa ledger reservation stale, workflow upload sẽ cho phép reserve lại SHA-256 và tiếp tục chạy bình thường.

---

## 2. Luồng Feed ➔ Upload Transition & Giải phóng RAM / ATX

### Triệu chứng:
Cuối phiên 3 sau khi lướt feed 15-20 phút, gọi hook upload video bị timeout 900s hoặc kẹt `ATX_SESSION_UNAVAILABLE` ngay tại `WAIT_FEED`.

### Quy trình giải phóng RAM & Reset ATX bắt buộc trước Upload:
1. `am force-stop com.ss.android.ugc.trill` (Đóng TikTok để giải phóng RAM).
2. `pkill -9 -f uiautomator` & `pkill -9 -f atx-agent`.
3. `/data/local/tmp/atx-agent server -d` (Khởi động lại ATX sạch).
4. Sau đó mới gọi `run_post.py` / `scripts.tiktok_workflow`.

---

## 3. Editor Preview Screen "Tiếp" Button (Tọa độ 800, 1850)

### Triệu chứng:
Sau khi chọn video trong thư viện và bấm `Tiếp`, TikTok chuyển vào màn hình **Xem trước / Chỉnh sửa (Preview & Edit Screen)** với các công cụ biên tập (AutoCut, Văn bản, Sticker). Màn hình này có nút **"Tiếp" màu đỏ hồng lớn ở góc dưới bên phải** (`[800, 1850]`), chưa phải màn hình Đăng bài (Composer).

### Xử lý:
Nếu ATX dump bị miss do hiệu ứng động của Preview screen:
- Bấm nút `Tiếp` tại tọa độ góc dưới phải (`input tap 800 1850` hoặc theo bounds XML) để chuyển sang màn hình Caption / Đăng bài (`Composer`), sau đó mới thực hiện điền hashtag và bấm `Đăng`.
