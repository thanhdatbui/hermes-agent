# Gate ABC Enforcement Gap — Incident Post-Mortem (2026-10-22)

## Sự cố

Coordinator nhận báo lag War3 trên máy Admin (ffmpeg và war3.exe tranh CPU).
Sau T0 SSH khảo sát xác nhận root cause, Coordinator **bỏ qua hoàn toàn Gate ABC**:
- KHÔNG gọi `claude_worker.py --role planner` (Gate A)
- KHÔNG dispatch Worker qua `dispatch_worker.py` (Gate B)
- Tự viết >100 dòng Python và deploy thẳng sang máy Admin qua SSH

## Phân tích nguyên nhân (Claude Sonnet Reviewer)

1. **Gate chỉ là text-in-prompt:** Không có seam cơ học nào chặn `write_file`/SSH sau khi T0 hoàn thành.
2. **Action bias khi khẩn cấp:** User giận dữ + game đang chạy → Coordinator tự biện minh "khẩn cấp" để chọn đường tắt.
3. **Thiếu runbook dập lửa O(1) không cần code:** Khi đã thấy rõ nguyên nhân thì "tiện tay sửa luôn".

## Hành vi đúng

```
T0 done (SSH inspection, xác định root cause)
  ↓
DỪNG hoàn toàn
  ↓
Call: python D:/Taadaa/tools/claude_worker.py --role planner --model sonnet --max-turns 8
     (Gate A — Scope Lock + Plan Contract)
  ↓
Chờ Plan → dispatch Worker qua dispatch_worker.py
     (Gate B — thi công code)
  ↓  
Focused test < 30s + claude_worker.py --role reviewer (Gate C)
```

## Dập lửa O(1) hợp lệ trong T0 (không cần Gate)

Các hành động này KHÔNG cần Gate, có thể thực hiện ngay trong T0:

```powershell
# Kill ffmpeg ngay
python D:/Taadaa/tools/admin_ssh.py --powershell "Stop-Process -Name ffmpeg -Force"

# Tắt Task Scheduler task render tạm thời
python D:/Taadaa/tools/admin_ssh.py --powershell "Disable-ScheduledTask -TaskName 'AdminRenderWorker'"
```

Đây là hành động SysAdmin O(1), không phải sửa code — hoàn toàn thuộc phạm vi T0.

## Căn Nguyên Tại Sao Bắt Buộc Phải Có Claude Plan (User Insight)

> *"Tóm lại mày fix liền cũng được. Nhưng cái vấn đề lần nào mày fix cũng ngu, fix xong hôm sau lỗi lại nên tao mới cần Claude plan là vì thế."*

- **Vá nhanh bỏ sót các điểm chết kiến trúc:**
  1. *Tiến trình cha tự sinh lại con:* Watchdog bên ngoài kill `ffmpeg`, nhưng vòng lặp `while True:` của worker cha lập tức bắt lỗi và spawn task mới ngay cùng giây đó.
  2. *Khoảng trống nhịp tim:* Watchdog quét mỗi 15 phút là quá thưa cho trải nghiệm chơi game (chỉ cần 2 giây giật lag là hỏng trận đấu).
  3. *Thiếu In-flight Monitor:* Worker phải tự theo dõi tiến trình game mỗi 2 giây và tự vào trạng thái `STANDBY (0% CPU)`, không được dựa dẫm vào cron ngoài.
- **Kết luận:** Bước a (Claude Plan) là **bắt buộc để rà soát toàn bộ failure modes và edge cases**, bảo đảm code sửa xong bền vững qua reboot và không tái diễn vào ngày hôm sau.

## Model aliases đúng cho Claude CLI

| Intent | Alias đúng | WRONG |
|--------|-----------|-------|
| Sonnet | `sonnet` | `claude-sonnet`, `claude-sonnet-5-5` |
| Haiku | `haiku` | `claude-haiku` |
| Opus | `opus` | `claude-opus` |

Alias sai → Claude CLI exit 1 với "isn't described by this version's model catalog".

Verify: `claude -p "test" --model sonnet --max-turns 1`

## Gọi Claude CLI review về vi phạm Gate

Khi user hỏi tại sao vi phạm Gate, gọi Claude CLI để điều tra khách quan:

```bash
python D:/Taadaa/tools/claude_worker.py \
  --role reviewer --model sonnet --max-turns 10 \
  "Yeu cau: Khong dung Bash, khong doc file ngoai. 
  Tra loi truc tiep: [mô tả sự vi phạm, 3 câu hỏi cụ thể]"
```

**Lưu ý:** Prompt phải chỉ thị rõ "không dùng Bash, không đọc file" nếu không Claude CLI sẽ tự quét file và cạn turns.
