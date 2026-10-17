# Grace Band (80-84), Plateau Handling & Model Governance in Closeout Loops

Bài học và quy chuẩn chốt phiên rút ra từ phiên làm việc 17/10/2026:

## 1. Bản chất điểm Plateau 80–84 & Cơ chế Grace Band
- **Hiện tượng Plateau:** Khi một patch $O(1)$ ($\le 30$ dòng, $\le 2$ files) có 100% focused tests PASS (0 fail, 0 error), Sol Reviewer thường trừ 1-5 điểm cho các lý do mang tính hệ thống/ngoại cảnh mà một patch nhỏ không thể đáp ứng (ví dụ: *"chưa test cắm trên máy thật farm"*, *"chưa chạy full regression toàn repo"*).
- **Grace Band (80–84 điểm):**
  * Được phép phê duyệt **APPROVED** và kích hoạt `auto-push` khi thỏa mãn:
    1. Điểm rơi vào mốc **80 – 84 / 100**.
    2. Patch $O(1)$ ($\le 30$ dòng diff, $\le 2$ files).
    3. Focused tests pass 100% (bắt buộc `passed >= 1`, 0 failed, 0 errors).
    4. Không có lỗi logic hoặc bảo mật (chỉ bị trừ điểm do thiếu test toàn cục/hạ tầng).
  * Chấm dứt tình trạng bị kẹt ở 84 điểm rồi quay sang hỏi User "có push không?" (vi phạm nguyên tắc tự chủ dứt điểm).

## 2. Loại bỏ tư duy "WIP Branch Parking"
- Với farm tự động hóa, patch không vào `main` nghĩa là farm không có bản vá.
- Tuyệt đối KHÔNG cất code vào WIP branch / Park rồi báo xong việc. Task giao ra là phải đưa vào `main` an toàn.

## 3. Khóa cứng Model Governance (Chống bào mòn Quota Sonnet)
- **Vòng lặp sửa chữa tự động (Remediation):**
  * Vòng 1 & 2: Dùng **Sol Repair** (local trên `:20129`, miễn phí 100%).
  * Vòng 3: Dùng **Haiku 5.5** hoặc **Agy CLI (Gemini Pro pool)** để sửa dứt điểm lỗi cụ thể.
  * Hard Cap: Tối đa 3 vòng sửa, không cho phép vòng lặp vô tận ("loop until tests pass").
- **Sonnet 5.5:** Bị CẤM HOÀN TOÀN trong các vòng lặp sửa lỗi tự động. CHỈ ĐƯỢC PHÉP gọi Sonnet khi có lệnh đích danh từ User ("gọi sonnet tư vấn", "bảo sonnet review").

## 4. Quản lý lệnh "Done" và `--owner-override`
- Từ khóa `"Done"` là lệnh bắt đầu quy trình đóng phiên tự động, không phải lệnh ép push bỏ qua an toàn.
- Cờ `--owner-override` chỉ được kích hoạt khi:
  * Đã qua Gate $\ge 80$ với Grace Band.
  * Hoặc User phát lệnh cưỡng chế rõ ràng ("cứ push đi", "ép push", "bỏ qua gate").
