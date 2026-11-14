# 🚀 Quick Start - CandidateRanking

CandidateRanking builds the top of candidates by referring to the hh.ru vacation: downloads responses, draws a summary, makes a multi-agent AI analysis and rank.

## (1) Training
```bash
cp config/settings.yaml.template config/settings.yaml
# Insert keys to config/settings.yaml:
# - ai_analysis.openai_api_key
# - hh_api.client_id / client_secret (OAuth employer)
# - hh_api.user_tokens.access_token / refresh_token (If you already have)
```

## (2) Launch (Docker Compose)
```bash
docker-compose up -d --build
```

## (3) Verification
- Frontend: http://localhost:8501
- Gateway API: http://localhost:8088/docs

## (4) Receive a TAP for a vacancy
1. Open Frontend
2. Insert `https://hh.ru/vacancy/<id>` mode link
3. Press "Construct a TOP for Responses"

Alternative via API (through Gateway):
```bash
curl -X POST http://localhost:8088/vacancy/top \
  -H 'Content-Type: application/json' \
  -d '{"vacancy_url":"https://hh.ru/vacancy/123456789","limit":10}'
```

## Composition of services and ports
- frontend: 8501
- gateway: 8088
- search: 8001
- ranking: 8002
- hh_api: 8003
- ai_analysis: 8005
- clickhouse: 8123 (http), 9000 (native)

## Thickness HH.ru
- The list of answers uses the “employee talks” (`/employer_negotiations`), requires the OAuth employer and rights.
- At 401/403 - check `client_id/client_secret` and issue office rights.
- At 429, reruns are delayed, wait for the limit window.

## Thickness AI
- OpenAI key is taken from `config/settings.yaml` (or `OPENAI_API_KEY`).
- The analysis goes through `/multi-agent/batch`.

## Update
```bash
docker-compose down && git pull && docker-compose up -d --build
```