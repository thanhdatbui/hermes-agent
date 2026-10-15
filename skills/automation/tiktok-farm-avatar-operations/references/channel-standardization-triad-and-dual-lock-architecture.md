# Chuẩn Hóa Bộ 3 Kênh (Ava - Hashtag - Pin) & Kiến Trúc Khóa Kép Chống Script Quét Đè

## 1. Yêu Cầu Vận Hành (User Directive & Invariant)
Khi nhận yêu cầu *"Chuẩn hoá kênh này / chuẩn hoá ava hashtag pin"*:
Hệ thống **BẮT BUỘC tự động kiểm tra đủ bộ 3 tiêu chí** mà không cần người dùng nhắc từng việc:
1. **Avatar (Ava):**
   - Soi ảnh đại diện thực tế trên profile app vs nội dung kênh (chân dung nhân vật thật, rõ mặt, không dùng ảnh thú cưng/ảnh ngẫu nhiên khi kênh là người thật).
   - Kiểm tra ảnh có sẵn trong kho `video goc/<F_src>` và `TIKTOK-videonuoinick/<F_out>` ($512 \times 512$, mặt cân đối ở tâm).
   - Đảm bảo đủ **cờ lock 3 tầng** chống tái sinh đè.
2. **Hashtag & Niche:**
   - Đối chiếu nội dung video thực tế vs `Keyword Video` & `Hashtag Pool` trong `Tik<Slot>.xlsx` (dòng tương ứng với máy $M$ và folder nguồn $F_{src}$).
   - Đảm bảo có **cờ khóa hashtag** (`manual_hashtag_protected_folders.json`) để script cronjob 15 phút không bao giờ ghi đè lại.
3. **Pin (Ghim Top Video):**
   - Quét lượt xem của toàn bộ video trên lưới profile.
   - Lọc các video có view vượt trội ($\ge 1.000$ views) nhưng chưa có nhãn "Đã ghim".
   - Tự động ghim tối đa 2–3 video top view lên đầu trang cá nhân bằng `pin_top_videos.py`.

---

## 2. Kiến Trúc Khóa Kép Độc Lập (Dual-Lock Architecture)

### Tại sao phải tách riêng Avatar Lock và Hashtag Lock?
Trước đây, việc lạm dụng file `manual_avatar_protected_folders.json` để chặn cả sync hashtag đã dẫn đến:
- **Test regression:** Unit test `test_sync_tik_file_integration` dùng folder `338` (vốn đã khóa avatar) để test đồng bộ keyword thông thường -> Test bị fail sai vì bị chặn nhầm.
- **Lệch ngữ nghĩa:** Một kênh có thể cần khóa avatar thủ công nhưng hashtag vẫn thuộc niche chuẩn để cronjob cập nhật; ngược lại một kênh có thể cần khóa bộ hashtag tùy biến riêng.

### Hai Tầng Khóa Độc Lập:

| Cơ chế khóa | File SSOT | Marker vật lý | Script áp dụng guard | Phạm vi bảo vệ |
| :--- | :--- | :--- | :--- | :--- |
| **1. Avatar Lock** | `D:\Taadaa\data\manual_avatar_protected_folders.json`<br>`D:\Taadaa\Tiktok-video\data\manual_avatar_protected_folders.json` | `.manual_avatar_locked` tại cả 4 folder ($F_{src}$, $F_{out}$) | `manual_avatar_guard.py`<br>(`is_folder_avatar_protected`) | Chặn tuyệt đối `regenerate_unique_avatars.py` và các batch avatar tự động ghi đè ảnh |
| **2. Hashtag Lock** | `D:\Taadaa\data\manual_hashtag_protected_folders.json` | Khóa trong registry JSON | `sync_all_tik_keywords.py`<br>(`is_folder_hashtag_protected`) | Chặn tuyệt đối cronjob 15 phút ghi đè lại `Keyword Video` và `Hashtag Pool` ở cả sheet `TaiKhoan` và `Hashtag theo Folder` |

### Cấu trúc chuẩn của `manual_hashtag_protected_folders.json`:
```json
{
  "protected_folders": [45, 326],
  "accounts": {
    "326": {
      "username": "alemafxjvxw",
      "machine": 6,
      "tik": 5,
      "video_goc": 326,
      "description": "Be Tuan Phong thieu nhi gia dinh"
    },
    "45": {
      "username": "alemafxjvxw",
      "machine": 6,
      "tik": 5,
      "video_goc": 326,
      "description": "Be Tuan Phong thieu nhi gia dinh"
    }
  }
}
```

---

## 3. Kỹ Thuật Khởi Động TikTok v47.0.3 Trên Samsung S7 (Pin & Profile Automation)

### Cạm bẫy Intent Explicit trên TikTok v47.0.3:
- Lệnh cũ: `adb shell am start -n com.ss.android.ugc.trill/.MainActivity`
  * Trên TikTok v47.0.3 mới, lệnh này **bị chặn intent explicit từ ngoài** hoặc fail im lặng, thiết bị vẫn kẹt ở màn hình Launcher (`com.sec.android.app.launcher`).
  * Dẫn đến lỗi `PROFILE_ROOT_NOT_CONFIRMED: Profile root was not confirmed` hoặc `UI_DUMP_INVALID`.

### Giải pháp Farm Invariant:
1. **Khởi động bằng Monkey Launcher:**
   ```bash
   adb shell monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1
   ```
2. **Nhịp chờ tải và chuyển Profile chủ động:**
   ```python
   execute_adb_cmd(serial, ["shell", "monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1"])
   time.sleep(8.0)  # Chờ SplashActivity chuyển vào Feed
   ad = ProfileAdapter(serial)
   ad.tap_profile()  # Tap tab Hồ sơ (972, 1857)
   time.sleep(3.0)   # Chờ profile tải đầy đủ
   xml = open_profile_root(ad)
   ```

---

## 4. Quy Trình Chạy Ghim Video Chuẩn (Pin Execution)
Chạy tool canonical với tài khoản và ngưỡng view:
```bash
python D:/Taadaa/tools/pin_top_videos.py --machine <M> --account <username> --min-views 1000 --max-pins 2
```
- Lệnh tự động đối soát số lượng video `is_pinned` trước và sau khi ghim (`pinned_before` -> `pinned_after`).
- Sau khi ghim, **BẮT BUỘC verify độc lập qua dump XML** kiểm tra nhãn `is_pinned: True` trên từng tile.
