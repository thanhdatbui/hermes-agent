import json
import sys
import time
import urllib.request

sys.path.insert(0, r"D:\Taadaa\Tiktok_Reg")
from social_reg_v1 import _cdp_evaluate  # noqa
from automation_core.adb import AdbClient

# Cách dùng: sửa DEVICE + PORT rồi chạy. In DOM Outlook thực tế để xem
# thứ tự mail TikTok (mới/cũ) và mã OTP — chẩn đoán OTP_REJECTED.
DEVICE = "ce11160b54ee2f3403"
PORT = "9224"


def main():
    fwd = AdbClient(adb_path=r"C:\Program Files (x86)\xiaowei\tools\adb.exe",
                    serial=DEVICE, default_timeout=10).run(
        ["forward", f"tcp:{PORT}", "localabstract:chrome_devtools_remote"], timeout=10)
    if not fwd.ok:
        print("forward FAIL", fwd.output)
        return
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=5) as r:
            tabs = json.load(r)
        outlook = [t for t in tabs if "outlook.live.com/mail" in str(t.get("url") or "")]
        print("outlook tabs:", len(outlook))
        if not outlook:
            print("TABS:", [t.get("url", "")[:60] for t in tabs][:10])
            return
        ws_url = str(outlook[0]["webSocketDebuggerUrl"]).replace(
            "localhost:9222", f"127.0.0.1:{PORT}").replace(
            "127.0.0.1:9222", f"127.0.0.1:{PORT}")
        expr = r"""
        (() => {
          const result = [];
          for (const node of document.querySelectorAll('div,span,a')) {
            const text = (node.innerText || node.textContent || '').trim();
            if (!text || text.length > 700 || !/tiktok/i.test(text)) continue;
            const match = text.match(/(?:^|\D)(\d{6})(?!\d)/);
            if (!match) continue;
            result.push({code: match[1], sample: text.slice(0, 140)});
          }
          return result.slice(0, 15);
        })()
        """
        for i in range(3):
            val = _cdp_evaluate(ws_url, expr)
            if val:
                for item in val:
                    print(item.get("code"), "|",
                          item.get("sample", "")[:110].replace("\n", " "))
                break
            print(f"attempt {i+1}: empty")
            time.sleep(4)
    finally:
        AdbClient(adb_path=r"C:\Program Files (x86)\xiaowei\tools\adb.exe",
                  serial=DEVICE, default_timeout=10).run(
            ["forward", "--remove", f"tcp:{PORT}"], timeout=10)


if __name__ == "__main__":
    main()