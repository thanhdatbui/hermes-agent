# Kỹ thuật Chọn Kênh Gái Xinh & Trích Xuất Avatar Chuẩn Farm

## 1. Tránh Kênh Cosplay / Anime / Reup Phim khi nạp Nguồn Gái Xinh
* **Hiện tượng:** Kênh mang tên "gái xinh" nhưng reup cosplay nhân vật game (Genshin, Anime), trích đoạn phim ngắn Douyin, làm avatar và video bị nhận diện nhầm thành hoạt hình/dị dạng.
* **Quy tắc chọn kênh:**
  - Lọc keyword tiêu đề: cấm `cosplayer`, `genshin`, `anime`, `hoathinh`, `phimtrungquoc`, `phimngandouyin`.
  - Ưu tiên kênh cá nhân người thật tự quay nhảy nhẹ nhàng, vlog đời thường (ví dụ `@diepyenvy55`).

## 2. Haar Cascade Face Detection Pitfall trên Video TikTok
* **Bẫy icon mép màn hình (Music Disc / Floating Icons):**
  - Icon đĩa nhạc xoay TikTok ở góc phải dưới (`x > 0.8*w, y > 0.7*h`) và icon avatar kênh ở mép phải thường có dạng tròn và bị OpenCV `detectMultiScale` nhận diện nhầm thành khuôn mặt (false positive).
  - Phải ép **Central Boundary Guard**:
    ```python
    # Chỉ nhận diện khuôn mặt ở vùng trung tâm khung hình (trừ lề UI):
    if 0.2 * w < cx < 0.8 * w and 0.15 * h < cy < 0.75 * h:
        # Khuôn mặt hợp lệ
    ```
  - Đặt `minSize=(140, 140)` để tránh bắt các icon nhỏ hoặc vật thể tròn.

## 3. TikTok 47.x Profile Layout
* **Bố cục Avatar mới:** Vòng tròn avatar của user dời sang góc trên bên phải cạnh tên handle. Vòng tròn to có dấu cộng `+` ở giữa là "Thêm vào Nhật ký" (Story).
* **Nút Sửa Hồ Sơ:** Icon bút chì góc trên bên trái `[24,96][126,204]`, tâm `(75, 150)`.
