# Kinh Nghiệm Chọn Frame Avatar TikTok: Bẫy OpenCV HaarCascade vs Tiêu Chuẩn Niche

## Bối Cảnh & Sự Cố (2026-10-20)
Khi chạy bóc tách avatar tự động hàng loạt từ video gốc (.mp4) bằng thuật toán OpenCV `HaarCascade` thuần túy, kết quả xuất ra bị lỗi nặng ("Hình này k hiểu", "40 vs 58 lỗi r"):
1. **Bắt nhầm bàn tay/đồ vật**: Nhận diện nhầm ngực và 2 bàn tay cầm điện thoại thành khuôn mặt (Folder 40) do góc tối và phụ đề.
2. **Bắt trúng filter biến dạng khuôn mặt**: Video TikTok hài hước có filter môi tều, mặt troll méo mó (Folder 70), OpenCV vẫn tính là "mặt người" $\rightarrow$ avatar dị hợm.
3. **Bắt nhầm sticker hoạt hình**: Má hồng nơ 2D trên sticker (Folder 83) bị nhận nhầm thành mặt người.
4. **Bẫy Podcast / Phòng thu âm**: Video dạng talkshow/podcast có headphone to trùm đầu và micro thu âm to che trước cằm/ngực (Folder 40) $\rightarrow$ avatar bị che khuất và ngột ngạt.
5. **Bẫy Showroom / Góc toàn cảnh xa**: Video quay cửa hàng/showroom xe máy (Folder 58), người đứng quá xa $\rightarrow$ crop vào bị vỡ nét, hạt to, góc mặt gượng gạo.

## Bộ Lọc Tiêu Chuẩn Cho Avatar TikTok Đạt Chuẩn (Chống False Positive)

### 1. Điều Kiện Kích Thước & Độ Nét Bắt Buộc:
* Kích thước khuôn mặt tối thiểu: `minSize = (160, 160)` trên khung hình 1080p (hoặc $\ge 25\%$ chiều rộng frame). Tuyệt đối không lấy mặt quá nhỏ ở hậu cảnh.
* Điểm sắc nét (Laplacian variance): `variance > 100`. Mặt mờ nhòe do chuyển động hoặc zoom từ góc rộng phải bị loại bỏ ngay.

### 2. Tiêu Chuẩn Ngữ Nghĩa (Bắt Buộc Kiểm Tra Qua Vision LLM Trước Khi Nạp):
* **Cấm filter troll / méo mặt**: Tuyệt đối không chọn frame trong các đoạn hiệu ứng hài hước.
* **Cấm micro / vật cản che mặt**: Không chọn frame host đang nói chuyện bị mic phòng thu hoặc pop-filter che miệng/cằm.
* **Không chọn nhân vật trong poster/banner dính chữ**: Chữ phụ đề, logo kênh YouTube cũ, banner đè vào mặt đều phải loại.
* **Góc mặt & biểu cảm**: Ưu tiên góc chính diện (frontal) hoặc nghiêng nhẹ $\le 15^\circ$, nụ cười tự nhiên, mắt nhìn thẳng vào ống kính.
* **Căn chỉnh viền tròn (Circular Boundary Safe Zone)**: Khuôn mặt và đỉnh đầu phải nằm trọn vẹn trong vòng tròn an toàn (headroom ~0.35, scale 2.2 - 2.3), không bị mép tròn TikTok cắt ngang đỉnh đầu hoặc cằm.
