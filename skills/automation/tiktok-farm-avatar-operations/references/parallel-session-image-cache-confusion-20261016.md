# Parallel-Session Image Cache Confusion (2026-10-16)

## 1. Bối cảnh & Hiện tượng

Khi User gửi lệnh **"Chuẩn hoá acc này"** cùng lúc trên **nhiều session song song** (ví dụ: Tik4 #2 lúc 22:19 và Tik2 #3 lúc 22:23), mỗi session đăng nhập xử lý một kênh khác nhau — nhưng coordinator trong session sau lại đọc nhầm file ảnh từ cache của session trước.

**Cụ thể đã xảy ra (2026-10-16 ~22:23):**
- Session A (`20261016_221913_0e4e90a5`): Chuẩn hoá nick `@daunthzrqig` (Mỹ phẩm/Skincare — Máy 66 Tik 4).
  - Hai phương án avatar được tạo: `opt1_red_v2_circle.jpg` và `opt2_white_v2_circle.jpg` (nam đeo kính, áo đỏ / áo trắng).
- Session B (`20261016_221940_cbe43d50`): Chuẩn hoá nick `@vukhodmee6s` (Bánh ngọt — Máy 61 Tik 2).
  - Coordinator đọc ảnh user gửi (`img_3394e776b50b.jpg`) NHƯNG khi phân tích lại trỏ vào `img_60985f16ba86.jpg` (ảnh từ Session A) → Gửi báo cáo avatar nam mỹ phẩm cho kênh làm bánh.
- User phát hiện: *"Ủa khoan. Sao ava này có session khác vừa đưa cũng chọn 1 trong 2 ảnh này. Là 2 kênh đang cào từ cùng 1 kênh nguồn à"*

**Nguyên nhân gốc rễ:**
- `hermes_image_cache` dùng tên file hash từ nội dung ảnh. Hai session xử lý cùng thời điểm, coordinator đọc file cache gần nhất thay vì file đính kèm trong lượt hiện tại.
- Sau nhiều tool call, context bị nén (compaction) — file ảnh đính kèm gốc của user trong session B bị mất liên kết, coordinator suy diễn nhầm sang cache session A.

---

## 2. Checklist Phòng Chống (Bắt Buộc Khi Xử Lý Song Song)

**Trước khi bắt đầu bất kỳ tác vụ chuẩn hoá nào:**

1. **Kiểm chứng file ảnh của session HIỆN TẠI** bằng cách đọc lại metadata:
   ```python
   os.path.basename(img_path)  # Phải khớp với hash trong tin nhắn user hiện tại
   ```
2. **Xác minh username trong ảnh** bằng Vision API ngay từ đầu, trước khi làm bất kỳ bước tra cứu farm nào:
   ```python
   ask_vision(img_path, "Tên hiển thị và Username (@...) trên màn hình TikTok này?")
   ```
3. **Chỉ trace username VỪA đọc được** khi tra Excel/SQLite — không dùng username của session khác hay context tóm tắt cũ.
4. **Sau khi crop avatar:** Gọi Vision soi mắt TRỰC TIẾP trên file vừa tạo tại path cụ thể, không lấy từ cache session khác.

---

## 3. Dấu Hiệu Nhận Biết Confusion

- User hỏi: *"Sao ảnh này giống session kia?"* / *"2 kênh cào chung nguồn à?"*
- Phân tích niche của 2 kênh HOÀN TOÀN KHÁC nhau (ví dụ: Skincare vs Bánh ngọt) nhưng báo cáo avatars lại giống nhau → Đây là confusion, không phải cùng nguồn.
- Avatar options đề xuất không khớp chủ đề của thumbnail video trên lưới kênh trong ảnh user gửi.

---

## 4. Cách Phân Biệt Nhanh "Cùng Nguồn" vs "Confusion"

Khi nghi ngờ 2 kênh cùng nguồn:
```python
# Check F_src của mỗi kênh
f_src_A = (slot_A - 1) * 80 + machine_A  # session A
f_src_B = (slot_B - 1) * 80 + machine_B  # session B

if f_src_A == f_src_B:
    print("THẬT SỰ cùng nguồn!")
else:
    print("KHÔNG phải cùng nguồn — kiểm tra lại file ảnh đã đọc đúng session chưa")
```

Và đối soát niche:
- Nếu niche A ≠ niche B → Chắc chắn **confusion**, không phải cùng nguồn.
- Nếu F_src A ≠ F_src B → Chắc chắn **confusion**, không phải cùng nguồn.

---

## 5. Pattern Vision Proxy Fallback (Khi ag_cli.py Timeout Do Tất Cả Profile Bị Lock)

Khi `ag_cli.py ask --file ...` liên tiếp timeout (exit 124) vì toàn bộ profile bị lease `< 300s`:

```python
# Dùng HTTP trực tiếp vào 9Router :20129 — không phụ thuộc profile lease
import urllib.request, json, base64

def ask_vision_proxy(img_path, prompt):
    with open(img_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {
        "model": "ag-gemini-pool-3",
        "stream": False,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]
        }]
    }
    req = urllib.request.Request(
        "http://127.0.0.1:20129/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"].strip()
```

**Lưu ý:** Cổng `:20129` là 9Router proxy — không bị lease lock như pool profile `ag_cli.py`.
Timeout khuyến nghị: 25-30s. Không dùng khi cần track context dài.

---

## 6. Kết luận Đúng Đắn Khi User Hỏi "2 Kênh Cào Chung Nguồn?"

Trả lời đúng khi đã xác minh:
1. **F_src khác nhau** → Hai kênh ĐỘC LẬP, không cào chung.
2. **Niche khác nhau** → Hai kênh ĐỘC LẬP.
3. Avatar options trùng là do **coordinator đọc nhầm file cache từ session chạy song song**.
4. Nhận lỗi rõ ràng: *"Em đã đọc nhầm file ảnh cache giữa 2 phiên song song. Đây là 2 kênh độc lập hoàn toàn."*
