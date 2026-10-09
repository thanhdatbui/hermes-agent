# VieNeu-TTS Production Hardening & Closeout Audit Standards

Kinh nghiệm thực chiến khi đưa VieNeu-TTS pipeline từ PoC vào production và vượt qua Closeout Gate (Sol Auditor >= 85/100).

---

## 1. Content-Addressed Audio Cache (Chống Cache Collision)

### Vấn đề:
Đặt tên file cache theo index (`voice_{idx}_raw.wav`, `voice_{idx}_adj.wav`) là lỗi kiến trúc nguy hiểm:
- Khi chạy lại trên cùng `temp_dir` với video khác, hoặc khi kịch bản dịch/thứ tự segment thay đổi nhưng cùng số câu, pipeline sẽ tái sử dụng nhầm audio cũ mà không gọi TTS.
- Không báo lỗi exception nhưng xuất video sai hoàn toàn khẩu hình và nội dung thoại.

### Giải pháp chuẩn hóa:
Băm SHA256 dựa trên bộ 3 giá trị: `(text, speaker, slot_duration)`:
```python
import hashlib

def compute_segment_hash(text: str, speaker: str, slot_duration: float) -> str:
    key = f"{text}|{speaker}|{slot_duration:.3f}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

# Tên file an toàn:
raw_audio = out_dir / f"voice_{idx}_{seg_hash}_raw.wav"
adj_audio = out_dir / f"voice_{idx}_{seg_hash}_adj.wav"
```

---

## 2. Chính sách triệt tiêu tiếng gốc (Zero-Leak Audio Policy)

### Vấn đề:
Khi người dùng xem video lồng tiếng, nếu vẫn nghe thấy tiếng Trung/tiếng nước ngoài lọt vào, trải nghiệm sẽ rất khó chịu ("nhiều đoạn vẫn nói tiếng Trung").
- Ducking 15% - 20% chỉ phù hợp khi video gốc là nhạc nền không lời.
- Với video hội thoại (drama, vlog), tiếng nói gốc rất to và rõ, ducking 20% vẫn nghe rõ tiếng ngoại ngữ bên dưới giọng lồng tiếng.

### Giải pháp:
- Mặc định đặt `volume=0` (tắt hẳn track âm thanh gốc) cho video lồng tiếng toàn phần.
- Nếu muốn giữ tiếng động môi trường/nhạc nền gốc, chỉ đặt tối đa `volume=0.04` (4%) và chỉ áp dụng khi đã tách được vocal bằng Demucs/Spleeter.

---

## 3. Quy chuẩn độ phân giải video thành phẩm (Chống teo nhỏ video)

### Vấn đề:
Khi xuất bản preview để gửi Telegram cho nhẹ file, nếu vô tình scale độ phân giải (ví dụ từ `1088x1920` xuống `544x960`), người dùng sẽ phản hồi: *"Cái dưới bị teo nhỏ video"*.

### Giải pháp:
- Giữ nguyên độ phân giải gốc của video đầu vào (đặc biệt là video dọc 9:16).
- Để giảm dung lượng gửi nhanh qua Telegram:
  - Tăng nhẹ CRF (`-crf 23` hoặc `-crf 26`).
  - Dùng preset nhanh (`-preset fast` hoặc `-preset veryfast`).
  - Luôn thêm cờ `-movflags +faststart` để video phát được ngay lập tức trên app nhắn tin.

---

## 4. Kiểm thử tích hợp thật với FFmpeg (Real FFmpeg Integration Test)

### Vấn đề:
Khi closeout phiên làm việc, Sol Auditor sẽ đánh rớt điểm (REJECTED < 85) nếu toàn bộ unit test chỉ mock `subprocess.run`:
- Mock không chứng minh được cú pháp `filter_complex`, `adelay`, `amix` hay `subtitles` có chạy được trên FFmpeg thật hay không.
- Mock không kiểm tra được output MP4 có hợp lệ và có đủ stream `video` + `audio` hay không.

### Mẫu test tích hợp tự sinh media không cần fixture cồng kềnh:
```python
def test_pipeline_real_ffmpeg_integration(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not available")

    # 1. Tự sinh video test 1s có audio sine wave 1kHz bằng lavfi
    in_video = tmp_path / "test_1s.mp4"
    cmd_gen = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=1.0",
        "-t", "1.0", "-c:v", "libx264", "-c:a", "aac", str(in_video)
    ]
    subprocess.run(cmd_gen, capture_output=True, check=True)

    # 2. Chạy pipeline qua FFmpeg thật
    out_video = tmp_path / "out.mp4"
    run_dubbing(video_path=str(in_video), segments=[...], output_path=str(out_video), ...)

    # 3. Dùng ffprobe thật kiểm chứng stream
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out_video)],
        capture_output=True, text=True, check=True
    )
    streams = probe.stdout.strip().splitlines()
    assert "video" in streams
    assert "audio" in streams
```

---

## 5. Subprocess Timeout Guards & Structured Telemetry

- Mọi lệnh gọi `subprocess.run` (cả `ffprobe` và `ffmpeg`) BẮT BUỘC phải có tham số `timeout=120` để tránh treo tiến trình ngầm làm nghẽn phone farm.
- Hàm trả về object `DubbingMetrics` (số segment thành công, số segment lỗi, số segment bị stretch `atempo`, thời gian xử lý) thay vì chỉ trả về string đường dẫn.

---

## 6. Reviewer Port & Infrastructure Failover Insight (Closeout Gate 2026-10-07)

- **Review combo `review` trên OmniRoute (`:20129`)**:
  - Thứ tự priority: `[Tier 0] chatgpt-web-pool (Sol High) -> [Tier 1] codex-terra-high -> [Tier 2] ag-opus-pool (Claude Opus 4.6 Thinking via Antigravity) -> [Tier 3] Nemotron`.
  - Nếu Sol chết hoặc rớt mạng, OmniRoute tự động nhảy sang Antigravity Claude Opus.
- **Nguyên nhân lỗi `[WinError 10061]` khi chạy Closeout Gate**:
  - Khi Node.js của OmniRoute khởi động lại, cổng `:20129` tạm đóng trong ~10-15s.
  - Script `closeout_gate.py` thăm dò timeout nhanh (1s) và tự động fallback sang IP LAN `192.168.110.123:20129` rồi báo lỗi từ chối kết nối.
  - Khắc phục: Đợi vài giây backoff kết nối lại `http://127.0.0.1:20129/v1/chat/completions` thay vì vội vàng chuyển sang LAN IP.
- **9Router (`:20128`) vs OmniRoute (`:20129`) Web Capability**:
  - `chatgpt-web` là provider nội bộ của OmniRoute. 9Router KHÔNG có provider `chatgpt-web` mà chỉ có `openai` (API key), `codex` (Codex CLI OAuth), `grok-web`, `perplexity-web`.
  - Muốn 9Router làm fallback độc lập khi OmniRoute chết thì phải dùng pool `antigravity` (Claude Opus 4.6 Thinking) hoặc `deepseek`.

