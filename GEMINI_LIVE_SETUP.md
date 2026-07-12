# Gemini Live API Setup

## Current Architecture

```
Frontend (index.html)
  ↓ WebSocket
Browser Proxy Handler (ws_proxy_handler)  [port 8081]
  ↓ WebSocket (localhost:8083/ws)
Backend WebSocket Handler (app.py)  [port 8083]
  ↓ WebSocket with Bearer Token
Google Vertex AI Live API  [wss://us-central1-aiplatform.googleapis.com/...]
```

## Current Authentication Flow

### 1. Service Account Credentials (Backend)

**File**: `/Users/miguelaprossine/octopus-thorvg/credentials.json`
- Service Account: `vertex-express@octopus-489714.iam.gserviceaccount.com`
- Project ID: `octopus-489714`
- Uses Google Service Account for OAuth2 token generation

**Code in app.py (lines 462-480)**:
```python
creds = service_account.Credentials.from_service_account_file(
    creds_path,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)
creds.refresh(Request())
token = creds.token

google_ws = await websockets.connect(
    service_url,
    additional_headers=[
        ("Authorization", f"Bearer {token}"),
        ("Content-Type", "application/json"),
    ],
)
```

### 2. Vertex AI WebSocket Connection

**Service URL Pattern** (line 487):
```python
wss://us-central1-aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent
```

**Setup Message** (lines 485-502):
```json
{
  "setup": {
    "model": "projects/octopus-489714/locations/us-central1/publishers/google/models/gemini-live-2.5-flash-native-audio",
    "generation_config": {
      "response_modalities": ["AUDIO"],
      "temperature": 1.0,
      "speech_config": { ... }
    },
    "system_instruction": { ... },
    "input_audio_transcription": {},
    "output_audio_transcription": {}
  }
}
```

### 3. Environment Variables

**In .env** (lines 23-29):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_PROJECT_ID=octopus-489714

# Currently not used for Gemini Live
VERTEX_AI_API_KEY=AIzaSyBYVD-zuTRVl9dnt1-A0UE6t52nMwAWBtA
```

## How to Switch to New Vertex AI Account

### Step 1: Get New Service Account Credentials

1. Go to Google Cloud Console: https://console.cloud.google.com
2. Select your new project or create one
3. Go to **Service Accounts** section
4. Create a new Service Account (or use existing)
5. Create a JSON key file
6. This file contains:
   - `project_id`
   - `private_key`
   - `client_email`
   - `type: "service_account"`

### Step 2: Enable Vertex AI API

1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Vertex AI API"
3. Click **Enable**
4. Also enable "Cloud Logging API" for monitoring

### Step 3: Update credentials.json

Replace `/Users/miguelaprossine/octopus-thorvg/credentials.json` with your new service account JSON key file.

Example structure:
```json
{
  "type": "service_account",
  "project_id": "YOUR_NEW_PROJECT_ID",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@YOUR_NEW_PROJECT_ID.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Step 4: Update Project ID (if different)

In `/Users/miguelaprossine/octopus-thorvg/backend/app.py`:

**Line 24** (gemini_live_client.py):
```python
self.project_id = "YOUR_NEW_PROJECT_ID"  # Was: "upheld-rain-484209-a6"
```

**Line 484** (app.py):
```python
project_id = os.environ.get("GEMINI_PROJECT_ID", "YOUR_NEW_PROJECT_ID")  # Was: "octopus-489714"
```

Or better, update `.env`:
```env
GEMINI_PROJECT_ID=YOUR_NEW_PROJECT_ID
```

### Step 5: Optional - Update Region

Default: `us-central1`

If your new project uses different region, update in app.py:

**Line 165** (geminilive.js):
```javascript
this.location = "YOUR_REGION";  // e.g., "us-east1", "europe-west1"
this.apiHost = `${this.location}-aiplatform.googleapis.com`;
```

**Line 25** (gemini_live_client.py):
```python
self.location = "YOUR_REGION"
```

## Files That Need Changes

### Must Update:
1. **`/credentials.json`** — Replace with new service account key
2. **`.env`** — Update `GEMINI_PROJECT_ID` (optional, only if project ID changed)

### May Need Update (if using different project/region):
1. **`backend/app.py`** — Line 484 (project_id default)
2. **`frontend/geminilive.js`** — Line 135 (modelUri), Line 165 (location)
3. **`backend/gemini_live_client.py`** — Line 24-25 (project_id, location)

## Testing

### 1. Check Credentials Loading
```bash
cd /Users/miguelaprossine/octopus-thorvg
python3 -c "
from google.oauth2 import service_account
from google.auth.transport.requests import Request

creds = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
creds.refresh(Request())
print(f'✅ Token obtained: {creds.token[:50]}...')
print(f'Project: {creds.project_id}')
"
```

### 2. Start Backend & Test
```bash
# Start backend
python3 backend/app.py

# In browser console
console.log(state.geminiClient)
```

### 3. Monitor Logs
Watch for these messages:
- `📡 Connecting to: wss://...` — Connecting to Vertex AI
- `🔑 Token: ...` — Bearer token obtained
- `✅ Google подключен` — Connection successful
- `📤 Setup message sent to Google` — Session initialized

## Common Issues

### Issue: "403 Forbidden" or "401 Unauthorized"
**Cause**: Service account doesn't have necessary permissions
**Fix**: 
1. Go to IAM & Admin in Cloud Console
2. Find your service account
3. Grant these roles:
   - `Vertex AI User` (roles/aiplatform.user)
   - `Vertex AI Service Agent`

### Issue: "Model not found" or "Project not found"
**Cause**: Wrong project_id or region
**Fix**: Verify in app.py console output that project_id matches Cloud Console

### Issue: Connection drops after setup
**Cause**: Token expired or WebSocket timeout
**Fix**: Token is auto-refreshed every ~1 hour in the code. Check network logs in browser console.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Frontend: index.html + geminilive.js                   │   │
│  │  - WebSocket client                                      │   │
│  │  - No credentials stored (all handled server-side)      │   │
│  │  - Proxy URL: ws://localhost:8083/ws                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            ↓                                      │
│                    Browser ↔ Backend                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                             ↓
        ┌──────────────────────────────────────────┐
        │    Backend Server (app.py)               │
        │    Port 8083 (frontend proxy)            │
        │    Port 8081 (HTTP server)               │
        ├──────────────────────────────────────────┤
        │ 1. Load credentials.json                 │
        │ 2. Generate OAuth2 Bearer token         │
        │ 3. Connect to Vertex AI WebSocket       │
        │ 4. Proxy messages between browser/AI    │
        └──────────────────────────────────────────┘
                             ↓
        ┌──────────────────────────────────────────────┐
        │  Google Vertex AI (Cloud Hosted)             │
        │  WebSocket: wss://REGION-aiplatform.googleapis.com
        │  Model: gemini-live-2.5-flash-native-audio  │
        │  Auth: Bearer token (from service account)   │
        └──────────────────────────────────────────────┘
```

## Credentials Path Resolution

Backend looks for credentials in this order:
1. `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. `backend/credentials.json` (local to backend dir)
3. `credentials.json` (parent dir)
4. Falls back to `"credentials.json"` (current working dir)

**Best practice**: Keep at `/Users/miguelaprossine/octopus-thorvg/credentials.json`

---

**Last Updated**: 2026-05-22
