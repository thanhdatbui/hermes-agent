# Outbound Attestation Workflow & Anti-Hallucination Recipe

## 1. Bản Chất Vụ Án: Mù Quáng Tin Excel & Bịa Đặt Avatar
Khi thực hiện chuẩn hóa kênh hoặc cắt avatar từ video:
1. **Lỗi ngộ nhận từ Excel:** File `Tik5.xlsx` dòng 75 ghi nhầm `Niche: Thú Cưng / Chó Cưng`.
2. **Ảo giác Upstream:** Bot cắt video `18.mp4` trong kho `D:/video goc/394` (thực tế là cảnh một người đàn ông há hốc mồm cãi vã trong nhà hàng bên cạnh đầu bếp DUY), nhưng bot lại không mở mắt nhìn cái ảnh mình vừa cắt, mà tự động dùng định kiến "Thú Cưng" trong Excel để tuôn ra văn mẫu: *"Khuôn mặt chú cún cưng lông nâu cân đối 2 tai, lông nét căng..."*.
3. **Khi User quăng ảnh lại để chửi:** Bot lại tưởng User quăng ảnh bên ngoài vào để thử Gate, rồi tiếp tục cãi chày cãi cối mà không nhận ra đó chính là file avatar mình vừa tự tay cắt!

## 2. Quy Trình Thực Thi Cơ Học O(1) Bắt Buộc Khi Cắt Avatar

```bash
# Bước 1: Trích xuất frame ra file avatar
python -c "
import cv2
cap = cv2.VideoCapture('D:/video goc/<id>/<clip>.mp4')
# crop vuông 1:1 ...
cv2.imwrite('D:/Taadaa/reports/avatar_temp.jpg', crop)
"

# Bước 2: Attestation thị giác tại chỗ (BẮT BUỘC 100% TRƯỚC KHI BÁO CÁO)
python -c "
from tools.vision_tools import vision_analyze_tool
import asyncio

async def attest():
    res = await vision_analyze_tool(
        image_url='D:/Taadaa/reports/avatar_temp.jpg',
        user_prompt='Describe exactly what is shown in this avatar image in 1 sentence. Is it a human, an animal, food, or text?'
    )
    print('ATTESTED_SUBJECT:', res)

asyncio.run(attest())
"
```

## 3. Quy Tắc Ứng Xử Bắt Buộc (Fail-Closed)
1. **Lấy ATTESTED_SUBJECT làm mỏ neo sự thật duy nhất:**
   - Nếu `ATTESTED_SUBJECT` báo là Người (`Human drama scene`) mà Excel ghi là Chó cưng $\rightarrow$ **Excel sai 100%**.
   - BẮT BUỘC mô tả sự thật: *"Ảnh vừa cắt là cảnh người trong phim ngắn/drama, không phải chó cưng"*.
   - Lập tức mở file Excel sửa lại cột Keyword/Niche theo đúng nội dung video thật.
2. **CẤM TUYỆT ĐỐI:** Cấm lấy bất kỳ văn mẫu nào từ bộ nhớ cũ hoặc từ Excel để đắp vào ảnh vừa tạo nếu chưa có kết quả `ATTESTED_SUBJECT` từ `vision_analyze_tool`.
