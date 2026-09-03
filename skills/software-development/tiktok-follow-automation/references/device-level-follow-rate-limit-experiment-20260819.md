# Thực Nghiệm: TikTok Phạt Lây Theo Thiết Bị Khi Có Acc Dính Nhả Follow & Quy Tắc An Toàn (19/08/2026)

## 1. Bối cảnh & Câu hỏi Thực nghiệm
* **Vấn đề đặt ra:** Khi một thiết bị (máy) chạy một nick (Row 3 - 0 video) bị dính cờ nhả follow (`FOLLOW_FAILED`) vào buổi chiều, thì các nick uy tín khác trên cùng máy đó (Row 1 - đã có video, sáng chạy OK) khi chạy lại vào buổi tối/sau đó có bị TikTok phạt lây (`device/session cooldown`) không?

---

## 2. Kết quả Thực nghiệm Trực tiếp (Live Test Máy 33)
* **Thông tin đối tượng:** Máy 33 (Serial `ce0616061a74682305`).
  * Sáng 19/08: Row 1 (`@ngocc.dip66`, có video) follow thành công **17 nick** (`OK`).
  * Chiều 19/08 (17:15): Row 3 (0 video) bấm follow bị nhả (`FOLLOW_FAILED`).
* **Tiến hành test đêm 19/08:**
  1. Mở lại nick Row 1 trên Máy 33.
  2. Điều hướng vào profile `@phan.thanh.hi758` (nick trong danh sách farm).
  3. Bấm nút đỏ `Follow` -> Nút nhận tap.
  4. Thực hiện `pull-to-refresh` (kéo từ trên xuống) để reload profile.
* **Kết quả từ Vision AI:** Nút **LẬP TỨC BẬT ĐỎ LẠI THÀNH "FOLLOW" (KHÔNG LÊN SỐ / BỊ NHẢ NGAY)**.

---

## 3. Rút ra Quy Luật Kỹ Thuật (Key Takeaways)
1. **Hiện tượng "Rate-Limit Kép (Account + Device/IP Cooldown)":**
   * Khi 1 nick rác/0 video bị TikTok gắn cờ nhả follow trên máy -> TikTok tạm thời áp dụng cơ chế siết chặt tương tác xuất phát từ chính phiên mạng/thiết bị đó trong ngày.
   * Do đó, dù nick Row 1 buổi sáng rất uy tín, nhưng chạy lại trên máy vừa bị dính cờ lúc chiều vẫn bị nhả nút follow theo!
2. **Quy tắc An Toàn Bắt Buộc:**
   * **CẤM TUYỆT ĐỐI KHÔNG CHO NICK 0 VIDEO ĐI FOLLOW:** Chặn đứng bằng rule `zero-video-follow-disabled` trong `_run_follow_hook`. Nếu để nick 0 video bấm follow và bị nhả, nó sẽ "làm bẩn" toàn bộ phiên máy trong ngày, làm hại lây sang các nick khác.
   * **Giữ sạch thiết bị (Clean Device State):** Đảm bảo mỗi máy chỉ chạy follow trên các nick đã đạt điều kiện ($\ge 1$ video, tối ưu $\ge 8$ video) để bảo vệ Trust Score chung của thiết bị.
