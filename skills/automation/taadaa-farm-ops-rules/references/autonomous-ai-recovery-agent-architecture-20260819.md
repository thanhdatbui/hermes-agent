# Kiến Trúc Autonomous AI Auto-Recovery Cho Farm Android (User Chốt 19/08/2026)

## 1. Bản Chất & Phân Vai (Producer — Subagent Orchestrator — Vision/Review Workers)

1. **Producer (Script Nuôi Acc / Runner trên máy — 0 Token LLM)**:
   - Khi gặp lỗi dừng phiên / blocker chưa giải quyết được: Chụp ảnh hiện trường, vẽ **Banner Đỏ `[MAY XX] - HH:MM DD/MM`** ở đỉnh ảnh.
   - Gửi **Tin nhắn 1** vào nhóm Telegram **Farm Alerts** (`-5373649734`).
   - **BẢO TOÀN HIỆN TRƯỜNG LỖI**: Tuyệt đối không bấm Home, không tắt app để giữ nguyên trạng thái UI cho AI xử lý.
   - **Spawn Subagent Ngầm**: Gọi `subprocess.Popen([python, "-m", "ai_recovery.agent", ...])` chạy nền độc lập rồi kết thúc ca chạy chính sạch sẽ, không bị block hay treo tiến trình feed.

2. **Autonomous Recovery Agent (`python_runner/ai_recovery/agent.py`)**:
   - Nhạc trưởng tự hành độc lập điều phối quy trình 5 bước.
   - **Quản lý khóa Per-Device Lock (TTL 5 phút)**: Tránh xử lý dồn dập nhiều lần trên cùng 1 máy.
   - **Pre-check Live Screen (`screen_verifier.py`)**: Dùng `dHash` so khớp ảnh màn hình thật của máy xem có còn đúng màn hình kẹt không (nếu người dùng bấm tay hoặc máy tự đổi thì dừng lại, không can thiệp bậy).
   - **Auto-Rollback Counter**: Nếu 1 lỗi xuất hiện $\ge 3$ lần trong 15 phút sau khi patch, tự động `git revert` và gửi cảnh báo khẩn cấp.

3. **Mô Hình Não AI Vận Hành**:
   - **Vision & Coding Worker**: `ag/claude-opus-4-6-thinking` (gửi ảnh base64 + UI XML dump qua 9Router port 20128) ➔ Đọc ảnh, suy luận bản chất kẹt và sinh đoạn code rule/handler Python hoàn chỉnh.
   - **Plan-Review Audit Worker**: `gpt-5.6-terra` (combo `plan-review` kịch trần `reasoning_effort: max`) ➔ Audit git diff của code vừa sinh, bắt buộc nhận `VERDICT: APPROVED`.

---

## 2. QUY TẮC CỐT LÕI: CODE TRƯỚC ➔ TEST TẠI CHỖ KẸT THAY TAY ➔ PUSH GIT ➔ BÁO CÁO

> **TUYỆT ĐỐI CẤM**: Bắn lệnh ADB thô bằng tay trước rồi mới viết code sau. Làm tay trước làm mất hiện trường lỗi, khiến không còn môi trường thực tế để kiểm chứng đoạn code vừa viết có chạy được thật hay không.

### Chuỗi 5 Bước Bắt Buộc:
```
┌─────────────────────────────────────────────────────────────┐
│ 1. AI ĐỌC ẢNH & SUY LUẬN                                    │
│ • Vision Model soi ảnh alert_machine_{X}.png + cây UI XML   │
│ • Xác định loại blocker: Popup, Survey, Live, CTA, Shop...  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VIẾT CODE / ENCODE VÀO SCRIPT TRƯỚC                      │
│ • Mở file runner (feed_swipe_smoke.py / benign_popup.py)    │
│ • Nạp rule/handler mới vào GEMPHONEFARM_BLIND_POPUP_RULES   │
│ • Gọi Model Plan-Review audit diff (bắt buộc APPROVED)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CHẠY CHÍNH HÀM VỪA CODE LÊN MÁY ĐANG KẸT                │
│ • Kích hoạt hàm vừa viết chạy trực tiếp trên máy đang lỗi   │
│ • Chụp ảnh sau thao tác: Xác nhận máy đã vượt qua bước kẹt  │
│ • (TUYỆT ĐỐI KHÔNG reset hay chạy lại từ đầu)               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. KIỂM THỬ REGRESSION & COMMIT GIT                         │
│ • Chạy test suite pytest (test_feed_swipe_smoke.py /        │
│   test_ai_recovery.py) đảm bảo 100% PASS                    │
│ • Git commit & push origin master đồng bộ toàn bộ 80 máy    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. BÁO CÁO KẾT QUẢ VÀO NHÓM FARM ALERTS                    │
│ • Reply Tin nhắn 2 với đầy đủ Hướng sửa, Kết quả thực tế    │
│   và thông tin Code patch đã commit                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Format Báo Cáo Chuẩn Nhóm Farm Alerts

```text
🛠️ [AI AUTO-RECOVERY - MÁY XX]
• Hướng sửa: <Giải thích lý do kỹ thuật gốc từ ảnh/XML và logic đã vá>
• Kết quả: 🟢 THÀNH CÔNG — màn hình đã thay đổi sau lệnh ADB — <Hành động thực tế>
• Code patch: ✅ Đã commit <handler_name> → <target_file> SHA <sha_commit>
• pytest: <Dòng tóm tắt kết quả pytest 100% pass>
• (Nếu đúng ý bạn im lặng bỏ qua, cần sửa cách khác hãy nhắn lại)
```

---

## 4. Troubleshooting & Gotchas
- **Lỗi 9Router 401 Unauthorized**: Token trong `.env` (`NINEROUTER_API_KEY`) phải khớp với API Key lưu trong `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (bảng `apiKeys`).
- **Telegram Bot Self-Message Loop Guard**: Telegram Bot API không bao giờ gửi webhook/polling update cho tin nhắn do chính bot đó gửi ra. Do đó, Producer phải chủ động spawn subagent `ai_recovery.agent` thay vì chờ bot trong group tự nghe tin nhắn của chính mình.
