import subprocess
import sys

res = subprocess.run([sys.executable, r"D:\Taadaa\AI-Tools\scripts\mobiproxy_auto_healer.py", "--check-and-heal"], capture_output=True, text=True)
if res.stdout:
    print(res.stdout)
if res.stderr:
    print(res.stderr, file=sys.stderr)
sys.exit(res.returncode)
