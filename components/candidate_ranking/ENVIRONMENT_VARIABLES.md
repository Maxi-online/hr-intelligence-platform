# CandidateRanking — Changing Environments

CandidateRanking uses YAML – configuration (`config/settings.yaml`) as the source of truth. Changing environments can be used for local development and CI/CD, but they are not mandatory.

## Basic variables
```bash
# Start mode (used to identify service addresses))
DOCKER_ENV=true            # for launching in Docker Compose
```

## OpenAI (optimal)
If you don’t want to store the key in YAML (`ai_analysis.openai_api_key`), set it through the container environment `ai_analysis`.
```bash
OPENAI_API_KEY=sk-your-openai-api-key
```

## HH.ru OAuth (employer)
It is recommended to be stored in `config/settings.yaml` (`hh_api` section), but for CI/CD it is allowed to export through the environment and subsequent recording in YAML.
```bash
HH_CLIENT_ID=your_hh_client_id
HH_CLIENT_SECRET=your_hh_client_secret
# If user currents are available:
HH_ACCESS_TOKEN=...
HH_REFRESH_TOKEN=...
```

## Treamlit (optimal)
```bash
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## Proxie (optimal)
Use only if necessary. Don't keep real creds in the repository.
```bash
PROXY_HOST=
PROXY_PORT=
PROXY_USERNAME=
PROXY_PASSWORD=
PROXY_PROTOCOL=http
```

## Security notes
- Don't mix real keys/passwords. Use CI/CD secrets or local `.env.local` (in `.gitignore`).
- You keep secrets in the store, not in YAML.
- Within the Docker Composition, the variables are transmitted via `environment:` of the corresponding service.