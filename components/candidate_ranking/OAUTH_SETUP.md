# 🔐 OAuth settings for CandidateRanking

## What it takes to operate the system

CandidateRanking requires **OAuth HH API tokens** for access to your jobs and **OpenAI API key** for AI analysis.

## 📋 HH API step settings

### 1. Create application on hh.ru

1. Enter https://dev.hh.ru/admin
2. Create a new application:
   - **Name**: CandidateRanking
   - ** Description**: Vacancy response system
   - **Redirect URI**: `http://localhost:8088/oauth/callback`
3. Save **Client ID** and **Client Secret**

### 2. Production of currents

1. Open the URL authorization:
   ```
   https://hh.ru/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8088/oauth/callback
   ```
2. Authorize as**employer** (not applicant!)
3. Allow access to data
4. Copy `code=...` from the URL rerouting
5. Exchange the code for the current:
   ```bash
   curl -X POST https://hh.ru/oauth/token \
     -d "grant_type=authorization_code" \
     -d "client_id"
     -d "client_secret"
     -d "code" = code received
     -d "redirect_uri=http://localhost:8088/oauth/callback"
   ```

### 3. Settings

Edit `config/settings.yaml`:

```yaml
hh_api:
  client_id: "OH_CLIENT_ID"
  client_secret: "WAY_CLIENT_SECRET"
  user_agent: "CandidateRanking/1.0 (your_email@domain.com)"
  user_tokens:
    access_token: RECEIVED_ACESS_TOKEN
    refresh_token: RECEIVED_REFRESH_TOKEN

ai_analysis:
  openai_api_key: "sk-WAS_OPENAI_KNOCK"
```

## 🤖 Get OpenAI API Key

1. Enter https://platform.openai.com/api-keys
2. Create a new API Key
3. Add it to configuration.

## 🚀 Start the system

```bash
# Reassembly and run
docker-compose down --remove-orphans
docker-compose up -d --build

# Check Status
docker-compose ps
```

## ⚠️ Important restrictions

- **Only your jobs**: The system can only receive answers on the jobs placed from your employer account
- **Employers &apos; rights**: Token must be obtained from the employer &apos; s rights account
- **API**: HH.ru limits the number of requests per minute

## 🔍 Performance review

1. Open http://localhost:8501
2. Insert a link to the vacancy (from this account))
3. Press "Construct a TOP for Responses"

## 🐛 Addressing the problems

- **401 Authentication Error**: Check the tokens in configuration
- **403 Access prohibited**: Make sure the vacancy is yours
- **404 Not found**: no vacancy exists or is unavailable
- **429 Limited exceeded**: Wait before next request
