# Auto-GPM Repository - Implementation Reference

## Repository Location
`D:\Taadaa\GPM auto\` (Git initialized, main branch)

## Directory Structure
```
D:\Taadaa\GPM auto\
├── AGENTS.md                 # Worker role gate
├── HANDOFF.md                # Context handoff
├── PROJECT_RULES.md          # Execution rules (from AI-Tools)
├── README.md                 # Usage docs
├── requirements.txt          # requests, playwright, pytest, pydantic
├── config/
│   ├── accounts.example.txt  # email|password|recovery_email
│   ├── proxies.example.txt   # protocol://user:pass@ip:port
│   └── config.example.yaml   # GPM base_url, batch settings
├── src/
│   ├── gpm_client.py         # GPM Local API v3 wrapper
│   └── cdp_auth.py           # Playwright CDP automation
├── scripts/
│   └── run_auth_batch.py     # Batch runner: 5 acc / 1 proxy
└── tests/
    └── test_gpm_client.py    # 5/5 PASSED
```

## Key Source Files

### src/gpm_client.py
```python
class GPMClient:
    def __init__(self, base_url="http://127.0.0.1:19995/api/v3", timeout=30):
        # Auto-detects port from api_port.dat or uses default 19995
    
    def create_profile(self, name, raw_proxy=None):
        # POST /profiles/create with raw_proxy
    
    def start_profile(self, profile_id):
        # GET /profiles/start/{id} → returns remote_debugging_address
    
    def stop_profile(self, profile_id):
        # GET /profiles/stop/{id}
    
    def delete_profile(self, profile_id, mode=1):
        # GET /profiles/delete/{id}?mode=1
    
    def list_profiles(self, page=1, per_page=100):
        # GET /profiles?page={page}&per_page={per_page}
```

### src/cdp_auth.py
```python
class CDPAuthWorker:
    def __init__(self, cdp_url):
        # playwright.chromium.connect_over_cdp(cdp_url)
    
    def login_google(self, email, password, recovery_email=None):
        # Full Google sign-in flow with recovery email handling
    
    def authorize_antigravity(self, auth_url):
        # Navigate to auth_url, click Allow/Continue, extract token
```

### scripts/run_auth_batch.py
```python
# Usage:
# python scripts/run_auth_batch.py --accounts config/accounts.txt --proxies config/proxies.txt --auth-url "https://..."
# 
# Logic:
# 1. Read accounts & proxies
# 2. For each proxy: process up to 5 accounts
# 3. For each account: gpm.create → gpm.start → cdp.login → cdp.auth → gpm.stop → gpm.delete
# 4. Delay 5-15s between accounts on same proxy
```

## Test Commands
```bash
cd "D:\Taadaa\GPM auto"
python -m pytest tests/ -v
# 5 tests PASSED
```

## Integration Notes
- GPM API Port: 19995 (stored in `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\api_port.dat`)
- Profile DB: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- Delete mode=1: Local data deletion only (keeps profile record with GroupId=0 for recovery)
- 7za available at: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\7za.exe`