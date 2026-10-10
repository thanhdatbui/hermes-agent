# Cross-Cluster Media Isolation & Admin Contamination Reversion (2026-10-10)

## 1. Bối cảnh & Sai lầm Nghiêm trọng
Khi Operator yêu cầu: *"Làm cả admin"* (chuẩn hoá avatar toàn bộ cụm Admin), Agent phát hiện thư mục `D:\TIKTOK-videonuoinick-admin` trên máy chủ `admin-farm` bị thiếu 407/640 file `avatar.jpg`.
Do thiếu thận trọng và suy diễn cẩu thả, Agent đã:
1. Đóng gói toàn bộ 640 file `avatar.jpg` từ trạm Kibe (`D:\TIKTOK-videonuoinick`) thành file tarball `kibe_avatars.tar`.
2. SCP sang máy chủ Admin và giải nén đè vào `D:\TIKTOK-videonuoinick-admin`.

Ngay lập tức, Operator chấn chỉnh gay gắt:
> *"Là sao? Tự nhiên lấy của kibe ném qua admin!!?"*

---

## 2. Bản chất Kỹ thuật & Căn nguyên Lệch Niche
- **Hai kho nguồn video hoàn toàn độc lập:**
  - **Trạm Kibe (Máy 1–80):** Sử dụng kho video gốc `D:\video goc` và kho video render `D:\TIKTOK-videonuoinick`.
  - **Trạm Admin (Máy 201–280):** Sử dụng kho video gốc `D:\video goc may 2` và kho video render `D:\TIKTOK-videonuoinick-admin`.
- **Cùng số folder nhưng khác hoàn toàn nội dung và ngách video:**
  - **Folder 1 trên Admin (`D:\video goc may 2\1`):** Chứa các clip đời thường/vlog của **bé gái học sinh tiểu học áo trắng cổ xanh** tại trường tiểu học Long Hòa (miền Tây sông nước).
  - **Folder 1 trên Kibe (`D:\TIKTOK-videonuoinick\1`):** Chứa clip meme hài hước của **nam thanh niên đeo kính râm áo ba lỗ ôm mèo reaction**.
- **Hậu quả:** Việc lấy avatar từ Kibe ném qua Admin gây ra **ô nhiễm chéo ngách toàn diện (cross-cluster niche contamination)**. Hàng trăm tài khoản của Admin sẽ bị bot upload gắn avatar của các nhân vật hoàn toàn không liên quan đến video đang đăng.

---

## 3. Quy trình Revert Khẩn cấp & Khôi phục Đúng Nguồn
Khi phát hiện đã copy nhầm avatar từ Kibe sang Admin:

### Bước 1: Xóa sạch file ô nhiễm từ Kibe
Xác định toàn bộ các folder trong `D:\TIKTOK-videonuoinick-admin` mà nguồn không thuộc về `D:\video goc may 2` và xóa bỏ (`unlink()`) ngay lập tức để không cho watchdog/runner bốc nhầm:
```python
vg2_ava_folders = {int(f.name) for f in vg2.iterdir() if f.is_dir() and f.name.isdigit() and (f / "avatar.jpg").exists()}
for f in admin_nuoi.iterdir():
    if f.is_dir() and f.name.isdigit():
        fnum = int(f.name)
        av = f / "avatar.jpg"
        if av.exists() and fnum not in vg2_ava_folders:
            av.unlink()
```

### Bước 2: Khôi phục avatar gốc từ `D:\video goc may 2`
Sao chép lại toàn bộ avatar chuẩn xác mà chính Admin đã sở hữu từ `D:\video goc may 2` sang `D:\TIKTOK-videonuoinick-admin`:
```python
for f in vg2.iterdir():
    if f.is_dir() and f.name.isdigit():
        av = f / "avatar.jpg"
        if av.exists():
            target_dir = admin_nuoi / f.name
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(av, target_dir / "avatar.jpg")
```

### Bước 3: Xác minh đối soát hash MD5
Kiểm tra MD5 hash của các folder tiêu biểu (ví dụ Folder 1) trên Admin để bảo đảm 100% trùng khớp với `video goc may 2` và hoàn toàn khác với file của Kibe.

---

## 4. Invariant Bắt buộc cho Vận hành Đa Cụm (Multi-Cluster Farm)
1. **CẤM TUYỆT ĐỐI COPY MEDIA XUYÊN CỤM:** Không bao giờ được phép copy video hoặc avatar giữa Kibe và Admin trừ khi có chỉ thị migrate rõ ràng từ Operator. Mỗi cụm farm quản lý một không gian media riêng biệt.
2. **TRÍCH XUẤT AVATAR TẠI CHỖ (LOCAL EXTRACTION):**
   - Muốn bổ sung avatar cho các folder còn thiếu trên Admin: BẮT BUỘC chạy script trích xuất trực tiếp từ các file `.mp4` nằm trong `D:\video goc may 2\<folder>` của Admin.
   - Nếu folder trên Admin chưa có video (`0 mp4`): BẮT BUỘC giữ nguyên trạng thái thiếu avatar chờ downloader cào video về, tuyệt đối không lấy ảnh placeholder của máy khác lấp vào.
