# Quy Tắc: Fix Báo Lỗi Máy = Sửa Script Toàn Cục (Cấm Fix Tay / Bypass Ad-Hoc)

## Bài học từ phản hồi của User (Sự cố Máy 19 ngày 29/08/2026)

### 1. Bối cảnh & Hiện tượng sai lầm (Anti-Pattern)
- **Tình huống:** User gửi ảnh chụp cảnh báo Telegram báo lỗi trên Máy 19 (`account-switcher-not-open`) và yêu cầu "fix máy 19".
- **Hành vi sai lầm của Agent:** Agent tập trung kết nối ADB vào Máy 19, kiểm tra activity, gửi phím Home để máy hết kẹt UI rồi dừng lại hoặc giải thích hiện tượng, coi như đã "fix".
- **Hậu quả:** Thao tác ad-hoc chỉ giải quyết tạm thời màn hình cho 1 máy đơn lẻ. Lỗi gốc (trôi sang Search Landing / Explore Grid, thiếu popup dismissal trước switcher guard, anchor display_name không bung danh sách nick) vẫn tồn tại trên codebase và sẽ tiếp tục làm sập 159 máy còn lại trong Farm.

---

### 2. Quy trình chuẩn hóa (Standard Workflow)

Khi nhận được yêu cầu "fix máy N" kèm ảnh chụp màn hình / log lỗi:

```
[User báo lỗi Máy N + Ảnh/Log]
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Trích xuất Bằng chứng (Read-Only Evidence)          │
│    - Kiểm tra log.jsonl, ui.xml, screenshot hiện trường │
│    - Xác định chính xác root cause kỹ thuật             │
│    - CẤM gửi lệnh tap/bypass ad-hoc qua mặt bot         │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Patch Mã Nguồn Repo Toàn Cục                         │
│    - Sửa flow/core/matcher trong repo tương ứng         │
│    - Tích hợp auto-dismiss popup cản trở                │
│    - Bổ sung fallback logic / retry an toàn             │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Kiểm Thử Độc Lập & Cập Nhật Catalog                 │
│    - Chạy unit test / regression test                   │
│    - Cập nhật Case Fix vào docs/farm-automation-cases.md│
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Chốt Phiên & Phân Phối (Commit / Push)               │
│    - Đồng bộ sang toàn bộ repo liên quan                │
│    - Báo cáo súc tích: Mục đích → Kết quả → Blocker     │
└─────────────────────────────────────────────────────────┘
```

---

### 3. Nguyên tắc bất biến
1. **Hiện trường máy là Read-Only:** Thiết bị thật chỉ cung cấp dữ liệu phục vụ chẩn đoán.
2. **Nhiệm vụ "Fix" = Code Patch:** Kết quả bàn giao phải là diff code trong repo giải quyết được vấn đề cho toàn bộ Farm 160 máy.
3. **Cấm bypass bằng tay:** Không bấm hộ, không back hộ, không Home hộ để lấy kết quả giả tạo.
