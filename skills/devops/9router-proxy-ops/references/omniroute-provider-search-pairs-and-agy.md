# OmniRoute Provider Search Pairs & Antigravity/Agy Credential Routing

## Core Architecture
- **Backend Shared Endpoints**: `antigravity` (IDE / VS Code OAuth) and `agy` (Antigravity CLI OAuth) both route to Google Cloud Code Assist backend (`daily-cloudcode-pa.googleapis.com`).
- **Model Aliasing**: `ALIAS_TO_PROVIDER_ID["agy"] = "antigravity"` (`open-sse/services/model.ts`).
- **Token Search Pairs**: `PROVIDER_SEARCH_PAIRS` in `src/sse/services/auth.ts`:
  ```ts
  PROVIDER_SEARCH_PAIRS = [
    ["antigravity", "agy"],
    ["opencode", "opencode-zen"],
    ["jina-ai", "jina-reader", "jina-search"],
  ];
  ```

## Request & Test Dispatch Flow
1. When calling `POST /api/models/test` or `/v1/chat/completions` with provider `agy`:
   - `getProviderSearchPool("agy")` resolves to `["agy", "antigravity"]`.
   - Active tokens from both `agy` and `antigravity` connections in `provider_connections` table are pulled into the search candidate pool.
   - If user has active `antigravity` accounts (e.g. 12 Pro + 1 Starter), `agy` model test / calls will succeed using those credentials.

## UI Presentation vs Backend Reality
- **UI `/dashboard/providers/agy`**: Queries `WHERE provider = 'agy'`, so it shows 0 accounts if all connections were imported under `antigravity`.
- **Model Test Result**: Succeeds because the test runner executes against the unified search pool, borrowing active credentials from `antigravity`.
