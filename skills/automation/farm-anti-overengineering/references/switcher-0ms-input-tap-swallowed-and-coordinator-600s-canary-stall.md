# Switcher 0ms `input tap` Swallowed & Coordinator 600s Canary Stall Trap (Case Máy 8, 2026-09-07)

## 1. Hiện tượng & Phản ứng từ User
- **Cảnh báo farm:** `[FARM ALERT: MÁY 8] DỪNG PHIÊN - Nick: tolmavhj12k - profile username still mismatched after switch`.
- **Hành vi sai lầm của Coordinator:**
  1. Phỏng đoán qua lại giữa tọa độ tâm Button (`x=540`) và tọa độ inner TextView (`x=393`). Cả 2 tọa độ đều tap trượt (TikTok vẫn giữ nguyên nick cũ `donieovhdvc`).
  2. Coordinator tự kích hoạt lệnh Canary PowerShell trực tiếp tại terminal session chính với `timeout=600`.
  3. Lệnh chạy kẹt trong tiến trình reconcile/feed, ngốn trọn 10 phút (600s) làm đơ hoàn toàn khung chat Telegram, kích hoạt terminal timeout `exit_code: 124`.
- **Phản ứng gắt từ User:** *"Mày lại bắt đầu over engineer r phải k"*.

---

## 2. Nguyên nhân kỹ thuật cốt lõi (Technical Root Cause)

### A. Lỗi nuốt sự kiện chạm 0ms trên Custom Button TikTok 46.x
1. **Bản chất lệnh `input tap`:**
   Lệnh `adb shell input tap x y` của Android bắn ra sự kiện `ACTION_DOWN` và `ACTION_UP` đồng thời trong cùng một tick (**thời lượng giữ chạm = 0ms**).
2. **Cơ chế chống chạm nhầm của TikTok:**
   Trên TikTok 46.x (chạy trên Android 7/8 Samsung S7), các container trong Bottom Sheet (`id/lkp`, `id/l9b`) sử dụng cơ chế lọc cử chỉ chạm (gesture filtering) để chống quẹt nhầm khi cuộn danh sách. Mọi sự kiện tap có thời lượng 0ms đều bị kernel/view framework nuốt chửng, không kích hoạt `OnClickListener`.
3. **Hệ quả:**
   Dù tap trúng giữa Button `(540, 708)` hay trúng giữa chữ TextView `(393, 708)`, TikTok đều không chuyển nick. Dấu tick xanh (`id/fiu`) vẫn giữ nguyên ở tài khoản cũ, dẫn tới `profile username still mismatched after switch`.

### B. Giải pháp cơ học chuẩn: Giữ chạm 120ms bằng `input swipe`
Thay vì tap 0ms, sử dụng `input swipe` tại cùng một tọa độ với tham số thời gian 120ms:
```python
# Giữ chạm 120ms để kích hoạt click event trên custom bottom sheet
result = ctx.adb.shell(
    ["input", "swipe", str(x), str(y), str(x), str(y), "120"],
    timeout=ctx.timeout("adb_seconds", 15)
)
if not result.ok:
    result = ctx.adb.shell(["input", "tap", str(x), str(y)], timeout=ctx.timeout("adb_seconds", 15))
```

---

## 3. Cạm bẫy Coordinator 600s Canary Blocking Stall & Kỷ luật phòng tránh

### A. Cạm bẫy chặn luồng (Blocking Trap)
- Lệnh Canary `run-feed-session.ps1` khi gặp trục trặc reconcile có thể chạy tới 9–15 phút.
- Nếu Coordinator chạy đồng bộ với `timeout=600` ở session chính:
  * Khung chat Telegram bị treo cứng (freeze) trong 10 phút.
  * User không thấy bất kỳ phản hồi nào, gây nghi vấn over-engineering hoặc script chạy lạc hướng.
  * Hết 600s tool bị kill, để lại tiến trình mồ côi (zombie/orphaned python) chiếm giữ device lock trên máy farm.

### B. Kỷ luật bắt buộc (Hard Rules):
1. **CẤM Coordinator chạy Canary trực tiếp ở session chính với timeout > 180s.**
2. **Bắt buộc dispatch Canary qua Worker Subagent** (`delegate_task`) hoặc chạy background `terminal(background=True, notify_on_complete=True)`:
   * Worker subagent theo dõi log và kết quả, trả về receipt gọn gàng.
   * Session chính luôn giữ được trạng thái tương tác với user, không bao giờ để khung chat bị đơ quá 2 phút.
