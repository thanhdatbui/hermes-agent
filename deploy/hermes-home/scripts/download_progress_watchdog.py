"""Script watchdog báo tiến độ download_by_niche mỗi 1h."""
import os
import sys
import json
import sqlite3
from datetime import datetime

STATE_DB = r"D:\CodexRuntime\tiktok-video\state.db"
VIDEO_GOC = r"D:\video goc"

def main():
    try:
        # Check folder video counts on disk
        total_folders = 480
        adequate = 0
        under = 0
        zero = 0
        total_mp4 = 0
        
        for i in range(1, total_folders + 1):
            p = os.path.join(VIDEO_GOC, str(i))
            if os.path.exists(p):
                vids = [f for f in os.listdir(p) if f.endswith(".mp4")]
                count = len(vids)
                total_mp4 += count
                if count >= 30:
                    adequate += 1
                elif count > 0:
                    under += 1
                else:
                    zero += 1
            else:
                zero += 1

        # Check DB status
        db_stats = {}
        if os.path.exists(STATE_DB):
            conn = sqlite3.connect(STATE_DB)
            cur = conn.cursor()
            cur.execute("SELECT status, count(*) FROM folders GROUP BY status")
            db_stats = dict(cur.fetchall())
            conn.close()

        now_str = datetime.now().strftime("%H:%M %d/%m/%Y")
        msg = (
            f"📊 [TIẾN ĐỘ DOWNLOAD VIDEO - {now_str}]\n"
            f"• Đã đủ (>=30 video): {adequate}/{total_folders} folder\n"
            f"• Chưa đủ (1-29 video): {under} folder\n"
            f"• Chưa có video (0 video): {zero} folder\n"
            f"• Tổng video đã tải trên đĩa: {total_mp4} video\n"
            f"• Trạng thái DB: {json.dumps(db_stats, ensure_ascii=False)}"
        )
        print(msg)
    except Exception as e:
        print(f"Lỗi kiểm tra tiến độ download: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
