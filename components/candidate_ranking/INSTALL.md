# CandidateRanking - Installation and launch

## Description
CandidateRanking – a micro-service system: hh.ru receives feedback, summarizes, makes a multi-agent AI analysis and builds the top of candidates.

## Requirements
- Docker + Docker Compase (recommended)
- Python 3.11+ (for local launch without Docker)
- 4GB+ RAM

## Quick start (Docker)
```bash
git clone <repository-url>
cd CandidateRanking
cp config/settings.yaml.template config/settings.yaml
# fill in the keys in settings.yaml

docker-compose up -d --build
```
Access:
- Frontend: http://localhost:8501
- Gateway: http://localhost:8088/docs

## Local launch (optional)
```bash
pip install -r requirements.txt
# in selected terminals/processes
python gateway/main.py
python search/main.py
python ranking/main.py
python hh_api/main.py
python ai_analysis/main.py
streamlit run frontend/app.py --server.port=8501
```

## Structure
```
CandidateRanking/
  frontend/  gateway/  search/  ranking/  hh_api/  ai_analysis/  database/  config/  shared/
```

## Settings
- File: `config/settings.yaml` (YAML –only)
- Keys:
  - `ai_analysis.openai_api_key`
  - `hh_api.client_id`, `hh_api.client_secret`, `hh_api.user_tokens`

## Use
- Enter a link to the vacancy on the frontend main page
- Press "Construct a TOP for Responses"
- The service will upload the responses to the summary

## Diagnostics
```bash
# The Logic of All Services
docker-compose logs -f
# Gateway Health
curl http://localhost:8088/health
```

## Frequent problems
- 401/403 in response - check OAuth employer and rights
- 429/503 hh.ru — Wait for limit window; reduce parallelism/frequency
- 500 AI - Check OpenAI key and `ai_analysis` logs

## Update
```bash
docker-compose down
git pull
docker-compose up -d --build
```

License: MIT