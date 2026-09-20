# Ad-hoc Sol Consultation & TikTok Shadowban Detection Standard

## 1. Ad-hoc Sol Consultation Protocol (Cấm Nói "Không Có Kênh Gọi Sol")

Khi sếp/user ra lệnh:
- *"Gọi sol hỏi..."*
- *"Hỏi sol xem..."*
- *"Tham vấn sol..."*

### Quy tắc cứng:
1. **TUYỆT ĐỐI CẤM** trả lời: *"Mình không có kênh gọi trực tiếp tên Sol..."* hoặc từ chối hỗ trợ. Đây là lỗi nhận diện ngữ cảnh nghiêm trọng khiến user ức chế.
2. **Sol** là chuyên gia kỹ thuật và vận hành cao cấp của hệ thống Taadaa Phone Farm, đại diện bởi mô hình `GPT-5.6 Sol` chạy qua OmniRoute Local API tại `http://127.0.0.1:20129`.

### Cách gọi Sol tức thì từ Coordinator (Python snippet / curl):
```python
import requests

url = "http://127.0.0.1:20129/v1/chat/completions"
# Model nhanh: "chatgpt-web/gpt-5.6-sol-instant"
# Model sâu: "chatgpt-web/gpt-5.6-sol-high"
payload = {
    "model": "chatgpt-web/gpt-5.6-sol-instant",
    "messages": [
        {
            "role": "system",
            "content": "Bạn là Sol, chuyên gia vận hành hệ thống Phone Farm TikTok 160 máy. Trả lời trực diện, súc tích, thực chiến, không lý thuyết suông."
        },
        {
            "role": "user",
            "content": "<câu hỏi của user>"
        }
    ],
    "max_tokens": 1500
}

r = requests.post(url, json=payload, timeout=60)
if r.status_code == 200:
    sol_response = r.json()["choices"][0]["message"]["content"]
```

---

## 2. Chuẩn Nhận Diện Shadowban vs Tụt Follow Jitter (Sol Standard - 2026-09-20)

Trong vận hành Phone Farm 160 máy, thuật toán TikTok phân phối video theo nội dung và tương tác, **không phân phối theo follower**.

### Phân biệt rõ:
- **Tụt -1 đến -3 follow**: Là hiện tượng bình thường (jitter do bot dạo bị quét, người dùng unfollow ngẫu nhiên). TUYỆT ĐỐI KHÔNG coi là shadowban.
- **Tụt Bất Thường (`is_anomaly_drop`)**:
  - Công thức: `DropRate = (-delta_follower / prev_follower) * 100%`
  - Ngưỡng cảnh báo: `delta_follower <= -5` HOẶC `(delta_follower < 0 và DropRate >= 1.0% và follower >= 10)`.
- **Nghi Ngờ 0 FYP (`is_zero_fyp`)**:
  - Dấu hiệu mạnh nhất của việc video không được đưa vào luồng For You Page.
  - Công thức: `delta_video > 0` (vừa đăng thêm video mới) VÀ `delta_heart == 0` (sau chu kỳ quét không nhận thêm được dù chỉ 1 tim) trên tài khoản trạng thái `LIVE`.

### Ứng dụng trên TikTok Dashboard (`D:/Taadaa/tools/tiktok_dashboard.py`):
1. **Sub-filter BXH Biến động**:
   - `[⚡ Tất cả biến động]`
   - `[🟢 Chỉ Tăng (+)]`
   - `[🔴 Tụt Follow (-)]`
   - `[⚠️ Tụt Bất Thường (>1%)]`
   - `[🚫 Nghi Ngờ 0 FYP (Up video 0 Tim)]`
2. **Cụm Máy (Cluster Partitioning)**:
   - Cụm Kibe: Máy 1–80 (`cluster == 'kibe'`)
   - Cụm Admin: Máy 201–280 (`cluster == 'admin'` hoặc `may >= 200`)
