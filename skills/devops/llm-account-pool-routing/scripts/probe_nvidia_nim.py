import sys
import json
import urllib.request
import urllib.error

def check_nvidia_key(api_key: str, model: str = "qwen/qwen2.5-coder-32b-instruct"):
    """
    Probe an NVIDIA NIM API key (nvapi-...) against integrate.api.nvidia.com
    to verify validity, remaining quota/credits, and model response.
    """
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 10
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("[SUCCESS] Key is VALID and ACTIVE!")
            print(f"Model: {model}")
            print(f"Response: {data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        print(f"[HTTP ERROR {e.code}]: {err_body}")
        if e.code == 401:
            print("-> Invalid API Key")
        elif e.code in (402, 429):
            print("-> Key exhausted (0 credits) or rate-limited")
        return False
    except Exception as e:
        print(f"[ERROR]: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python probe_nvidia_nim.py <nvapi-key> [model_name]")
        sys.exit(1)
    
    key = sys.argv[1]
    m = sys.argv[2] if len(sys.argv) > 2 else "qwen/qwen2.5-coder-32b-instruct"
    check_nvidia_key(key, m)
