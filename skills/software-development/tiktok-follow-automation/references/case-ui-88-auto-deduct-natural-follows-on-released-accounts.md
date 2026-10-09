# Case UI-88: Khấu Trừ Tự Động Follow Tự Nhiên Của Các Nick Bị Nhả Follow Trong Báo Cáo Watchdog & Database (2026-10-03)

## 1. Bối Cảnh & Đòi Hỏi Vận Hành
- **Hiện tượng:**
  - Trong ca nuôi feed, bước lướt feed chạy trước và ghi nhận các lượt follow tự nhiên khi xem video (`natural_follows`).
  - Đến bước follow chéo chạy sau, máy thực hiện quy trình Pull-to-refresh để đối soát server truth và phát hiện nick bị TikTok nhả follow (`follow_failed = True` hoặc `released`).
  - **Nghịch lý báo cáo trước đây:** Dòng trên watchdog vẫn ghi nhận đầy đủ số follow tự nhiên (ví dụ: `Follow tự nhiên: 12 lượt`), nhưng dòng dưới lại thông báo nick bị nhả follow và phần đối soát Web cào về delta `+0`.
- **Chỉ đạo vận hành từ User:**
  > *"Dữ liệu web đc cào trc mỗi phiên chạy mà? Còn fl tự nhiên chạy trc fl chéo đến phiên fl chéo phát hiện ra nick đó bị drop thì phải tự trừ ra lượt fl tự nhiên của nó chứ"*
- **Bản chất kỹ thuật:** Khi TikTok server đã Silent Action Block / nhả follow ở luồng follow chéo, 100% các lượt tap follow tự nhiên trên video trước đó của nick này cũng đã bị server âm thầm hủy bỏ (shadow-dropped). Việc báo cáo số follow tự nhiên đó là báo cáo khống / số ảo.

---

## 2. Giải Pháp Triển Khai Trong Code (`feed_session_watchdog.py`)

### A. Hàm Khấu Trừ `calculate_session_natural_follows`
Đặt tại `scripts/feed_session_watchdog.py`:
```python
def calculate_session_natural_follows(
    all_machines: dict[str, Any],
    all_follows: dict[str, Any],
    fl_released: list[Any] | None = None,
) -> tuple[int, int, int, int, int]:
    """Tính toán số lượt follow tự nhiên hợp lệ sau khi trừ các nick bị nhả/drop.
    
    Trả về: (valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot)
    """
    fl_released = fl_released or []
    released_machine_set = {str(m) for m in fl_released}
    for m_k, f_data in all_follows.items():
        if isinstance(f_data, dict) and (
            f_data.get("follow_failed") is True
            or str(f_data.get("status") or "").upper() == "FOLLOW_FAILED"
        ):
            released_machine_set.add(str(m_k))

    tot_fy = 0
    tot_fl = 0
    tot_fr = 0
    dropped_fy = 0
    dropped_fl = 0
    dropped_fr = 0

    for m, d in all_machines.items():
        if not isinstance(d, dict) or d.get("status") != "success":
            continue
        nf = d.get("natural_follows") or {}
        fy = int(nf.get("for-you", 0) or 0)
        fl = int(nf.get("following", 0) or 0)
        fr = int(nf.get("friends", 0) or 0)
        tot_fy += fy
        tot_fl += fl
        tot_fr += fr
        if str(m) in released_machine_set:
            dropped_fy += fy
            dropped_fl += fl
            dropped_fr += fr

    dropped_tot = dropped_fy + dropped_fl + dropped_fr
    valid_fy = max(0, tot_fy - dropped_fy)
    valid_fl = max(0, tot_fl - dropped_fl)
    valid_fr = max(0, tot_fr - dropped_fr)
    valid_tot = max(0, (tot_fy + tot_fl + tot_fr) - dropped_tot)

    return valid_tot, valid_fy, valid_fl, valid_fr, dropped_tot
```

### B. Minh Bạch Telemetry Trên Báo Cáo Telegram
Trong hàm `main()`, sau khi duyệt xong danh sách máy và thu được `fl_released`:
```python
valid_tot_nat, valid_fy_nat, valid_fl_nat, valid_fr_nat, dropped_tot_nat = calculate_session_natural_follows(
    all_machines, all_follows, fl_released
)
valid_nat_rate = (valid_tot_nat / tot_swipes * 100.0) if tot_swipes > 0 else 0.0
if dropped_tot_nat > 0:
    nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}] (Đã tự trừ {dropped_tot_nat} lượt do nick bị nhả/drop)"
else:
    nat_follow_line = f"  + Follow tự nhiên: {valid_tot_nat} lượt / {tot_swipes} video ({valid_nat_rate:.1f}%) [Đề xuất: {valid_fy_nat} | Bạn bè: {valid_fr_nat}]"
```

### C. Làm Sạch Database (`tiktok_tracker.db`)
Chỉ truyền `natural_fl = valid_tot_nat` vào `save_session_action_stats(...)` để ghi vào bảng `session_action_stats`, đảm bảo Dashboard `http://localhost:8080` không bị vống số liệu ghost follow:
```python
save_session_action_stats(
    db_path=r"D:/Taadaa/data/tiktok_tracker.db",
    session_key=session_key,
    cluster_name=cluster.get("name", "unknown"),
    target_date=target_date,
    internal_fl=total_followed_count,
    natural_fl=valid_tot_nat,
    likes=tot_likes,
    swipes=tot_swipes,
)
```

---

## 3. Quy Tắc Vận Hành Chuẩn Hóa
1. **Tiền đề xác thực T0:** Mỗi phiên chạy đều có bước cào T0 trước phiên trong `tiktok_runner.py` và cào T1 sau phiên trong `feed_session_watchdog.py`. Số liệu đối soát Web phản ánh đúng delta trong phiên.
2. **Nguyên tắc một chiều của Action Block:** Một khi nick bị phát hiện nhả follow ở bước follow chéo, toàn bộ tương tác follow (kể cả tự nhiên) trong phiên đó của nick phải bị coi là vô hiệu trên server.
3. **Kỷ luật Closeout Gate trước khi push:** Khi sửa watchdog hoặc flow follow, bắt buộc chạy `closeout_gate.py --repo <path> --json-output` với working tree staged sạch. Commit phải khớp exact hash với audit log để vượt qua pre-push hook `INC-HERMES-2026-001`.
