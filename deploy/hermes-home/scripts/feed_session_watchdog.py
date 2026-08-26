"""Watchdog báo cáo kết quả nuôi TikTok theo từng CA / PHIÊN (không spam từng tick đợt nhỏ).

Một ngày có 3 Ca, mỗi Ca có 3 Phiên:
- Ca 1 (Sáng):
  + Phiên 1: Khung ~06:00 - 07:30
  + Phiên 2: Khung ~07:35 - 09:30
  + Phiên 3: Khung ~09:35 - 11:30
- Ca 2 (Chiều):
  + Phiên 1: Khung ~12:00 - 13:45
  + Phiên 2: Khung ~13:45 - 15:30
  + Phiên 3: Khung ~15:30 - 18:15
- Ca 3 (Tối):
  + Phiên 1: Khung ~18:30 - 20:15
  + Phiên 2: Khung ~20:15 - 22:00
  + Phiên 3: Khung ~22:00 - 23:55

Cơ chế:
- Gom toàn bộ kết quả của các máy chạy trong phiên đó (kể cả chia nhỏ nhiều đợt runner).
- Khi phiên đó kết thúc (hết window giờ và runner đã hoàn tất batch cuối):
  -> Gửi đúng 1 BÁO CÁO TỔNG KẾT PHIÊN duy nhất.
"""
import os
import glob
import json
from datetime import datetime
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")
LIVE_ROOT = r"D:\Taadaa\runtime\kibe\live"
STATE_FILE = r"D:\Taadaa\runtime\kibe\cron-state\feed_session_reported.json"

# Định nghĩa các khung phiên chuẩn
SESSION_WINDOWS = [
    # Ca 1
    {"ca": 1, "phien": 1, "name": "Ca 1 - Phiên 1/3 (Sáng)", "start": "06:00", "end": "07:30", "row": 2},
    {"ca": 1, "phien": 2, "name": "Ca 1 - Phiên 2/3 (Sáng)", "start": "07:30", "end": "09:30", "row": 2},
    {"ca": 1, "phien": 3, "name": "Ca 1 - Phiên 3/3 (Sáng)", "start": "09:30", "end": "11:50", "row": 2},
    # Ca 2
    {"ca": 2, "phien": 1, "name": "Ca 2 - Phiên 1/3 (Chiều)", "start": "12:00", "end": "13:45", "row": 4},
    {"ca": 2, "phien": 2, "name": "Ca 2 - Phiên 2/3 (Chiều)", "start": "13:45", "end": "15:30", "row": 4},
    {"ca": 2, "phien": 3, "name": "Ca 2 - Phiên 3/3 (Chiều)", "start": "15:30", "end": "18:20", "row": 4},
    # Ca 3
    {"ca": 3, "phien": 1, "name": "Ca 3 - Phiên 1/3 (Tối)", "start": "18:30", "end": "20:15", "row": 2},
    {"ca": 3, "phien": 2, "name": "Ca 3 - Phiên 2/3 (Tối)", "start": "20:15", "end": "22:00", "row": 2},
    {"ca": 3, "phien": 3, "name": "Ca 3 - Phiên 3/3 (Tối)", "start": "22:00", "end": "23:59", "row": 2},
]


def parse_run_machines(run_dir):
    """Lấy map machine -> final_status từ 1 run dir."""
    summaries = glob.glob(os.path.join(run_dir, "**", "summary.txt"), recursive=True)
    res = {}
    for s in summaries:
        parts = os.path.normpath(s).split(os.sep)
        if "machines" in parts:
            m_idx = parts.index("machines") + 1
            if m_idx < len(parts):
                m_str = parts[m_idx].replace("machine_", "")
                c = open(s, encoding="utf-8", errors="ignore").read()
                st = "success" if "final_status: success" in c else "fail"
                # get reason if fail
                reason = ""
                for line in c.splitlines():
                    if line.startswith("reason:") or line.startswith("final_status:"):
                        val = line.split(":", 1)[1].strip()
                        if val != "success":
                            reason = val
                            break
                res[m_str] = {"status": st, "reason": reason}
    return res


def main():
    now = datetime.now(HCMC)
    today = now.strftime("%Y-%m-%d")
    now_hm = now.strftime("%H:%M")
    today_live = os.path.join(LIVE_ROOT, today)
    if not os.path.exists(today_live):
        return

    # Load state
    state = {"reported_sessions": []}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {"reported_sessions": []}

    reported = set(state.get("reported_sessions", []))
    runs = sorted(os.listdir(today_live))

    messages = []
    new_reported = list(reported)

    for win in SESSION_WINDOWS:
        session_key = f"{today}_ca{win['ca']}_phien{win['phien']}"
        if session_key in reported:
            continue

        # Chỉ báo cáo khi ĐÃ HẾT GIỜ của phiên đó
        if now_hm < win["end"]:
            continue

        # Tìm các run folder thuộc khung giờ phiên này
        session_runs = []
        for r in runs:
            # format: row-X-HHMMSS
            parts = r.split("-")
            if len(parts) >= 3 and parts[0] == "row":
                hhmmss = parts[2]
                if len(hhmmss) >= 4:
                    r_hm = f"{hhmmss[:2]}:{hhmmss[2:4]}"
                    if win["start"] <= r_hm <= win["end"]:
                        session_runs.append(r)

        if not session_runs:
            continue

        # Gom kết quả toàn bộ máy chạy trong phiên
        all_machines = {}
        for r in session_runs:
            r_path = os.path.join(today_live, r)
            m_res = parse_run_machines(r_path)
            # Latest run of machine in this session overrides previous run
            for m, data in m_res.items():
                all_machines[m] = data

        if not all_machines:
            continue

        def num_key(s):
            import re
            nums = re.findall(r"\d+", s)
            return int(nums[0]) if nums else 0

        succ = sorted([m for m, d in all_machines.items() if d["status"] == "success"], key=num_key)
        fail = sorted([f"M{m}" for m, d in all_machines.items() if d["status"] != "success"], key=num_key)
        total = len(succ) + len(fail)

        succ_str = ", ".join(succ) if succ else "Không có"
        fail_str = ", ".join(fail) if fail else "Không có"

        msg = (
            f"📊 [TIKTOK NUÔI ACC] {win['name']} hoàn tất\n"
            f"• Tổng máy xử lý: {total}\n"
            f"• Success ({len(succ)}): {succ_str}\n"
            f"• Fail ({len(fail)}): {fail_str}"
        )
        messages.append(msg)
        new_reported.append(session_key)

    if messages:
        state["reported_sessions"] = new_reported
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)
        except Exception:
            pass

        print("\n\n".join(messages))


if __name__ == "__main__":
    main()
